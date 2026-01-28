import os
import sys
import subprocess
import shutil
import time
import traceback
from PIL import Image

def update_progress(message):
    """진행 상황 메시지를 표준 출력으로 인쇄합니다."""
    print(message, flush=True)

# ... (wait_for_device_boot, get_sorted_files_by_ctime, resize_image, remove_all_files_in_folder 함수는 이전과 동일하므로 생략) ...
def wait_for_device_boot(timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "booted"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if "Booted" in result.stdout:
            return True
        time.sleep(2)
    return False

def get_sorted_files_by_ctime(folder_path, prefix):
    all_files = []
    try:
        for entry in os.scandir(folder_path):
            if entry.is_file() and entry.name.startswith(prefix):
                all_files.append(entry.path)
        all_files.sort(key=lambda x: os.path.getctime(x))
    except FileNotFoundError:
        update_progress(f"경고: 정렬할 파일을 찾기 위한 폴더가 없습니다: {folder_path}")
    return all_files

def resize_image(image_path, size):
    try:
        with Image.open(image_path) as img:
            img_resized = img.resize(size, Image.Resampling.LANCZOS)
            img_resized.save(image_path)
    except Exception as e:
        update_progress(f"리사이즈 오류: {image_path}, {str(e)}")

def remove_all_files_in_folder(folder_path):
    if not os.path.isdir(folder_path):
        return
    for entry in os.scandir(folder_path):
        if entry.is_file():
            os.remove(entry.path)

def postprocess_screenshots(desktop_screenshot_folder, project_folder):
    """
    스크린샷 후처리: 파일 선택, 리사이즈, 최종 폴더로 복사
    """
    selected_folder = os.path.dirname(project_folder)
    if not selected_folder or not os.path.isdir(selected_folder):
        update_progress(f"오류: 프로젝트의 상위 폴더를 찾을 수 없습니다: {selected_folder}")
        return

    # iPhone 스크린샷 처리
    iphone_files = get_sorted_files_by_ctime(desktop_screenshot_folder, prefix="iPhone")
    update_progress(f"iPhone 스크린샷 파일 개수: {len(iphone_files)}")
    iphone_keep = iphone_files[:15]
    iphone_delete = iphone_files[15:]
    for path in iphone_delete:
        os.remove(path)
    update_progress(f"[iPhone] {len(iphone_delete)}개 파일 삭제 완료.")

    iphone_correct_size = (1290, 2796)
    for path in iphone_keep:
        resize_image(path, iphone_correct_size)
    update_progress(f"[iPhone] 남긴 파일(최대 15개) 리사이즈 완료 {iphone_correct_size}.")

    # iPad 스크린샷 처리
    ipad_files = get_sorted_files_by_ctime(desktop_screenshot_folder, prefix="iPad")
    update_progress(f"iPad 스크린샷 파일 개수: {len(ipad_files)}")
    ipad_keep = ipad_files[:15]
    ipad_delete = ipad_files[15:]
    for path in ipad_delete:
        os.remove(path)
    update_progress(f"[iPad] {len(ipad_delete)}개 파일 삭제 완료.")

    ipad_correct_size = (2048, 2732)
    for path in ipad_keep:
        resize_image(path, ipad_correct_size)
    update_progress(f"[iPad] 남긴 파일(최대 15개) 리사이즈 완료 {ipad_correct_size}.")

    # --- ★★★★★ 수정된 부분 (폴더명을 기술적인 형식으로 변경) ★★★★★ ---
    screenshots_base = os.path.join(selected_folder, "Screenshots", "ko")
    # fastlane이 내부적으로 사용하는 디바이스 식별자 형식으로 변경
    iphone_target = os.path.join(screenshots_base, "APPLE_IPHONE_15_PRO_MAX") 
    ipad_target = os.path.join(screenshots_base, "APPLE_IPAD_PRO_12_9_6TH_GENERATION")
    # --- ★★★★★ 수정 끝 ★★★★★ ---

    os.makedirs(iphone_target, exist_ok=True)
    os.makedirs(ipad_target, exist_ok=True)
    update_progress(f"[생성] {iphone_target} 폴더 확인 완료.")
    update_progress(f"[생성] {ipad_target} 폴더 확인 완료.")

    for src_file in iphone_keep:
        shutil.copy2(src_file, iphone_target)
    for src_file in ipad_keep:
        shutil.copy2(src_file, ipad_target)
    total_copied = len(iphone_keep) + len(ipad_keep)
    update_progress(f"남긴 스크린샷 {total_copied}개 복사 완료:\n"
                         f"iPhone→ {iphone_target}\n"
                         f"iPad→ {ipad_target}")

    remove_all_files_in_folder(desktop_screenshot_folder)
    update_progress(f"임시 스크린샷 폴더({desktop_screenshot_folder}) 내 모든 파일 삭제 완료.")
    update_progress("스크린샷 후처리를 모두 마쳤습니다.")


def create_screenshot(selected_folder, bundle_id_val):
    if not selected_folder or not bundle_id_val:
        update_progress("오류: 폴더와 Bundle ID가 필요합니다!")
        return

    project_folder = os.path.join(selected_folder, bundle_id_val)
    if not os.path.exists(project_folder):
        update_progress(f"오류: 프로젝트 폴더를 찾을 수 없습니다: {project_folder}")
        return

    default_screenshot_folder = os.path.expanduser("~/Desktop/Screenshots")
    
    required_paths = {
        "integration_test 폴더": os.path.join(project_folder, "integration_test"),
        "main_test.dart 파일": os.path.join(project_folder, "integration_test", "main_test.dart"),
        "test_driver 폴더": os.path.join(project_folder, "test_driver"),
        "integration_test_driver.dart 파일": os.path.join(project_folder, "test_driver", "integration_test_driver.dart"),
        "run_screenshots.sh 파일": os.path.join(project_folder, "run_screenshots.sh"),
    }
    
    for name, path in required_paths.items():
        if not os.path.exists(path):
            update_progress(f"오류: {name}을(를) 찾을 수 없습니다: {path}")
            return
    
    try:
        os.makedirs(default_screenshot_folder, exist_ok=True)
        update_progress(f"스크린샷 임시 폴더 생성: {default_screenshot_folder}")
        
        # --- ▼▼▼ 수정된 부분 ▼▼▼ ---
        # 명령어를 문자열이 아닌 리스트로 구성합니다.
        chmod_command_list = ["chmod", "+x", required_paths['run_screenshots.sh 파일']]
        # shell=True 옵션을 제거하고 리스트를 전달합니다.
        result = subprocess.run(chmod_command_list, capture_output=True, text=True)
        # --- ▲▲▲ 수정된 부분 ▲▲▲ ---

        if result.returncode != 0:
            update_progress(f"실행 권한 부여 실패: {result.stderr}")
            return
        update_progress("run_screenshots.sh 실행 권한 부여 완료")

        env_vars = os.environ.copy()
        env_vars["SCREENSHOT_FOLDER"] = default_screenshot_folder
        env_vars["DISABLE_ADS"] = "true"
        env_vars["SCREENSHOT_MODE"] = "true"
        
        update_progress("=== 스크린샷 생성 시작 ===")
        update_progress(f"프로젝트 폴더: {project_folder}")
        update_progress(f"스크린샷 임시 저장 위치: {default_screenshot_folder}")
        update_progress("테스트 대상 기기: iPhone 15, iPad Pro (12.9-inch) (6th generation)")
        
        command = "./run_screenshots.sh"
        process = subprocess.Popen(
            command, shell=True, cwd=project_folder, env=env_vars,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, universal_newlines=True
        )
        
        for line in process.stdout:
            update_progress(line.strip())
        
        exit_code = process.wait()
        
        if exit_code != 0:
            update_progress(f"오류: 스크린샷 생성 실패 (종료 코드: {exit_code})")
        else:
            update_progress("=== 스크린샷 생성 완료 ===")
            update_progress("후처리 작업을 시작합니다...")
            postprocess_screenshots(default_screenshot_folder, project_folder)
            
    except Exception as e:
        update_progress(f"스크린샷 생성 중 예외 발생: {str(e)}")
        update_progress(f"상세 오류: {traceback.format_exc()}")

def main():
    if len(sys.argv) != 3:
        print("사용법: python 10_Screenshot.py <selected_folder> <bundle_id>")
        sys.exit(1)
        
    selected_folder = sys.argv[1]
    bundle_id = sys.argv[2]
    
    update_progress(f"10. 스크린샷 생성 스크립트 시작")
    update_progress(f"  - 대상 폴더: {selected_folder}")
    update_progress(f"  - Bundle ID: {bundle_id}")

    create_screenshot(selected_folder, bundle_id)

if __name__ == "__main__":
    main()