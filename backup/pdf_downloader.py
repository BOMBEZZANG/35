import os
import re
import sys
import threading
import time
import requests
import tkinter as tk
from tkinter import ttk, messagebox
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
    name = re.sub(r'\d{8}', '', name)
    name = re.sub(r'\d+', '', name)
    return sanitize_filename(name.strip())

def download_file(file_url: str, save_path: str, log_text) -> None:
    """file_url을 GET 요청으로 다운로드하여 save_path에 저장"""
    if os.path.exists(save_path):
        log_text.insert(tk.END, f"[SKIP] 이미 다운로드된 파일: {save_path}\n")
        return
    log_text.insert(tk.END, f"[다운로드 시작] {file_url} -> {save_path}\n")
    try:
        r = requests.get(file_url, timeout=20)
        r.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(r.content)
        log_text.insert(tk.END, f"[완료] {save_path}\n")
    except Exception as e:
        log_text.insert(tk.END, f"[에러 발생] {e}\n")

def download_dbs(boards, log_text):
    """주어진 URL 리스트에서 (교사용).pdf 파일을 다운로드"""
    
    # --- ▼▼▼ 수정된 부분 ▼▼▼ ---
    # chromedriver 경로를 직접 지정하는 대신, Selenium이 자동으로 관리하도록 변경
    try:
        log_text.insert(tk.END, "ChromeDriver 자동 설정 시작...\n")
        log_text.see(tk.END)
        service = Service()
        driver = webdriver.Chrome(service=service)
        driver.implicitly_wait(3)
        log_text.insert(tk.END, "ChromeDriver 설정 완료.\n")
        log_text.see(tk.END)
    except Exception as e:
        log_text.insert(tk.END, f"ChromeDriver 초기화 실패: {e}\n")
        log_text.insert(tk.END, "오류: Chrome 브라우저가 설치되어 있는지 확인해주세요.\n")
        log_text.see(tk.END)
        messagebox.showerror("드라이버 오류", f"ChromeDriver를 초기화할 수 없습니다. Chrome 브라우저가 올바르게 설치되었는지 확인하세요.\n\n오류: {e}")
        return
    # --- ▲▲▲ 수정된 부분 ▲▲▲ ---

    try:
        for board_url in boards:
            if is_excluded(board_url):
                log_text.insert(tk.END, f"[건너뛰기] 제외 패턴에 걸린 URL: {board_url}\n")
                log_text.see(tk.END)
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
                log_text.insert(tk.END, f"[안내] 게시글이 없습니다. 스킵: {board_url}\n")
                log_text.see(tk.END)
                continue

            log_text.insert(tk.END, f"[안내] 추출된 게시글 수: {len(post_links_data)} (카테고리 URL: {board_url})\n")
            log_text.see(tk.END)

            category_folder = None

            for idx, (post_href, post_text) in enumerate(post_links_data[:8], start=1):
                log_text.insert(tk.END, f"\n - [{idx}] 게시글 방문: {post_text} | URL: {post_href}\n")
                log_text.see(tk.END)

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
                            log_text.insert(tk.END, f"[안내] 카테고리 폴더 생성: {category_folder}\n")

                        local_path = os.path.join(category_folder, sanitize_filename(fname))
                        download_file(href, local_path, log_text)
                        break

                if not found:
                    log_text.insert(tk.END, "   -> (교사용).pdf 첨부파일을 찾지 못했습니다.\n")
                log_text.see(tk.END)

            log_text.insert(tk.END, f"[완료] 카테고리 {board_url} 처리 끝.\n\n")
            log_text.see(tk.END)

    finally:
        driver.quit()
        log_text.insert(tk.END, "=== 모든 카테고리 처리 완료 ===\n")
        log_text.see(tk.END)

def start_download():
    urls = url_entry.get("1.0", tk.END).strip().splitlines()
    if not urls or all(not url.strip() for url in urls):
        messagebox.showwarning("경고", "URL을 입력해주세요.")
        return
    
    # 다운로드를 별도 스레드에서 실행하여 GUI가 멈추는 것을 방지
    download_button.config(state="disabled")
    log_text.delete("1.0", tk.END)
    
    thread = threading.Thread(target=run_download_thread, args=(urls, log_text, download_button))
    thread.daemon = True
    thread.start()

def run_download_thread(urls, log_text, button):
    """다운로드 작업을 실행하고 완료 후 버튼을 활성화하는 함수"""
    try:
        download_dbs(urls, log_text)
    except Exception as e:
        log_text.insert(tk.END, f"\n!!! 치명적인 오류 발생: {e} !!!\n")
    finally:
        button.config(state="normal")


# GUI 생성
root = tk.Tk()
root.title("PDF 다운로더")
root.geometry("600x400")

url_label = ttk.Label(root, text="다운로드할 URL을 입력하세요 (한 줄에 하나씩):")
url_label.pack(pady=5)

url_entry = tk.Text(root, height=5, width=50)
url_entry.pack(pady=5)

download_button = ttk.Button(root, text="다운로드 시작", command=start_download)
download_button.pack(pady=5)

log_label = ttk.Label(root, text="진행 상황:")
log_label.pack(pady=5)

log_text = tk.Text(root, height=15, width=70)
log_text.pack(pady=5)

url_entry.insert(tk.END, "https://www.comcbt.com/xe/iz")

root.mainloop()