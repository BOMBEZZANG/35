import os
import sys
import subprocess
import unicodedata
import traceback

def update_progress(message):
    """진행 상황 메시지를 표준 출력으로 인쇄합니다."""
    print(message, flush=True)

def get_app_name(selected_folder):
    """폴더 경로에서 앱 이름을 추출합니다."""
    if not selected_folder:
        return ""
    folder_name = os.path.basename(selected_folder)
    # macOS 한글 자소 분리(NFD) 문제를 정규화(NFC)하여 해결
    folder_name = unicodedata.normalize('NFC', folder_name)
    return folder_name

def produce_app(selected_folder, bundle_id_input):
    """Fastlane Produce를 실행하여 App Store Connect에 앱을 생성합니다."""
    if not selected_folder or not bundle_id_input:
        update_progress("오류: 대상 폴더와 Bundle ID가 필요합니다.")
        return

    app_name_val = get_app_name(selected_folder)
    if not app_name_val:
        update_progress("오류: 앱 이름을 폴더명에서 추출할 수 없습니다.")
        return

    update_progress("=== Fastlane Produce 시작 ===")
    update_progress(f"앱 이름: {app_name_val}")
    update_progress(f"Bundle ID: {bundle_id_input}")

    app_identifier = f"com.example.{bundle_id_input}"
    sku = f"{bundle_id_input}SKU"

    command = [
        "fastlane", "produce",
        "--username", "bombezzang2607@gmail.com",
        "--app_identifier", app_identifier,
        "--app_name", f"{app_name_val}-기출문제,음성듣기",
        "--language", "ko",
        "--sku", sku,
        "--company_name", "JongminKIM"
    ]
    
    try:
        env = os.environ.copy()
        # 중요: 앱 전용 암호는 환경 변수나 더 안전한 방식으로 관리하는 것이 좋습니다.
        env["FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD"] = "huil-oazk-etxd-qmmn"
        env["FASTLANE_DEBUG"] = "1"
        
        update_progress(f"실행 명령어: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1,
            env=env
        )

        for line in iter(process.stdout.readline, ''):
            update_progress(line.strip())

        return_code = process.wait()
        
        if return_code == 0:
            update_progress("\n=== Fastlane Produce 성공적으로 완료되었습니다. ===")
        else:
            update_progress(f"\n오류: Fastlane Produce 실패 (종료 코드: {return_code})")
            sys.exit(1) # 실패 시 비정상 종료

    except Exception as e:
        update_progress(f"스크립트 실행 중 예외 발생: {e}")
        update_progress(traceback.format_exc())
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("사용법: python 11_produce.py <selected_folder> <bundle_id>")
        sys.exit(1)
        
    selected_folder = sys.argv[1]
    bundle_id = sys.argv[2]
    
    produce_app(selected_folder, bundle_id)

if __name__ == "__main__":
    main()