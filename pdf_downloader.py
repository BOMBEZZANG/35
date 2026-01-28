# pdf_downloader.py (수정된 버전)

import os
import re
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

# --- 사용자 설정 ---
BASE_DOWNLOAD_DIR = os.path.expanduser("~/Desktop/Apps/qcjongmin/appauto/raw_DB/rawdbs")

exclude_patterns = [
    r'dispMemberLoginForm',
    r'dispMemberSignUpForm',
    r'dispMemberFindAccount',
    r'index\.php\?mid=imsigongsi&act=',
    r'index\.php\?module=lottery',
    r'webhaesul',
    r'^//',
    r'#',
    r'^https?://m\.comcbt\.com/',
]

def is_excluded(url: str) -> bool:
    """exclude_patterns에 해당하면 True 반환"""
    for pattern in exclude_patterns:
        if re.search(pattern, url):
            return True
    return False

def sanitize_filename(filename: str) -> str:
    """파일명/폴더명에 들어갈 수 없는 문자 등을 제거"""
    return re.sub(r'[\\/:*?"<>|]', '_', filename)

def extract_category_name(filename: str) -> str:
    """파일명에서 숫자와 '(교사용).pdf'를 제거하여 카테고리 이름 추출"""
    name = re.sub(r'\(교사용\)\.pdf$', '', filename)
    name = re.sub(r'\d{11}', '', name)
    name = re.sub(r'\d+', '', name)
    return sanitize_filename(name.strip())

def download_file(file_url: str, save_path: str, log_callback=None) -> None:
    """file_url을 GET 요청으로 다운로드하여 save_path에 저장"""
    if os.path.exists(save_path):
        if log_callback:
            log_callback(f"[SKIP] 이미 다운로드된 파일: {save_path}")
        return
    if log_callback:
        log_callback(f"[다운로드 시작] {file_url} -> {save_path}")
    try:
        r = requests.get(file_url, timeout=20)
        r.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(r.content)
        if log_callback:
            log_callback(f"[완료] {save_path}")
    except Exception as e:
        if log_callback:
            log_callback(f"[에러 발생] {e}")

def download_pdfs_from_urls(urls, log_callback=None):
    """주어진 URL 리스트에서 (교사용).pdf 파일을 다운로드
    
    Args:
        urls: 다운로드할 URL 리스트
        log_callback: 로그 메시지 콜백 함수
        
    Returns:
        tuple: (성공여부, 다운로드된 폴더 경로)
    """
    downloaded_folder = None
    
    try:
        if log_callback:
            log_callback("ChromeDriver 자동 설정 시작...")
        service = Service()
        driver = webdriver.Chrome(service=service)
        driver.implicitly_wait(3)
        if log_callback:
            log_callback("ChromeDriver 설정 완료.")
    except Exception as e:
        if log_callback:
            log_callback(f"ChromeDriver 초기화 실패: {e}")
            log_callback("오류: Chrome 브라우저가 설치되어 있는지 확인해주세요.")
        return False, None

    try:
        for board_url in urls:
            if is_excluded(board_url):
                if log_callback:
                    log_callback(f"[건너뛰기] 제외 패턴에 걸린 URL: {board_url}")
                continue

            driver.get(board_url)
            time.sleep(1)

            post_links_data = []
            post_links = driver.find_elements(By.CSS_SELECTOR, "table tbody tr td:nth-child(2) a")
            for link_elem in post_links:
                href = link_elem.get_attribute("href")
                text = link_elem.text.strip()
                if not is_excluded(href):
                    post_links_data.append((href, text))

            if not post_links_data:
                if log_callback:
                    log_callback(f"[안내] 게시글이 없습니다. 스킵: {board_url}")
                continue

            if log_callback:
                log_callback(f"[안내] 추출된 게시글 수: {len(post_links_data)} (카테고리 URL: {board_url})")

            category_folder = None

            for idx, (post_href, post_text) in enumerate(post_links_data[:11], start=1):
                if log_callback:
                    log_callback(f"\n - [{idx}] 게시글 방문: {post_text} | URL: {post_href}")

                driver.get(post_href)
                time.sleep(1)

                attach_links = driver.find_elements(By.CSS_SELECTOR, "div.rd_body.clear article div p a")

                found = False
                for a_elem in attach_links:
                    fname = a_elem.text.strip()
                    href = a_elem.get_attribute("href")
                    if "(교사용).pdf" in fname:
                        found = True

                        if category_folder is None:
                            category_name = extract_category_name(fname)
                            category_folder = os.path.join(BASE_DOWNLOAD_DIR, category_name)
                            os.makedirs(category_folder, exist_ok=True)
                            if log_callback:
                                log_callback(f"[안내] 카테고리 폴더 생성: {category_folder}")
                            downloaded_folder = category_folder

                        local_path = os.path.join(category_folder, sanitize_filename(fname))
                        download_file(href, local_path, log_callback)
                        break

                if not found and log_callback:
                    log_callback("   -> (교사용).pdf 첨부파일을 찾지 못했습니다.")

            if log_callback:
                log_callback(f"[완료] 카테고리 {board_url} 처리 끝.\n")

    finally:
        driver.quit()
        if log_callback:
            log_callback("=== 모든 카테고리 처리 완료 ===")

    return True, downloaded_folder


def main():
    """메인 함수 - 기본 URL에서 PDF 다운로드"""
    # 기본 URL 설정 (필요에 따라 수정)
    default_urls = ["https://www.comcbt.com/xe/iz"]  # 기본값
    
    print("PDF 다운로더 시작...")
    print(f"다운로드 경로: {BASE_DOWNLOAD_DIR}")
    
    # 다운로드 실행
    success, folder = download_pdfs_from_urls(default_urls, log_callback=print)
    
    if success and folder:
        print(f"다운로드 완료! 폴더: {folder}")
    else:
        print("다운로드 실패")

if __name__ == "__main__":
    main()