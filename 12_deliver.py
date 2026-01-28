import os
import sys
import subprocess
import json
import traceback
from datetime import datetime


def get_all_apple_countries():
    """Apple에서 지원하는 175개국의 ISO 코드를 반환합니다."""
    return [
        "AE", "AG", "AI", "AL", "AM", "AO", "AR", "AT", "AU", "AZ",
        "BB", "BD", "BE", "BF", "BG", "BH", "BJ", "BM", "BN", "BO",
        "BR", "BS", "BT", "BW", "BY", "BZ", "CA", "CG", "CH", "CL",
        "CN", "CO", "CR", "CV", "CY", "CZ", "DE", "DK", "DM", "DO",
        "DZ", "EC", "EE", "EG", "ES", "FI", "FJ", "FM", "FR", "GA",
        "GB", "GD", "GE", "GH", "GM", "GR", "GT", "GW", "GY", "HK",
        "HN", "HR", "HU", "ID", "IE", "IL", "IN", "IS", "IT", "JM",
        "JO", "JP", "KE", "KG", "KH", "KN", "KR", "KW", "KY", "KZ",
        "LA", "LB", "LC", "LK", "LR", "LT", "LU", "LV", "LY", "MA",
        "MD", "MG", "MK", "ML", "MN", "MO", "MR", "MS", "MT", "MU",
        "MW", "MX", "MY", "MZ", "NA", "NE", "NG", "NI", "NL", "NO",
        "NP", "NR", "NZ", "OM", "PA", "PE", "PG", "PH", "PK", "PL",
        "PT", "PW", "PY", "QA", "RO", "RS", "RU", "RW", "SA", "SB",
        "SC", "SE", "SG", "SI", "SK", "SL", "SN", "SR", "ST", "SV",
        "SZ", "TC", "TD", "TG", "TH", "TJ", "TM", "TN", "TR", "TT",
        "TW", "TZ", "UA", "UG", "US", "UY", "UZ", "VC", "VE", "VG",
        "VN", "VU", "WS", "YE", "ZA", "ZM", "ZW"
    ]

def update_progress(message):
    """진행 상황 메시지를 표준 출력으로 인쇄합니다."""
    print(message, flush=True)
    
def generate_metadata(project_root_folder, bundle_id):
    """app_config.json을 읽어 fastlane이 사용할 메타데이터 파일을 생성합니다."""
    update_progress("--- 메타데이터 생성 시작 ---")
    
    json_path = os.path.join(project_root_folder, bundle_id, "ios", "app_config.json")
    if not os.path.exists(json_path):
        update_progress(f"오류: 설정 파일({json_path})을 찾을 수 없습니다. '8. Create App'을 먼저 실행해야 합니다.")
        return False
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        update_progress(f"오류: {json_path} 파일 읽기 실패 - {e}")
        return False

    ios_folder = os.path.dirname(json_path)
    metadata_root = os.path.join(ios_folder, "metadata")
    metadata_ko = os.path.join(metadata_root, "ko")
    os.makedirs(metadata_ko, exist_ok=True)
    
    review_info_dir = os.path.join(metadata_root, "review_information")
    os.makedirs(review_info_dir, exist_ok=True)

    metadata_dict = config.get("metadata", {})
    contact_name_val = metadata_dict.get("contact_name", "Jongmin KIM")
    first_name, last_name = contact_name_val.split(" ", 1) if " " in contact_name_val else (contact_name_val, "")

    with open(os.path.join(review_info_dir, "first_name.txt"), "w", encoding="utf-8") as f:
        f.write(first_name)
    with open(os.path.join(review_info_dir, "last_name.txt"), "w", encoding="utf-8") as f:
        f.write(last_name)
    with open(os.path.join(review_info_dir, "phone_number.txt"), "w", encoding="utf-8") as f:
        f.write(metadata_dict.get("contact_phone", "+821020221026"))
    with open(os.path.join(review_info_dir, "email_address.txt"), "w", encoding="utf-8") as f:
        f.write(metadata_dict.get("contact_email", "bombezzang100@gmail.com"))
    with open(os.path.join(review_info_dir, "notes.txt"), "w", encoding="utf-8") as f:
        f.write(config.get("review_notes", "This app does not require a login."))
    
    update_progress(f"앱 심사 정보 파일 생성 완료: {review_info_dir}")

    with open(os.path.join(metadata_ko, "name.txt"), "w", encoding="utf-8") as f:
        f.write(config.get("app_name", ""))
    with open(os.path.join(metadata_ko, "description.txt"), "w", encoding="utf-8") as f:
        f.write(config.get("description", ""))
    with open(os.path.join(metadata_ko, "keywords.txt"), "w", encoding="utf-8") as f:
        f.write(",".join(config.get("keywords", [])))
    with open(os.path.join(metadata_ko, "privacy_url.txt"), "w", encoding="utf-8") as f:
        f.write(config.get("privacy_url", ""))
    with open(os.path.join(metadata_ko, "support_url.txt"), "w", encoding="utf-8") as f:
        f.write(metadata_dict.get("support_url", ""))
        
    copyright_info = metadata_dict.get("copyright", f"© {datetime.now().year} Jongmin Kim")
    with open(os.path.join(metadata_root, "copyright.txt"), "w", encoding="utf-8") as f:
        f.write(copyright_info)
    update_progress(f"Copyright 정보 파일 생성 완료: {copyright_info}")

    price = metadata_dict.get("price", 0.0)
    price_tier = 0 if price == 0.0 else -1 

    if price_tier != -1:
        with open(os.path.join(metadata_root, "price_tier.txt"), "w", encoding="utf-8") as f:
            f.write(str(price_tier))
        update_progress(f"가격 정보 파일 생성 완료 (Tier: {price_tier})")
    
    available_countries_count = metadata_dict.get("available_countries", 0)
    if available_countries_count == 175:
        country_list = get_all_apple_countries()
        with open(os.path.join(metadata_root, "available_countries.txt"), "w", encoding="utf-8") as f:
            for country_code in country_list:
                f.write(f"{country_code}\n")
        update_progress("출시 국가 정보 파일 생성 완료 (175개국)")

    # ★★★★★ 수정된 부분 시작 ★★★★★
    # --- 카테고리 파일 생성 ---
    categories = config.get("categories", [])
    if len(categories) > 0:
        with open(os.path.join(metadata_root, "primary_category.txt"), "w", encoding="utf-8") as f:
            f.write(categories[0])
        update_progress(f"Primary Category 파일 생성: {categories[0]}")
    if len(categories) > 1:
        with open(os.path.join(metadata_root, "secondary_category.txt"), "w", encoding="utf-8") as f:
            f.write(categories[1])
        update_progress(f"Secondary Category 파일 생성: {categories[1]}")

    # --- 연령 등급 및 콘텐츠 권한 파일 생성 ---
    age_decl = metadata_dict.get("age_rating_declaration")
    if age_decl:
        rating_data = {
            "CARTOON_FANTASY_VIOLENCE": age_decl.get("violence_cartoon_or_fantasy", "NONE"),
            "REALISTIC_VIOLENCE": age_decl.get("violence_realistic", "NONE"),
            "PROLONGED_GRAPHIC_SADISTIC_REALISTIC_VIOLENCE": age_decl.get("violence_prolonged_graphic_or_sadistic", "NONE"),
            "PROFANITY_CRUDE_HUMOR": age_decl.get("profanity_or_crude_humor", "NONE"),
            "MATURE_SUGGESTIVE": age_decl.get("mature_or_suggestive_themes", "NONE"),
            "HORROR_FEAR": age_decl.get("horror_or_fear_themes", "NONE"),
            "MEDICAL_TREATMENT_INFO": age_decl.get("medical_or_treatment_information", "NONE"),
            "ALCOHOL_TOBACCO_DRUGS": age_decl.get("alcohol_tobacco_or_drug_use_or_references", "NONE"),
            "SIMULATED_GAMBLING": age_decl.get("simulated_gambling", "NONE"),
            "SEXUAL_CONTENT_NUDITY": age_decl.get("sexual_content_or_nudity", "NONE"),
            "GRAPHIC_SEXUAL_CONTENT_NUDITY": age_decl.get("graphic_sexual_content_and_nudity", "NONE"),
            "UNRESTRICTED_WEB_ACCESS": age_decl.get("unrestricted_web_access", False),
            "GAMBLING_CONTESTS": age_decl.get("gambling_and_contests", False),
            "THIRD_PARTY_CONTENT": metadata_dict.get("third_party_content", False)
        }
        
        rating_file_path = os.path.join(metadata_root, "app_store_rating_config.json")
        with open(rating_file_path, "w", encoding="utf-8") as f:
            json.dump(rating_data, f, indent=2)
        update_progress(f"연령 등급 설정 파일 생성 완료: {rating_file_path}")
    # ★★★★★ 수정된 부분 끝 ★★★★★

    update_progress(f"✅ 메타데이터 파일 생성 완료: {metadata_root}")
    return True


def deliver_app(selected_folder, bundle_id):
    project_folder = os.path.join(selected_folder, bundle_id)
    ios_folder = os.path.join(project_folder, "ios")
    
    if not os.path.isdir(ios_folder):
        update_progress(f"오류: iOS 프로젝트 폴더({ios_folder})를 찾을 수 없습니다. '8. Create App'을 먼저 실행해야 합니다.")
        return

    if not generate_metadata(selected_folder, bundle_id):
        sys.exit(1)

    update_progress("\n=== Fastlane Deliver 시작 ===")
    app_identifier = f"com.example.{bundle_id}"

    fastlane_dir = os.path.join(ios_folder, "fastlane")
    os.makedirs(fastlane_dir, exist_ok=True)
    
    with open(os.path.join(fastlane_dir, "Appfile"), "w", encoding='utf-8') as f:
        f.write(f'app_identifier("{app_identifier}")\n')
        f.write('apple_id("bombezzang2607@gmail.com")\n')
        f.write('team_id("CPHBF5XF4B")\n')

    with open(os.path.join(fastlane_dir, "Deliverfile"), "w", encoding='utf-8') as f:
        f.write(f'app_identifier("{app_identifier}")\n')
        f.write('username("bombezzang2607@gmail.com")\n')

    update_progress("Appfile 및 Deliverfile 생성 완료.")

    metadata_path = os.path.join(ios_folder, "metadata")
    screenshots_path = os.path.join(selected_folder, "Screenshots")
    iap_path = os.path.join(project_folder, "in_app_purchases")

    command = [
        "fastlane", "deliver",
        "--skip_binary_upload", "true",
        "--force", "true",
        "--overwrite_screenshots", "true", 
        "--metadata_path", metadata_path,
        # "--in_app_purchase_path", iap_path
    ]

    if os.path.isdir(screenshots_path):
        command.extend(["--screenshots_path", screenshots_path])
        update_progress(f"스크린샷 경로 사용: {screenshots_path}")
    else:
        update_progress(f"경고: 스크린샷 폴더({screenshots_path})를 찾을 수 없어 스크린샷 업로드를 건너뜁니다.")
        command.extend(["--skip_screenshots", "true"])
        
    try:
        env = os.environ.copy()
        env["FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD"] = "huil-oazk-etxd-qmmn"
        
        update_progress(f"실행 명령어: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            cwd=ios_folder,
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
            update_progress("\n=== Fastlane Deliver 성공적으로 완료되었습니다. ===")
        else:
            update_progress(f"\n오류: Fastlane Deliver 실패 (종료 코드: {return_code})")
            sys.exit(1)

    except Exception as e:
        update_progress(f"스크립트 실행 중 예외 발생: {e}")
        update_progress(traceback.format_exc())
        sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("사용법: python 12_deliver.py <selected_folder> <bundle_id>")
        sys.exit(1)
        
    selected_folder = sys.argv[1]
    bundle_id = sys.argv[2]
    
    deliver_app(selected_folder, bundle_id)

if __name__ == "__main__":
    main()