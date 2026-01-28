# 13_release.py (수정)

import os
import sys
import subprocess

def log_message(message):
    """진행 상황을 콘솔에 출력하는 함수"""
    print(message, flush=True)

def run_fastlane_release(selected_folder, bundle_id_val):
    """Fastlane Release 명령어를 실행하는 핵심 함수"""
    log_message("Fastlane 배포 프로세스를 시작합니다.")
    
    project_folder = os.path.join(selected_folder, bundle_id_val)
    ios_folder = os.path.join(project_folder, "ios")
    fastlane_dir = os.path.join(ios_folder, "fastlane")
    fastfile_path = os.path.join(fastlane_dir, "Fastfile")

    if not os.path.isdir(ios_folder):
        log_message(f"오류: iOS 프로젝트 폴더를 찾을 수 없습니다 - {ios_folder}")
        sys.exit(1)

    os.makedirs(fastlane_dir, exist_ok=True)
    log_message(f"Fastlane 디렉토리 확인: {fastlane_dir}")

    # Fastfile 기본 내용
    default_fastfile_content = """
default_platform(:ios)
platform :ios do
  desc "Build and upload to App Store Connect"
  lane :release do
    sh "flutter pub get"
    sh "flutter clean"
    sh "flutter build ios --release --no-codesign"
    gym(
      workspace: "Runner.xcworkspace",
      scheme: "Runner",
      export_method: "app-store",
      output_directory: "./build/ios/iphoneos",
      archive_path: "./build/ios/archive",
      output_name: "Runner.ipa",
      clean: true,
      silent: false,
      xcargs: "-allowProvisioningUpdates"
    )
    deliver(
      skip_screenshots: true,
      skip_metadata: true,
      submit_for_review: false,
      force: true,
      username: "bombezzang2607@gmail.com"
    )
  end
end
""".lstrip()

    # Fastfile이 없으면 생성
    if not os.path.exists(fastfile_path):
        log_message("Fastfile이 없어 새로 생성합니다...")
        with open(fastfile_path, "w", encoding="utf-8") as f:
            f.write(default_fastfile_content)
    
    # 환경 변수 설정
    env_vars = os.environ.copy()
    env_vars["FASTLANE_PASSWORD"] = "huil-oazk-etxd-qmmn" # 앱 전용 암호
    env_vars["FASTLANE_SKIP_UPDATE_CHECK"] = "1"
    env_vars["LC_ALL"] = "en_US.UTF-8"

    log_message("Fastlane release 명령을 실행합니다... (수 분 소요)")
    
    try:
        process = subprocess.Popen(
            ["fastlane", "release"],
            cwd=ios_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1,
            env=env_vars
        )

        for line in iter(process.stdout.readline, ''):
            log_message(line.strip())

        process.stdout.close()
        return_code = process.wait()

        if return_code == 0:
            log_message("\n✅ Fastlane release 작업이 성공적으로 완료되었습니다.")
        else:
            log_message(f"\n⚠️ Fastlane release 작업 중 오류가 발생했습니다. (Return Code: {return_code})")
            sys.exit(return_code)
    
    except Exception as e:
        log_message(f"심각한 오류 발생: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        log_message("사용법: python 13_release.py <selected_folder> <bundle_id>")
        sys.exit(1)
        
    selected_folder = sys.argv[1]
    bundle_id = sys.argv[2]
    
    run_fastlane_release(selected_folder, bundle_id)

if __name__ == "__main__":
    main()