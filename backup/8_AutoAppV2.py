import plistlib
import subprocess
import os
import shutil
import yaml
import re
import sqlite3
import json
import time
import datetime
import pickle
from pathlib import Path
from PIL import Image
from googleapiclient import discovery
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import sys
import unicodedata
import socket
import socketserver

# 전역 변수
generated_privacy_policy_url = ""

# 상수 정의
CLIENT_SECRET = '/Users/jongminkim/Desktop/Apps/qcjongmin/client_secret_156950230449-p855cnddrfhl2o7tgs82c7jj9pdshr1j.apps.googleusercontent.com.json'
SCOPES = ['https://www.googleapis.com/auth/blogger']
BLOG_ID = '2760621040889199473'
TOKEN_FILE = "auto_token.pickle"
PORT = 8080

def update_progress(message):
    """진행 상황 메시지를 콘솔에 출력합니다."""
    print(message)
    sys.stdout.flush()

def get_app_name(app_name=None, selected_folder=None):
    """앱 이름을 폴더명으로부터 가져옵니다."""
    if app_name:
        return app_name
    if not selected_folder:
        return ""
    folder_name = os.path.basename(selected_folder)
    # Mac에서 한글 자소 분리 현상(NFD)을 정상적인 한글(NFC)로 변환
    folder_name = unicodedata.normalize('NFC', folder_name)
    return folder_name

def get_db_count(selected_folder):
    """폴더 내의 db 파일 개수를 셉니다."""
    assets_folder = os.path.join(selected_folder, "assets")
    if not os.path.exists(assets_folder):
        update_progress(f"DB 개수 확인: 'assets' 폴더를 찾을 수 없습니다: {assets_folder}")
        return 0
    try:
        db_files = [f for f in os.listdir(assets_folder)
                    if os.path.isfile(os.path.join(assets_folder, f)) and re.match(r'^question\d+\.db$', f)]
        return len(db_files)
    except Exception as e:
        update_progress(f"DB 파일 개수 확인 중 오류: {e}")
        return 0

def create_privacy_policy(selected_folder=None, app_name=None):
    """개인정보처리방침을 생성하고 블로그에 포스팅합니다."""
    global generated_privacy_policy_url
    update_progress("\n--- 개인정보처리방침 생성 시작 ---")
    app_name_val = get_app_name(app_name=app_name, selected_folder=selected_folder)
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    template = f"""
<p>This privacy policy applies to the {app_name_val} app (hereby referred to as "Application") for mobile devices that was created by Jongmin KIM (hereby referred to as "Service Provider") as a Free service. This service is intended for use "AS IS".</p>
<p><strong>Information Collection and Use</strong></p>
<p>The Application does not collect any personally identifiable information. All data, such as quiz results and study notes, is stored locally on your device and is not transmitted to the Service Provider or any third parties.</p>
<p>The Application uses Google AdMob for advertising, which may collect non-personally identifiable information to serve ads. For more information, please review Google's Privacy Policy.</p>
<p><strong>Third Party Access</strong></p>
<p>The Application utilizes third-party services that have their own Privacy Policy. Below is the link to the Privacy Policy of the third-party service provider used by the Application:<br>
<a href="https://www.google.com/policies/privacy/">Google Play Services & AdMob</a></p>
<p><strong>Opt-Out Rights</strong></p>
<p>You can stop all collection of information by the Application easily by uninstalling it.</p>
<p><strong>Children's Privacy</strong></p>
<p>The Application does not address anyone under the age of 13. The Service Provider does not knowingly collect personally identifiable information from children under 13.</p>
<p><strong>Security</strong></p>
<p>All user data is stored on the device, ensuring that your information remains private and secure.</p>
<p><strong>Changes</strong></p>
<p>This Privacy Policy may be updated from time to time. You are advised to consult this Privacy Policy regularly for any changes.</p>
<p>This privacy policy is effective as of {today}</p>
<p><strong>Contact Us</strong></p>
<p>If you have any questions regarding privacy while using the Application, please contact the Service Provider via email at bombezzang100@gmail.com.</p>
"""
    policy_text = template
    title = f"{app_name_val} - 기출문제 Privacy and Policy"
    hashtags = f"{app_name_val},privacy,policy"
    try:
        response = blog_posting(BLOG_ID, title, policy_text, hashtags, draft=False)
        if response and 'url' in response:
            generated_privacy_policy_url = response['url']
            update_progress("✅ 개인정보처리방침 포스트가 블로그에 업데이트 되었습니다: " + generated_privacy_policy_url)
        else:
            update_progress("⚠️ 개인정보처리방침 포스트 생성에 실패하였습니다.")
            generated_privacy_policy_url = "https://grea.site/2024/10/07/%EC%95%B1-%EC%A7%80%EC%9B%90-%EC%A0%95%EB%B3%B4/" # Fallback URL
    except Exception as e:
        update_progress(f"⚠️ 개인정보처리방침 생성 중 오류 발생: {e}")
        generated_privacy_policy_url = "https://grea.site/2024/10/07/%EC%95%B1-%EC%A7%80%EC%9B%90-%EC%A0%95%EB%B3%B4/" # Fallback URL


def save_config(selected_folder, bundle_id_val, app_name_val):
    """앱 설정을 app_config.json 파일로 저장합니다."""
    update_progress("\n--- app_config.json 생성 시작 ---")
    user_input_id = bundle_id_val
    project_folder = os.path.join(selected_folder, user_input_id)
    # 실제 bundle ID는 com.example.{bundle_id} 형식
    full_bundle_id = f"com.example.{user_input_id}"
    ios_folder = os.path.join(project_folder, "ios")
    if not os.path.exists(ios_folder):
        update_progress(f"⚠️ 오류: iOS 폴더를 찾을 수 없습니다: {ios_folder}")
        return

    config_json_path = os.path.join(ios_folder, "app_config.json")
    pubspec_path = os.path.join(project_folder, "pubspec.yaml")
    
    # pubspec.yaml에서 버전 정보 읽기
    version_str, build_number_str = "1.0.0", "1"
    if os.path.exists(pubspec_path):
        try:
            with open(pubspec_path, "r", encoding="utf-8") as f:
                pubspec_data = yaml.safe_load(f)
                version_line = pubspec_data.get('version', '1.0.0+1')
                version_str, build_number_str = version_line.split('+')
        except Exception as e:
            update_progress(f"⚠️ pubspec.yaml에서 버전 정보 읽기 실패: {e}")
    else:
        update_progress(f"경고: pubspec.yaml 파일이 없습니다: {pubspec_path}")

    db_count = get_db_count(project_folder) # 프로젝트 폴더 내의 assets 폴더 기준

    description_template = (
        f"""{app_name_val} 자격증 합격? 이 앱 하나면 끝!

* 주요 기능*
- 최신 기출문제 {db_count}세트!
- 연도별, 과목별 기출문제 풀기
- 기출문제 음성듣기
- 랜덤 문제 풀기
- 모든 문제 해설 제공
- 오답노트: 틀린 문제만 자동 저장
- 즐겨찾기 기능: 내가 찜한 문제를 다시 복습
- Wifi, 인터넷 없이도 사용 가능
- 완전 무료

지하철 및 이동중에도 , 언제 어디서나 간편하게 기출문제를 풀고, 실력을 완성하세요. 합격에 필요한 모든 것!
이 앱만 있으면 {app_name_val} 자격증을 손에 넣을 수 있습니다.
"""
    )
    
    config = {
        "bundle_id": full_bundle_id,
        "app_name": f"{app_name_val}-기출문제,음성듣기,해설강의",
        "version": version_str,
        "build_number": build_number_str,
        "description": description_template,
        "privacy_url": generated_privacy_policy_url,
        "keywords": [
            f"{app_name_val}", f"{app_name_val} 기출문제", f"{app_name_val} 필기",
            f"{app_name_val} 자격증", f"{app_name_val} 해설", f"{app_name_val} 오답노트",
            "자격증", "기출문제"
        ],
        # ★★★★★ 수정된 부분 시작 ★★★★★
        "categories": ["EDUCATION", "PRODUCTIVITY"],
        # ★★★★★ 수정된 부분 끝 ★★★★★
        "screenshot_folder": os.path.join(selected_folder, "Screenshots"),
        "metadata": {
            "support_url": "https://grea.site/2024/10/07/%EC%95%B1-%EC%A7%80%EC%9B%90-%EC%A0%95%EB%B3%B4/",
            "marketing_url": "https://bangkokwalkerr.blogspot.com/",
            "copyright": f"{datetime.date.today().year} Jongmin Kim",
            "contact_name": "Jongmin KIM",
            "contact_phone": "+821020221026",
            "contact_email": "bombezzang100@gmail.com",
            "requires_login": False,
            "primary_language": "ko",
            # ★★★★★ 수정된 부분 시작 ★★★★★
            "third_party_content": False,
            "age_rating_declaration": {
                "violence_cartoon_or_fantasy": "NONE",
                "violence_realistic": "NONE",
                "violence_prolonged_graphic_or_sadistic": "NONE",
                "profanity_or_crude_humor": "NONE",
                "mature_or_suggestive_themes": "NONE",
                "horror_or_fear_themes": "NONE",
                "medical_or_treatment_information": "NONE",
                "alcohol_tobacco_or_drug_use_or_references": "NONE",
                "simulated_gambling": "NONE",
                "sexual_content_or_nudity": "NONE",
                "graphic_sexual_content_and_nudity": "NONE",
                "unrestricted_web_access": False,
                "gambling_and_contests": False
            },
            # ★★★★★ 수정된 부분 끝 ★★★★★
            "price": 0.0,
            "available_countries": 175,
            "personal_data_collected": False
        }
    }

    try:
        with open(config_json_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        update_progress(f"✅ Step 11: app_config.json 저장 완료 ({config_json_path})")
    except Exception as e:
        update_progress(f"⚠️ app_config.json 저장 오류: {e}")

def create_app(selected_folder=None, bundle_id=None, app_name=None):
    """Flutter 앱 생성을 시작하고 모든 단계를 조율하는 메인 함수."""
    update_progress(f"--- Flutter 프로젝트 생성 시작 ---")
    update_progress(f"선택된 폴더: {selected_folder}")
    update_progress(f"Bundle ID: {bundle_id}")
    update_progress(f"앱 이름: {app_name}")

    if not all([selected_folder, bundle_id, app_name]):
        update_progress("⚠️ 오류: 폴더, Bundle ID, 앱 이름이 모두 필요합니다!")
        return

    # --- Step 1: `flutter create` 실행 ---
    update_progress("\n--- Step 1: Flutter 프로젝트 생성 ---")
    command = f"flutter create --org com.example --project-name {bundle_id} ."
    project_path = os.path.join(selected_folder, bundle_id)
    os.makedirs(project_path, exist_ok=True)
    
    try:
        process = subprocess.Popen(command, cwd=project_path, shell=True, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            update_progress(f"⚠️ 앱 생성 실패:\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            return
        update_progress("✅ Step 1: Flutter 프로젝트 생성 완료")
    except Exception as e:
        update_progress(f"⚠️ 앱 생성 중 예외 발생: {e}")
        return

    # --- Step 2 ~ 11: 순차적 프로세스 실행 (의존성 순서에 맞게 재정렬) ---
    # 1. 기본 파일/폴더 준비
    update_lib(selected_folder, bundle_id, app_name)
    update_db_assets(selected_folder, bundle_id, app_name)
    
    # 2. constants.dart 업데이트 (lib, assets 폴더 모두 필요)
    update_date(selected_folder, bundle_id)
    update_category(selected_folder, bundle_id)
    
    # 3. 핵심 강의 파일 업데이트 (완성된 constants.dart 및 assets/output 필요)
    update_summary_files(selected_folder, bundle_id)
    
    # 4. 나머지 설정 진행
    copy_integration_tests(selected_folder, bundle_id)
    edit_pubspec(selected_folder, bundle_id, app_name)
    edit_info_plist(selected_folder, bundle_id, app_name)
    edit_appname(selected_folder, bundle_id, app_name)
    edit_splash_screen(selected_folder, bundle_id, app_name)
    # ★★★★★ NEW FUNCTION CALL START ★★★★★
    add_imports_to_ox_quiz_page(selected_folder, bundle_id)
    # ★★★★★ NEW FUNCTION CALL END ★★★★★
    insert_logo(selected_folder, bundle_id)
    
    # 5. 최종 단계
    finalize_process(selected_folder, bundle_id, app_name)


def update_lib(selected_folder, bundle_id_val, app_name_val):
    """lib 폴더의 내용을 교체합니다."""
    update_progress("\n--- Step 2: lib 폴더 업데이트 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    lib_folder = os.path.join(project_folder, "lib")
    
    # 소스 폴더 경로 (하드코딩된 경로)
    source_folder = "/Users/jongminkim/Desktop/Apps/qcjongmin/DbMachine3/FinalDbmachine/35/lib36"
    
    if not os.path.exists(source_folder):
        update_progress(f"⚠️ 소스 lib 폴더를 찾을 수 없습니다: {source_folder}")
        return

    try:
        if os.path.exists(lib_folder):
            shutil.rmtree(lib_folder)
        shutil.copytree(source_folder, lib_folder)
        update_progress("✅ Step 2: lib 폴더 업데이트 완료")
    except Exception as e:
        update_progress(f"⚠️ lib 업데이트 오류: {e}")


def update_summary_files(selected_folder, bundle_id_val):
    """
    constants.dart, 2.txt를 기반으로 summary_lectureX.dart 파일들과
    summary_select.dart를 동적으로 생성 및 업데이트합니다.
    """
    update_progress("\n--- Step 2.5: 핵심강의 파일(Summary Lectures) 업데이트 시작 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    lib_folder = os.path.join(project_folder, "lib")
    output_folder = os.path.join(project_folder, "assets", "output")
    constants_path = os.path.join(lib_folder, "constants.dart")

    if not os.path.exists(constants_path):
        update_progress(f"⚠️ '핵심강의 업데이트' 건너뛰기: constants.dart 파일을 찾을 수 없습니다: {constants_path}")
        return
    if not os.path.exists(output_folder):
        update_progress(f"⚠️ '핵심강의 업데이트' 건너뛰기: output 폴더를 찾을 수 없습니다: {output_folder}")
        return

    try:
        update_progress(f"1. '{constants_path}'에서 카테고리 정보 읽기...")
        with open(constants_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        categories_match = re.search(r'final List<String> categories = \[(.*?)\];', content, re.DOTALL)
        if not categories_match:
            update_progress("⚠️ '핵심강의 업데이트' 건너뛰기: constants.dart에서 'categories' 목록을 찾을 수 없습니다.")
            return

        categories_str = categories_match.group(1).strip()
        categories = re.findall(r"['\"]([^'\"]+)['\"]", categories_str)
        
        # ★★★★★ 수정된 부분 시작 ★★★★★
        # 오디오 생성 스크립트(4_StudyNote.py)와의 정렬 순서를 맞추기 위해
        # 카테고리 리스트를 알파벳 순으로 정렬합니다.
        categories.sort()
        update_progress(f"   - 발견된 카테고리 (정렬됨): {categories}")
        # ★★★★★ 수정된 부분 끝 ★★★★★

        if not categories:
            update_progress("⚠️ 카테고리가 비어있어 업데이트를 진행할 수 없습니다.")
            return

        update_progress("2. 카테고리별 summary_lectureX.dart 파일 생성...")
        lecture1_path = os.path.join(lib_folder, "summary_lecture1.dart")
        if not os.path.exists(lecture1_path):
            update_progress(f"⚠️ '핵심강의 업데이트' 건너뛰기: 템플릿 파일(summary_lecture1.dart)이 없습니다.")
            return

        with open(lecture1_path, 'r', encoding='utf-8') as f:
            lecture1_content = f.read()

        for i, category in enumerate(categories, 1):
            if i == 1: 
                continue 
            
            new_lecture_path = os.path.join(lib_folder, f"summary_lecture{i}.dart")
            new_content = lecture1_content.replace("SummaryLecture1Page", f"SummaryLecture{i}Page")
            new_content = re.sub(r"lecture1\.mp3", f"lecture{i}.mp3", new_content)
            with open(new_lecture_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            update_progress(f"   - '{os.path.basename(new_lecture_path)}' 생성 완료.")

        update_progress("3. 각 강의 파일에 studyNotes 내용 업데이트...")
        for i, category in enumerate(categories, 1):
            lecture_path = os.path.join(lib_folder, f"summary_lecture{i}.dart")
            txt_path = os.path.join(output_folder, category, "2.txt")

            if not os.path.exists(txt_path):
                update_progress(f"   - 경고: '{txt_path}' 파일이 없어 '{os.path.basename(lecture_path)}' 업데이트를 건너뜁니다.")
                continue
            
            update_progress(f"   - '{os.path.basename(txt_path)}' 파일 읽는 중...")
            with open(txt_path, 'r', encoding='utf-8') as f:
                txt_content = f.read()

            dart_map_code = parse_txt_to_dart(txt_content)
            
            with open(lecture_path, 'r', encoding='utf-8') as f:
                lecture_content = f.read()

            updated_lecture_content = re.sub(
                r'final Map<String, Map<String, dynamic>> studyNotes = \{.*?\};',
                dart_map_code,
                lecture_content,
                flags=re.DOTALL
            )
            
            with open(lecture_path, 'w', encoding='utf-8') as f:
                f.write(updated_lecture_content)
            update_progress(f"   - ✅ '{os.path.basename(lecture_path)}' 업데이트 완료.")

        update_progress("4. summary_select.dart 파일 업데이트...")
        summary_select_path = os.path.join(lib_folder, "summary_select.dart")
        if os.path.exists(summary_select_path):
            import_statements = "\n".join([f"import 'summary_lecture{i}.dart';" for i in range(1, len(categories) + 1)])
            
            nav_logic = ""
            for i, category in enumerate(categories, 1):
                nav_logic += f"""
    {'else ' if i > 1 else ''}if (category == '{category}') {{
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => SummaryLecture{i}Page(dbPath: 'assets/your_database.db'),
        ),
      );
    }}"""
            
            full_nav_function = f"""void _navigateToSummaryPage(String category) {{
    {nav_logic.strip()}
  }}"""

            with open(summary_select_path, 'r', encoding='utf-8') as f:
                select_content = f.read()
            
            last_import_match = list(re.finditer(r"^(import .*?;\n)", select_content, re.MULTILINE))
            if last_import_match:
                insert_pos = last_import_match[-1].end()
                select_content = select_content[:insert_pos] + import_statements + '\n' + select_content[insert_pos:]
                update_progress("   - Import 구문 추가 완료.")
            else:
                update_progress("   - 경고: summary_select.dart에서 import 위치를 찾지 못했습니다.")

            if "_navigateToSummaryPage" in select_content:
                select_content = re.sub(
                    r"void _navigateToSummaryPage\(String category\)\s*\{[\s\S]*?\}",
                    full_nav_function,
                    select_content,
                    flags=re.DOTALL
                )
                update_progress("   - 네비게이션(_navigateToSummaryPage) 로직 업데이트 완료.")
            else:
                 update_progress("   - 경고: _navigateToSummaryPage 함수를 찾지 못해 업데이트하지 못했습니다.")

            with open(summary_select_path, 'w', encoding='utf-8') as f:
                f.write(select_content)
            update_progress(f"   - ✅ '{os.path.basename(summary_select_path)}' 파일 저장 완료.")

        update_progress("✅ Step 2.5: 핵심강의 파일 업데이트 완료")

    except Exception as e:
        update_progress(f"⚠️ 핵심강의 파일 업데이트 중 심각한 오류 발생: {e}")
        import traceback
        update_progress(traceback.format_exc())

def parse_txt_to_dart(txt_content):
    """2.txt 파일 내용을 파싱하여 Dart 맵 코드로 변환하는 헬퍼 함수"""
    dart_code = "final Map<String, Map<String, dynamic>> studyNotes = {\n"
    topics = txt_content.strip().split('---')

    for topic in topics:
        topic = topic.strip()
        if not topic:
            continue

        lines = topic.split('\n')
        title_line = lines[0].strip()
        
        if not re.match(r'^\d+\.', title_line):
            continue

        description_lines = []
        related_questions = []
        is_question_section = False

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue

            if "관련 문제:" in line:
                is_question_section = True
                continue

            if is_question_section:
                # 날짜 및 ID 파싱 로직 수정
                date_match = re.search(r'(\d{4})년\s*(\d{1,2})월', line)
                if date_match:
                    year, month = date_match.groups()
                    # Dart 코드와 일관된 형식으로 날짜 생성 ('2022년 4월')
                    date_for_dart = f"{year}년 {int(month)}월"
                    ids_match = re.search(r'Question_id:\s*([\d,\s]+)', line)
                    if ids_match:
                        question_ids = [int(q_id.strip()) for q_id in ids_match.group(1).split(',')]
                        for q_id in question_ids:
                           related_questions.append(f"      {{'date': '{date_for_dart}', 'question_id': {q_id}}},\n")
            else:
                description_lines.append(line.replace("'''", "'' '")) # Dart의 삼중 따옴표 오류 방지

        escaped_title = json.dumps(title_line, ensure_ascii=False)
        description_text = '\n'.join(description_lines)
        
        dart_code += f"  {escaped_title}: {{\n"
        dart_code += f"    'description':\n        '''{description_text}''',\n"
        dart_code += "    'related_questions': [\n"
        
        unique_questions = sorted(list(set(related_questions)))
        dart_code += "".join(unique_questions)
        
        dart_code += "    ],\n"
        dart_code += "  },\n"

    dart_code += "};"
    return dart_code


def copy_integration_tests(selected_folder, bundle_id_val):
    """
    integration_test, test_driver 폴더 및 관련 스크립트를 복사하고,
    Dart 테스트 파일 내의 프로젝트 패키지명만 선택적으로 수정합니다.
    """
    project_folder = os.path.join(selected_folder, bundle_id_val)
    update_progress("\n--- Step 3: 테스트 폴더 및 스크립트 복사 ---")

    def ignore_patterns(path, names):
        return {'mini_integration'}

    try:
        source_test_driver = "/Users/jongminkim/Desktop/Apps/qcjongmin/appauto/test_driver"
        dst_test_driver = os.path.join(project_folder, "test_driver")
        if os.path.exists(dst_test_driver):
            shutil.rmtree(dst_test_driver)
        shutil.copytree(source_test_driver, dst_test_driver)
        update_progress("test_driver 폴더 복사 완료.")
    except Exception as e:
        update_progress(f"⚠️ test_driver 폴더 복사 오류: {e}")

    try:
        source_integration = "/Users/jongminkim/Desktop/Apps/qcjongmin/appauto/integration_test"
        dst_integration = os.path.join(project_folder, "integration_test")
        if os.path.exists(dst_integration):
            shutil.rmtree(dst_integration)
        shutil.copytree(source_integration, dst_integration, ignore=ignore_patterns, dirs_exist_ok=True)
        update_progress("integration_test 폴더 복사 완료.")

        ignore_package_names = ['flutter', 'provider', 'flutter_test', 'integration_test']

        for test_file_name in ["main_test.dart", "my_app_test.dart"]:
            test_file_path = os.path.join(dst_integration, test_file_name)
            if os.path.exists(test_file_path):
                try:
                    with open(test_file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    new_lines = []
                    content_changed = False
                    
                    for line in lines:
                        match = re.search(r"import\s+['\"]package:([^/]+)/", line)
                        
                        if match:
                            package_name = match.group(1)
                            if package_name not in ignore_package_names:
                                new_line = re.sub(r"package:[^/]+", f"package:{bundle_id_val}", line)
                                new_lines.append(new_line)
                                if new_line != line:
                                    content_changed = True
                            else:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)
                    
                    if content_changed:
                        with open(test_file_path, "w", encoding="utf-8") as f:
                            f.writelines(new_lines)
                        update_progress(f"{test_file_name}의 패키지명 수정 완료.")
                except Exception as e:
                    update_progress(f"⚠️ {test_file_name} 수정 오류: {e}")
    except Exception as e:
        update_progress(f"⚠️ integration_test 폴더 복사/수정 오류: {e}")

    try:
        source_script = "/Users/jongminkim/Desktop/Apps/qcjongmin/appauto/run_screenshots.sh"
        dst_script = os.path.join(project_folder, "run_screenshots.sh")
        if os.path.exists(source_script):
            shutil.copy(source_script, dst_script)
            update_progress("run_screenshots.sh 스크립트 복사 완료.")
        else:
            update_progress(f"⚠️ run_screenshots.sh 소스 파일을 찾을 수 없습니다: {source_script}")
    except Exception as e:
        update_progress(f"⚠️ run_screenshots.sh 복사 오류: {e}")



def update_db_assets(selected_folder, bundle_id_val, app_name_val):
    """assets 폴더로 DB 및 기타 에셋 폴더들을 복사합니다."""
    update_progress("\n--- Step 4: DB 및 Asset 파일 복사 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    flutter_assets_folder = os.path.join(project_folder, "assets")
    os.makedirs(flutter_assets_folder, exist_ok=True)
    
    source_assets_folder = os.path.join(selected_folder, "assets")
    if not os.path.exists(source_assets_folder):
        update_progress(f"⚠️ 원본 assets 폴더를 찾을 수 없습니다: {source_assets_folder}")
        return

    try:
        db_copied_count = 0
        for f in os.listdir(source_assets_folder):
            if f.lower().endswith(".db"):
                shutil.copy2(os.path.join(source_assets_folder, f), os.path.join(flutter_assets_folder, f))
                db_copied_count += 1
        if db_copied_count > 0:
            update_progress(f"DB 파일 {db_copied_count}개 복사 완료.")

        def _copy_directory_if_exists(src_parent, dst_parent, folder_name):
            source_path = os.path.join(src_parent, folder_name)
            dest_path = os.path.join(dst_parent, folder_name)
            if os.path.exists(source_path):
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(source_path, dest_path)
                update_progress(f"✅ '{folder_name}' 폴더 복사 완료.")
            else:
                update_progress(f"ℹ️ '{folder_name}' 소스 폴더가 없어 복사를 건너뜁니다: {source_path}")

        _copy_directory_if_exists(source_assets_folder, flutter_assets_folder, "audio")
        _copy_directory_if_exists(source_assets_folder, flutter_assets_folder, "audio_output")
        _copy_directory_if_exists(source_assets_folder, flutter_assets_folder, "output")

        update_progress("✅ Step 4: DB 및 Asset 파일 복사 완료")
    except Exception as e:
        update_progress(f"⚠️ 파일 복사 오류: {e}")

def edit_pubspec(selected_folder, bundle_id_val, app_name_val):
    """pubspec.yaml 파일을 수정합니다."""
    update_progress("\n--- Step 5: pubspec.yaml 파일 수정 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    pubspec_path = os.path.join(project_folder, "pubspec.yaml")

    if not os.path.exists(pubspec_path):
        update_progress(f"⚠️ pubspec.yaml 파일을 찾을 수 없습니다: {pubspec_path}")
        return

    try:
        with open(pubspec_path, "r", encoding="utf-8") as f:
            pubspec = yaml.safe_load(f)
    except Exception as e:
        update_progress(f"⚠️ pubspec.yaml 읽기 오류: {e}")
        return
    
    pubspec['name'] = bundle_id_val
    pubspec['version'] = "8.0.0+6"
    
    pubspec['dependencies'].update({
        'fluttertoast': '^8.2.8', 'sqflite': '^2.4.0', 'shared_preferences': '^2.3.2',
        'google_mobile_ads': '^4.0.0', 'path': '^1.8.0', 'in_app_purchase': '^3.2.1',
        'provider': '^6.1.2', 'fl_chart': '^0.70.2', 'url_launcher': '^6.3.1',
        'just_audio': '^0.9.46', 'in_app_review': '^2.0.10', 'app_tracking_transparency': '^2.0.4',
        'audioplayers': '^6.4.0', 'table_calendar': '^3.2.0', 'intl': '^0.20.0',
        'vector_math': '^2.1.4','flutter_html': '^3.0.0', 'font_awesome_flutter': '^10.8.0', 
    })

    if 'dev_dependencies' not in pubspec or pubspec['dev_dependencies'] is None:
        pubspec['dev_dependencies'] = {}
        
    pubspec['dev_dependencies'].update({
        'flutter_launcher_icons': '^0.13.1',
        'integration_test': {
            'sdk': 'flutter'
        }
    })
    
    pubspec['flutter_launcher_icons'] = {
        'android': True, 'ios': True,
        'image_path': "assets/splash_logo.png", 'min_sdk_android': 21
    }
    
    assets_list = []
    db_count = get_db_count(project_folder) 
    for i in range(1, db_count + 1):
        assets_list.append(f"assets/question{i}.db")
    
    assets_list.extend([
        "assets/splash_logo.png", 
        "assets/quiz.db", 
        "assets/dictionary.db",
        "assets/audio/",
        "assets/audio_output/",
        "assets/output/",
        "assets/audio_output/dictionary_audio/",
        "assets/audio/summary/"

    ])

    for i in range(1, 4):
        assets_list.append(f"assets/audio/question{i}/")

    if 'flutter' not in pubspec or pubspec['flutter'] is None:
        pubspec['flutter'] = {}
    pubspec['flutter']['assets'] = sorted(list(set(assets_list)))
    
    try:
        with open(pubspec_path, "w", encoding="utf-8") as f:
            yaml.dump(pubspec, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
        update_progress("✅ Step 5: pubspec.yaml 업데이트 완료")
    except Exception as e:
        update_progress(f"⚠️ pubspec.yaml 업데이트 오류: {e}")

def update_date(selected_folder, bundle_id_val):
    """DB 파일의 날짜 정보를 기반으로 constants.dart를 업데이트합니다."""
    update_progress("\n--- Step 6: constants.dart 날짜 정보 업데이트 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    assets_folder = os.path.join(project_folder, "assets")
    
    db_files = [f for f in os.listdir(assets_folder) if re.match(r'^question\d+\.db$', f)]
    if not db_files:
        update_progress("⚠️ assets 폴더에 questionX.db 파일이 없습니다.")
        return

    entries = []
    for file in db_files:
        db_path = os.path.join(assets_folder, file)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT Date_information FROM questions WHERE Date_information IS NOT NULL AND Date_information != '' LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                match = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월', str(row[0]))
                if match:
                    year, month = match.groups()
                    date_key = f"{year}년 {int(month)}월"
                    order_num = int(re.search(r'(\d+)', file).group(1))
                    entries.append((order_num, date_key))
        except Exception as e:
            update_progress(f"⚠️ {file} 에서 날짜 정보 읽기 실패: {e}")

    if not entries:
        update_progress("⚠️ DB 파일에서 유효한 날짜를 추출할 수 없었습니다.")
        return

    entries.sort(key=lambda x: x[0])
    reverseRoundMapping = {order: date_key for order, (num, date_key) in enumerate(entries, 1)}
    
    reverseRoundMapping_str = "final Map<int, String> reverseRoundMapping = {\n" + \
                              "\n".join([f"  {k}: '{v}'," for k, v in reverseRoundMapping.items()]) + \
                              "\n};"
    
    examSessionToRoundName_str = """
String examSessionToRoundName(dynamic examVal) {
  int? intVal = (examVal is int) ? examVal : int.tryParse(examVal.toString());
  return reverseRoundMapping[intVal] ?? '기타';
}
"""
    color_definitions_str = """import 'package:flutter/material.dart';

const Color primaryColor = Color(0xFF4A90E2);
const Color secondaryColor = Color(0xFF8E9AAF);
const Color favoriteColor = Color(0xFFEC4899);

Color getPrimaryColor(bool isDarkMode) {
  return isDarkMode ? Color(0xFF8E9AAF) : Color(0xFF4A90E2);
}
"""

    constants_content = f"{color_definitions_str}\n{reverseRoundMapping_str}\n\n{examSessionToRoundName_str}"
    constants_path = os.path.join(project_folder, "lib", "constants.dart")
    try:
        with open(constants_path, "w", encoding="utf-8") as f:
            f.write(constants_content)
        update_progress("✅ Step 6: constants.dart 날짜 정보 업데이트 완료")
    except Exception as e:
        update_progress(f"⚠️ constants.dart 업데이트 중 오류 발생: {e}")

def update_category(selected_folder, bundle_id_val):
    """question1.db에서 카테고리 정보를 읽어 constants.dart에 추가합니다."""
    update_progress("\n--- Step 7: constants.dart 카테고리 정보 업데이트 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    assets_folder = os.path.join(project_folder, "assets")
    question_db_path = os.path.join(assets_folder, "question1.db")
    if not os.path.exists(question_db_path):
        update_progress(f"⚠️ 오류: question1.db 파일이 없습니다: {question_db_path}")
        return

    try:
        conn = sqlite3.connect(question_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT Category FROM questions ORDER BY Question_id")
        
        seen = set()
        categories = []
        for row in cursor.fetchall():
            category = row[0]
            if category and category not in seen:
                seen.add(category)
                categories.append(category)
                
        conn.close()
    except Exception as e:
        update_progress(f"⚠️ DB 조회 오류: {e}")
        return

    if categories:
        categories_str = "final List<String> categories = [\n" + ",\n".join([f"  '{cat}'" for cat in categories]) + "\n];"
        constants_path = os.path.join(project_folder, "lib", "constants.dart")
        try:
            with open(constants_path, "a", encoding="utf-8") as f:
                f.write("\n\n" + categories_str)
            update_progress("✅ Step 7: constants.dart 카테고리 정보 업데이트 완료")
        except Exception as e:
            update_progress(f"⚠️ constants.dart 업데이트 중 오류 발생: {e}")

def edit_info_plist(selected_folder, bundle_id_val, app_name_val):
    """Info.plist 파일을 수정합니다."""
    update_progress("\n--- Step 8: Info.plist 파일 수정 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    info_plist_path = os.path.join(project_folder, "ios", "Runner", "Info.plist")
    
    if not os.path.exists(info_plist_path):
        update_progress(f"⚠️ 오류: Info.plist 파일을 찾을 수 없습니다: {info_plist_path}")
        return

    try:
        with open(info_plist_path, "rb") as f:
            plist_data = plistlib.load(f)
        
        plist_data.update({
            "CFBundleDisplayName": app_name_val,
            "CFBundleName": bundle_id_val,
            "GADApplicationIdentifier": "ca-app-pub-2598779635969436~7514788278",
            "NSMicrophoneUsageDescription": "이 앱은 오디오 재생 기능만 사용하며, 마이크는 사용하지 않습니다. 이 설명은 외부 라이브러리의 요구 사항을 준수하기 위해 추가되었습니다.",
            "NSUserTrackingUsageDescription": "관심 없는 광고를 보지않기 위해 '허용'을 눌러주세요. '허용'을 눌러도 개인정보가 유출되지 않으니 안심하세요",
            "SKAdNetworkItems": [{"SKAdNetworkIdentifier": "cstr6suwn9.skadnetwork"}],
            "UIApplicationSupportsIndirectInputEvents": True
        })

        with open(info_plist_path, "wb") as f:
            plistlib.dump(plist_data, f)
        update_progress("✅ Step 8: Info.plist 업데이트 완료")
    except Exception as e:
        update_progress(f"⚠️ Info.plist 수정 중 오류 발생: {e}")
        
def edit_appname(selected_folder, bundle_id_val, app_name_val):
    """Dart 파일 내의 앱 이름을 변경합니다."""
    update_progress("\n--- Step 9: Dart 파일 내 앱 이름 변경 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    home_dart_path = os.path.join(project_folder, "lib", "home.dart")
    if not os.path.exists(home_dart_path):
        update_progress(f"⚠️ home.dart 파일을 찾을 수 없어 건너뜁니다: {home_dart_path}")
        return

    try:
        with open(home_dart_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("'산업안전기사'", f"'{app_name_val}'")
        content = content.replace("'산업안전기사 기출문제'", f"'{app_name_val} 기출문제'")
        with open(home_dart_path, "w", encoding="utf-8") as f:
            f.write(content)
        update_progress("✅ Step 9: home.dart의 앱 이름 변경 완료")
    except Exception as e:
        update_progress(f"⚠️ home.dart 수정 중 오류 발생: {e}")

def edit_splash_screen(selected_folder, bundle_id_val, app_name_val):
    """splash_screen.dart 파일의 앱 이름을 변경합니다."""
    update_progress("\n--- Step 9.5: 스플래시 화면 앱 이름 변경 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    splash_screen_path = os.path.join(project_folder, "lib", "splash_screen.dart")
    
    if not os.path.exists(splash_screen_path):
        update_progress(f"⚠️ splash_screen.dart 파일을 찾을 수 없어 건너뜁니다: {splash_screen_path}")
        return

    try:
        with open(splash_screen_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 정규식을 사용하여 "Text("...", ...)" 패턴을 찾고 내부 텍스트만 교체
        # 이렇게 하면 다른 Text 위젯에 영향을 주지 않고 목표 텍스트만 정확히 변경 가능
        content = re.sub(
            r'Text\(\s*"산업안전기사 기출문제",',
            f'Text(\n              "{app_name_val} 기출문제",',
            content
        )
        
        with open(splash_screen_path, "w", encoding="utf-8") as f:
            f.write(content)
        update_progress(f"✅ Step 9.5: splash_screen.dart의 앱 이름 변경 완료")
    except Exception as e:
        update_progress(f"⚠️ splash_screen.dart 수정 중 오류 발생: {e}")


# ★★★★★ NEW FUNCTION DEFINITION START ★★★★★
def add_imports_to_ox_quiz_page(selected_folder, bundle_id_val):
    """ox_quiz_page.dart 파일에 특정 import 구문을 추가합니다."""
    update_progress("\n--- Step 9.7: ox_quiz_page.dart import 구문 추가 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    ox_quiz_page_path = os.path.join(project_folder, "lib", "ox_quiz_page.dart")

    if not os.path.exists(ox_quiz_page_path):
        update_progress(f"⚠️ ox_quiz_page.dart 파일을 찾을 수 없어 건너뜁니다: {ox_quiz_page_path}")
        return

    imports_to_add_str = (
        f"\nimport 'package:{bundle_id_val}/widgets/common/common_header_widget.dart';"
        f"\nimport 'package:{bundle_id_val}/widgets/common/themed_background_widget.dart';"
    )

    try:
        with open(ox_quiz_page_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 이미 구문이 존재하는지 확인하여 중복 추가 방지
        if f"package:{bundle_id_val}/widgets/common/common_header_widget.dart" in content and \
           f"package:{bundle_id_val}/widgets/common/themed_background_widget.dart" in content:
            update_progress(f"ℹ️ ox_quiz_page.dart에 필요한 import 구문이 이미 존재합니다.")
            return

        # 마지막 import 문을 찾아 그 뒤에 삽입
        last_import_match = list(re.finditer(r"^(import .*?;\n)", content, re.MULTILINE))
        if last_import_match:
            insert_pos = last_import_match[-1].end() -1 # Get position before the newline
            new_content = content[:insert_pos] + imports_to_add_str + content[insert_pos:]
        else:
            # import문이 없는 경우 (매우 드문 경우), 파일 최상단에 추가
            new_content = imports_to_add_str.strip() + '\n\n' + content

        with open(ox_quiz_page_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        update_progress("✅ Step 9.7: ox_quiz_page.dart에 import 구문 추가 완료")

    except Exception as e:
        update_progress(f"⚠️ ox_quiz_page.dart 수정 중 오류 발생: {e}")
# ★★★★★ NEW FUNCTION DEFINITION END ★★★★★


def insert_logo(selected_folder, bundle_id_val):
    """
    Resizes the splash logo to 1024x1024, copies it, and runs the
    flutter_launcher_icons tool to generate app icons.
    """
    update_progress("\n--- Step 10: 로고 및 아이콘 생성 ---")
    project_folder = os.path.join(selected_folder, bundle_id_val)
    flutter_assets_folder = os.path.join(project_folder, "assets")

    source_logo_path = os.path.join(selected_folder, "assets", "splash_logo.png")
    
    if not os.path.exists(source_logo_path):
        update_progress(f"⚠️ 아이콘 생성 오류: 소스 파일을 찾을 수 없습니다: {source_logo_path}")
        return

    try:
        with Image.open(source_logo_path) as img:
            if img.size != (1024, 1024):
                update_progress(f"이미지 리사이즈 중... (원본: {img.size}) -> (1024, 1024)")
                resized_img = img.resize((1024, 1024), Image.LANCZOS)
                resized_img.save(source_logo_path)
                update_progress("✅ splash_logo.png 이미지 리사이즈 완료.")
            else:
                update_progress("ℹ️ splash_logo.png 이미지가 이미 1024x1024 사이즈입니다.")
    except Exception as e:
        update_progress(f"⚠️ 이미지 리사이즈 중 오류 발생: {e}")
        return

    try:
        os.makedirs(flutter_assets_folder, exist_ok=True)
        dest_logo_path = os.path.join(flutter_assets_folder, "splash_logo.png")
        shutil.copy2(source_logo_path, dest_logo_path)
        update_progress(f"✅ splash_logo.png를 Flutter 프로젝트의 assets 폴더로 복사했습니다.")
    except Exception as e:
        update_progress(f"⚠️ splash_logo.png 복사 중 오류 발생: {e}")
        return

    update_progress("`flutter pub run flutter_launcher_icons` 실행 중...")
    try:
        command = "flutter pub run flutter_launcher_icons:main"
        result = subprocess.run(
            command, 
            cwd=project_folder, 
            shell=True, 
            check=True, 
            text=True, 
            capture_output=True
        )
        update_progress("✅ Step 10: 로고 및 아이콘 생성 완료")
    except subprocess.CalledProcessError as e:
        update_progress(f"⚠️ 아이콘 생성 스크립트 실행 중 오류 발생:")
        update_progress(e.stderr)
    except Exception as e:
        update_progress(f"⚠️ insert_logo 작업 중 예측하지 못한 오류 발생: {e}")


def create_app_privacy_json(selected_folder, bundle_id_val):
    """App Privacy 상세 정보 JSON 파일을 생성합니다."""
    update_progress("\n--- App Privacy JSON 파일 생성 시작 ---")
    
    # 저장할 JSON 데이터 정의
    privacy_data = {
      "version": "1",
      "privacy_declarations": [
        {
          "privacy_types": [
            {
              "data_category": "IDENTIFIERS",
              "data_type": "DEVICE_ID",
              "is_linked": False,
              "is_tracked": True,
              "purposes": [
                "THIRD_PARTY_ADVERTISING"
              ]
            },
            {
              "data_category": "USAGE_DATA",
              "data_type": "ADVERTISING_DATA",
              "is_linked": False,
              "is_tracked": True,
              "purposes": [
                "THIRD_PARTY_ADVERTISING"
              ]
            }
          ]
        }
      ]
    }

    # 저장할 경로 설정
    project_folder = os.path.join(selected_folder, bundle_id_val)
    fastlane_folder = os.path.join(project_folder, "ios", "fastlane")
    
    try:
        # fastlane 폴더가 없으면 생성
        os.makedirs(fastlane_folder, exist_ok=True)
    except Exception as e:
        update_progress(f"⚠️ fastlane 폴더 생성 중 오류 발생: {e}")
        return

    # JSON 파일 저장
    file_path = os.path.join(fastlane_folder, "app_privacy_details.json")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(privacy_data, f, indent=2, ensure_ascii=False)
        update_progress(f"✅ App Privacy JSON 파일 생성 완료: {file_path}")
    except Exception as e:
        update_progress(f"⚠️ app_privacy_details.json 파일 저장 중 오류 발생: {e}")

def create_iap_package(selected_folder, bundle_id_val):
    """제공된 정보를 바탕으로 In-App Purchase(.itmsp) 패키지를 생성합니다."""
    update_progress("\n--- In-App Purchase 패키지 생성 시작 ---")

    # IAP 기본 정보 설정
    product_id = f"ad_remove_{bundle_id_val}"
    reference_name = "광고제거"
    price_tier = "8" # 8,800 KRW는 보통 Tier 8에 해당합니다. (App Store Connect에서 확인 필요)
    
    # 심사 정보 설정
    review_screenshot_path = "/Users/jongminkim/Desktop/Apps/qcjongmin/DbMachine3/FinalDbmachine/35/IMG_6568.PNG"
    review_notes = "본 앱은 비소모성 인앱 구매를 통해 ‘광고 제거’ 기능을 제공합니다. 사용자가 ‘광고 제거 구매하기’를 선택하여 결제하면, 결제 완료 후 SharedPreferences에 구매 내역이 저장되고 전역 변수(adsRemovedGlobal)가 업데이트되어 앱 내 모든 광고(배너, 전면, 보상형 등)가 제거됩니다. 또한, ‘구매 복원하기’ 기능을 통해 기기 변경이나 앱 재설치 후에도 구매 내역이 복원되어 광고 제거 상태가 유지됩니다. 심사 시, 제공된 샌드박스 테스터 계정을 사용하여 인앱 구매 및 복원 플로우를 테스트해 주시기 바랍니다. 구매 전후 UI에서 광고가 정상적으로 노출되거나 제거되는 것을 확인하실 수 있습니다."
    
    # .itmsp 패키지 경로 설정
    project_folder = os.path.join(selected_folder, bundle_id_val)
    iap_base_folder = os.path.join(project_folder, "in_app_purchases")
    itmsp_path = os.path.join(iap_base_folder, f"{product_id}.itmsp")

    try:
        os.makedirs(itmsp_path, exist_ok=True)
    except Exception as e:
        update_progress(f"⚠️ .itmsp 폴더 생성 중 오류: {e}")
        return

    # metadata.xml 내용 생성
    # 참고: Apple의 Team ID는 12_deliver.py 스크립트에서 가져왔습니다.
    metadata_xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<package version="software5.10" xmlns="http://apple.com/itunes/importer">
    <provider>JongminKIM</provider>
    <team_id>CPHBF5XF4B</team_id>
    <software>
        <vendor_id>{bundle_id_val}</vendor_id>
        <software_metadata>
            <in_app_purchases>
                <in_app_purchase>
                    <product_id>{product_id}</product_id>
                    <reference_name>{reference_name}</reference_name>
                    <type>non-consumable</type>
                    <products>
                        <product>
                            <cleared_for_sale>true</cleared_for_sale>
                            <intervals>
                                <interval>
                                    <start_date>{datetime.date.today().strftime('%Y-%m-%d')}</start_date>
                                    <wholesale_price_tier>{price_tier}</wholesale_price_tier>
                                </interval>
                            </intervals>
                        </product>
                    </products>
                    <locales>
                        <locale name="ko-KR">
                            <title>광고 제거</title>
                            <description>1회 구매로 평생 광고제거 이용</description>
                        </locale>
                    </locales>
                    <review_notes>{review_notes}</review_notes>
                    <review_screenshot>
                        <file_name>review_screenshot.png</file_name>
                        <size>{os.path.getsize(review_screenshot_path)}</size>
                        <checksum type="md5">{subprocess.check_output(['md5', '-q', review_screenshot_path]).decode('utf-8').strip()}</checksum>
                    </review_screenshot>
                </in_app_purchase>
            </in_app_purchases>
        </software_metadata>
    </software>
</package>
"""
    
    # metadata.xml 파일 저장
    try:
        with open(os.path.join(itmsp_path, "metadata.xml"), "w", encoding="utf-8") as f:
            f.write(metadata_xml_content)
        update_progress("✅ metadata.xml 파일 생성 완료.")
    except Exception as e:
        update_progress(f"⚠️ metadata.xml 저장 오류: {e}")

    # 심사 스크린샷 복사
    try:
        if os.path.exists(review_screenshot_path):
            shutil.copy(review_screenshot_path, os.path.join(itmsp_path, "review_screenshot.png"))
            update_progress("✅ 심사 스크린샷 복사 완료.")
        else:
            update_progress(f"⚠️ 심사 스크린샷 원본 파일을 찾을 수 없습니다: {review_screenshot_path}")
    except Exception as e:
        update_progress(f"⚠️ 심사 스크린샷 복사 오류: {e}")
    
    update_progress("✅ In-App Purchase 패키지 생성 완료.")


def finalize_process(selected_folder, bundle_id_val, app_name_val):
    """모든 프로세스를 완료하고 최종 정리 작업을 수행합니다."""
    update_progress("\n--- 최종 정리 및 설정 단계 시작 ---")
    update_ad_remove(selected_folder, bundle_id_val)
    create_privacy_policy(selected_folder, app_name_val)
    create_app_privacy_json(selected_folder, bundle_id_val) # <--- 이 줄을 추가하세요.
    create_iap_package(selected_folder, bundle_id_val) # <--- 이 줄을 추가하세요.
    save_config(selected_folder, bundle_id_val, app_name_val)
    update_progress("\n==============================================")
    update_progress("✅ 모든 자동 생성 프로세스가 완료되었습니다! ✅")
    update_progress("==============================================")

def update_ad_remove(selected_folder, bundle_id_val):
    """ad_remove.dart 파일의 product ID를 bundle_id에 맞게 업데이트합니다."""
    project_folder = os.path.join(selected_folder, bundle_id_val)
    ad_remove_path = os.path.join(project_folder, "lib", "ad_remove.dart")
    
    if not os.path.exists(ad_remove_path):
        return

    try:
        with open(ad_remove_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"final\s+String\s+_adRemovalProductId\s*=\s*'.*?';", f"final String _adRemovalProductId = 'ad_remove_{bundle_id_val}';", content)
        content = re.sub(r"final\s+String\s+_supportProductId\s*=\s*'.*?';", f"final String _supportProductId = 'support_developer_{bundle_id_val}';", content)
        with open(ad_remove_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        update_progress(f"⚠️ ad_remove.dart 수정 중 오류: {e}")

# --- 블로그 포스팅 관련 함수들 ---
def get_blogger_service_obj():
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), TOKEN_FILE)
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                update_progress(f"토큰 갱신 실패: {e}, 인증 재시도")
                creds = run_oauth_flow()
        else:
            creds = run_oauth_flow()

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return discovery.build('blogger', 'v3', credentials=creds)

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_oauth_flow():
    secret_path = os.path.join(os.path.dirname(__file__), 'client_secret.json')
    if not os.path.exists(secret_path):
        secret_path = CLIENT_SECRET

    flow = InstalledAppFlow.from_client_secrets_file(secret_path, SCOPES)
    creds = flow.run_local_server(port=PORT, server_class=ReusableTCPServer)
    return creds

def blog_posting(blog_id, title, content, hashtags, draft=False):
    update_progress("블로그 포스팅 시도...")
    blogger_service = get_blogger_service_obj()
    posts = blogger_service.posts()
    data = {'title': title, 'content': content, 'labels': hashtags.split(',') if hashtags else []}
    response = posts.insert(blogId=blog_id, body=data, isDraft=draft, fetchImages=True).execute()
    update_progress("블로그 포스팅 완료, ID: " + response['id'])
    return response

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("실행 방법: python 8_AutoAppV2.py <selected_folder> <bundle_id>")
        sys.exit(1)

    selected_folder_arg = sys.argv[1]
    bundle_id_arg = sys.argv[2]
    app_name_arg = get_app_name(selected_folder=selected_folder_arg)

    try:
        create_app(
            selected_folder=selected_folder_arg, 
            bundle_id=bundle_id_arg, 
            app_name=app_name_arg
        )
    except Exception as e:
        update_progress(f"\n\nFATAL ERROR: 스크립트 실행 중 치명적인 오류 발생\n{e}")
        import traceback
        update_progress(traceback.format_exc())
