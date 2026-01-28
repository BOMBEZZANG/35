# 0_Machine.py (전체 수정)

import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import re
import threading
import sqlite3
import plistlib
from typing import List, Dict, Tuple, Optional
import sys
from pathlib import Path
import subprocess
import unicodedata
import queue
import glob

try:
    from pdf_processor import PDFProcessor
except ImportError:
    print("pdf_processor.py 파일이 필요합니다. 이 파일과 같은 폴더에 있어야 합니다.")
    sys.exit(1)
    
    
try:
    from pdf_downloader import download_pdfs_from_urls
except ImportError:
    print("pdf_downloader.py 파일이 필요합니다. 이 파일과 같은 폴더에 있어야 합니다.")
    sys.exit(1)

# ★★★★★ 사용자 설정 필요 ★★★★★
DB_BROWSER_PATH = "/Applications/DB Browser for SQLite.app/Contents/MacOS/DB Browser for SQLite"


class PDFBatchProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF/DB Batch Processor & App Creator")
        self.root.geometry("800x750") # 세로 길이 조정
        
        self.default_folder = os.path.expanduser("~/Desktop/Apps/qcjongmin/appauto/raw_DB/rawdbs/")
        self.selected_folder = ""
        
        
        
        self.setup_ui()
        self.reset_internal_state()
        self.is_one_click_running = False  # One Click 실행 상태 추가
        self.one_click_queue = queue.Queue()  # 프로세스 간 통신용 큐
        self.one_click_bundle_id = None  # One Click에서 사용할 Bundle ID 저장
        self.one_click_down_url = None  # ★ 이 줄 추가

        self.download_thread = None  # 다운로드 스레드 추가

    def reset_internal_state(self):
        """내부 처리 상태 변수들을 초기화합니다."""
        self.total_files = 0
        self.processed_files = 0
        self.failed_files = []
        self.debug_issues = []
        self.question_number_issues = []
        self.first_db_last_number = None
        self.db_last_numbers = []
        self.issue_files_to_correct = []
        self.current_correction_index = -1
        self.opened_processes = []
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # --- UI 요소들 ---
        # 폴더 선택 (row=0)
        folder_frame = ttk.LabelFrame(main_frame, text="폴더 선택", padding="5")
        folder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.folder_button = ttk.Button(folder_frame, text="Folder Selected", command=self.select_folder)
        self.folder_button.pack(side=tk.LEFT, padx=(0, 10))
        self.folder_label = ttk.Label(folder_frame, text="폴더를 선택해주세요", foreground="gray")
        self.folder_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        # 버튼 라인 1 (row=1) 수정 - One Click 버튼 추가
        button_line_1_frame = ttk.Frame(main_frame)
        button_line_1_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # One Click 버튼을 맨 앞에 추가
        self.one_click_button = ttk.Button(
            button_line_1_frame, 
            text="One Click", 
            command=self.start_one_click_process,
            style='Accent.TButton'  # 강조 스타일
        )
        self.one_click_button.pack(side=tk.LEFT, padx=5)
        
        # 구분선 추가
        ttk.Separator(button_line_1_frame, orient='vertical').pack(side=tk.LEFT, fill='y', padx=5)
        
        
        self.downloader_button = ttk.Button(button_line_1_frame, text="0. PDF 다운로드", command=self.launch_pdf_downloader)
        self.process_button = ttk.Button(button_line_1_frame, text="1. PDF -> DB", command=self.start_pdf_to_db_process, state="disabled")
        self.api_button = ttk.Button(button_line_1_frame, text="2. 해설 생성", command=lambda: self.start_external_script_process('2_pro_api.py'), state="disabled")
        self.audio_button = ttk.Button(button_line_1_frame, text="3. 음성 생성", command=lambda: self.start_external_script_process('3_description_audio.py'), state="disabled")
        self.studynote_button = ttk.Button(button_line_1_frame, text="4. Study Note", command=lambda: self.start_external_script_process('4_StudyNote.py'), state="disabled")
        self.ox_quiz_button = ttk.Button(button_line_1_frame, text="5. OX Quiz", command=lambda: self.start_external_script_process('5_OX_Quiz_Creating.py'), state="disabled")
        self.dictionary_button = ttk.Button(button_line_1_frame, text="6. 용어사전", command=lambda: self.start_external_script_process('6_dictionary.py'), state="disabled")

        for btn in [self.downloader_button, self.process_button, self.api_button, self.audio_button, self.studynote_button, self.ox_quiz_button, self.dictionary_button]:
            btn.pack(side=tk.LEFT, padx=2)

        # 버튼 라인 2 (row=2)
        button_line_2_frame = ttk.Frame(main_frame)
        button_line_2_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)

        self.mindmap_button = ttk.Button(button_line_2_frame, text="7. 마인드맵", command=lambda: self.start_external_script_process('7_mindmap.py'), state="disabled")
        self.create_app_button = ttk.Button(button_line_2_frame, text="8. Create App", command=self.start_app_creation_process, state="disabled")
        self.simple_create_button = ttk.Button(button_line_2_frame, text="Simple_Create", command=self.start_simple_create_process, state="disabled")

        self.ox_dict_mindmap_button = ttk.Button(button_line_2_frame, text="9. OX,Dict,Map", command=self.start_ox_dict_mindmap_process, state="disabled")
        self.screenshot_button = ttk.Button(button_line_2_frame, text="10. 스크린샷", command=self.start_screenshot_process, state="disabled")
        self.produce_button = ttk.Button(button_line_2_frame, text="11. Produce", command=self.start_produce_process, state="disabled")
        self.deliver_button = ttk.Button(button_line_2_frame, text="12. Deliver", command=self.start_deliver_process, state="disabled")
        self.release_button = ttk.Button(button_line_2_frame, text="13. Release", command=self.start_release_process, state="disabled")

        for btn in [self.mindmap_button, self.create_app_button, self.simple_create_button, self.ox_dict_mindmap_button, 
                    self.screenshot_button, self.produce_button, self.deliver_button, self.release_button]:
            btn.pack(side=tk.LEFT, padx=2)

        # Bundle ID 입력 (row=3)
        app_creation_frame = ttk.LabelFrame(main_frame, text="App Generation", padding="5")
        app_creation_frame.grid(row=3, column=0, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Label(app_creation_frame, text="Bundle ID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.bundle_id_entry = ttk.Entry(app_creation_frame, width=40)
        self.bundle_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        app_creation_frame.columnconfigure(1, weight=1)
        
                # Bundle ID 입력 (row=3) 다음에 Down_URL 입력칸 추가
        app_creation_frame = ttk.LabelFrame(main_frame, text="App Generation", padding="5")
        app_creation_frame.grid(row=3, column=0, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Label(app_creation_frame, text="Bundle ID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.bundle_id_entry = ttk.Entry(app_creation_frame, width=40)
        self.bundle_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        # Down_URL 입력칸 추가
        ttk.Label(app_creation_frame, text="Down URL:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.down_url_entry = ttk.Entry(app_creation_frame, width=40)
        self.down_url_entry.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        self.down_url_entry.insert(0, "https://www.comcbt.com/xe/iz")  # 기본값 설정
        
        app_creation_frame.columnconfigure(1, weight=1)

        # 처리 로그 (row=4)
        log_frame = ttk.LabelFrame(main_frame, text="처리 로그", padding="5")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10,0))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 디버그 수정 모드 (row=5) - 숨겨져 있다가 필요시 나타남
        self.correction_frame = ttk.LabelFrame(main_frame, text="디버그 수정 모드", padding="5")
        self.correction_label = ttk.Label(self.correction_frame, text="수정할 파일: 대기 중...", foreground="blue")
        self.correction_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.next_button = ttk.Button(self.correction_frame, text="다음", command=self.next_correction_file)
        self.next_button.grid(row=0, column=1, padx=5, pady=5)
        self.finish_button = ttk.Button(self.correction_frame, text="종료", command=self.finish_correction_mode)
        self.finish_button.grid(row=0, column=2, padx=5, pady=5)
        # correction_frame은 초기에 grid()에서 제외
        self.correction_frame.grid_remove() 
        self.correction_frame.grid_configure(row=5, column=0, sticky=(tk.W, tk.E), pady=10)


        # --- Grid Weight 설정 ---
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1) # 로그 프레임이 세로 공간을 차지하도록
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.correction_frame.columnconfigure(0, weight=1)
        
    def start_one_click_process(self):
        """One Click 프로세스 시작"""
        if self.is_one_click_running:
            messagebox.showwarning("경고", "One Click 프로세스가 이미 실행 중입니다.")
            return
            
        # Bundle ID 입력 확인
        bundle_id = self.bundle_id_entry.get().strip()
        if not bundle_id:
            messagebox.showerror("오류", "Bundle ID를 입력해주세요.")
            return
        
        # ★ Down URL 입력 확인 추가
        down_url = self.down_url_entry.get().strip()
        if not down_url:
            messagebox.showerror("오류", "Down URL을 입력해주세요.")
            return
        
        # One Click용 Bundle ID와 URL 저장
        self.one_click_bundle_id = bundle_id
        self.one_click_down_url = down_url  # ★ 이 줄 추가
        
        self.is_one_click_running = True
        self.set_ui_for_processing(True)
        self.one_click_button.config(state="disabled", text="실행 중...")
        
        self.log_message("\n" + "="*50)
        self.log_message("🚀 ONE CLICK 프로세스 시작")
        self.log_message(f"📝 Bundle ID: {self.one_click_bundle_id}")
        self.log_message(f"🔗 Down URL: {self.one_click_down_url}")  # ★ 이 줄 추가
        self.log_message("="*50)
        
        # PDF 다운로더 실행 및 모니터링 시작
        self.run_pdf_downloader_and_monitor()
        
    # 0_Machine.py 수정 코드
    # 0_Machine.py 수정 코드

    def run_pdf_downloader_and_monitor(self):
        """PDF 다운로더 실행 후 완료 감지"""
        self.log_message("\n[1/10] PDF 다운로드 시작...")
        
        try:
            # ★ One Click에서 저장한 URL 사용
            url = self.one_click_down_url if self.one_click_down_url else self.down_url_entry.get().strip()
            if not url:
                raise ValueError("다운로드 URL이 지정되지 않았습니다.")
                
            urls = [u.strip() for u in url.split('\n') if u.strip()]
            
            # 다운로드 경로
            raw_db_path = os.path.expanduser("~/Desktop/Apps/qcjongmin/appauto/raw_DB/rawdbs")
            
            # 다운로드 전 기존 폴더 목록 저장
            before_folders = set()
            if os.path.exists(raw_db_path):
                before_folders = {f for f in os.listdir(raw_db_path) 
                                if os.path.isdir(os.path.join(raw_db_path, f))}
            
            # 별도 스레드에서 다운로드 실행
            threading.Thread(
                target=self.one_click_download_thread,
                args=(urls, raw_db_path, before_folders),
                daemon=True
            ).start()
            
        except Exception as e:
            self.log_message(f"❌ PDF 다운로더 실행 실패: {e}")
            self.finish_one_click_process(success=False)

    def monitor_download_folder(self, process, raw_db_path, before_folders):
        """다운로드 폴더를 모니터링하여 완료 감지"""
        try:
            self.log_message("📂 다운로드 폴더 모니터링 시작...")
            
            # 새 폴더가 생성될 때까지 대기 (최대 5분)
            new_folder = None
            start_time = time.time()
            check_interval = 2  # 2초마다 확인
            max_wait_time = 300  # 최대 5분 대기
            
            while time.time() - start_time < max_wait_time:
                # 프로세스가 종료되었는지 확인
                if process.poll() is not None:
                    self.log_message("ℹ️ PDF 다운로더가 종료되었습니다.")
                    break
                
                # 새 폴더 확인
                if os.path.exists(raw_db_path):
                    current_folders = {f for f in os.listdir(raw_db_path) 
                                    if os.path.isdir(os.path.join(raw_db_path, f))}
                    new_folders = current_folders - before_folders
                    
                    if new_folders:
                        new_folder_name = list(new_folders)[0]
                        new_folder = os.path.join(raw_db_path, new_folder_name)
                        self.log_message(f"✅ 새 폴더 감지: {new_folder}")
                        
                        # 폴더 내용이 안정화될 때까지 대기
                        self.wait_for_folder_stability(new_folder)
                        break
                
                time.sleep(check_interval)
            
            # 프로세스가 아직 실행 중이면 종료
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                self.log_message("다운로더 프로세스를 종료했습니다.")
            
            # 다운로드 결과 확인
            if new_folder and os.path.exists(new_folder):
                # PDF 파일이 있는지 확인
                pdf_files = [f for f in os.listdir(new_folder) if f.endswith('.pdf')]
                if pdf_files:
                    self.log_message(f"✅ PDF 다운로드 완료. {len(pdf_files)}개 파일 발견")
                    self.selected_folder = new_folder
                    
                    # UI 업데이트
                    self.root.after(0, self.update_folder_selection, new_folder)
                    
                    # 다음 단계로 진행
                    self.root.after(1000, self.one_click_step2_pdf_to_db)
                else:
                    raise Exception(f"다운로드 폴더에 PDF 파일이 없습니다: {new_folder}")
            else:
                # 새 폴더가 없으면 가장 최근 폴더 사용
                if os.path.exists(raw_db_path):
                    all_folders = [os.path.join(raw_db_path, f) for f in os.listdir(raw_db_path) 
                                if os.path.isdir(os.path.join(raw_db_path, f))]
                    if all_folders:
                        latest_folder = max(all_folders, key=os.path.getmtime)
                        pdf_files = [f for f in os.listdir(latest_folder) if f.endswith('.pdf')]
                        if pdf_files:
                            self.log_message(f"ℹ️ 최근 폴더 사용: {latest_folder}")
                            self.selected_folder = latest_folder
                            self.root.after(0, self.update_folder_selection, latest_folder)
                            self.root.after(1000, self.one_click_step2_pdf_to_db)
                            return
                
                raise Exception("다운로드된 폴더를 찾을 수 없습니다.")
                
        except Exception as e:
            self.log_message(f"❌ 폴더 모니터링 중 오류: {e}")
            self.root.after(0, lambda: self.finish_one_click_process(success=False))

    def wait_for_folder_stability(self, folder_path, stability_time=3):
        """폴더 내용이 안정화될 때까지 대기"""
        self.log_message("📥 파일 다운로드 완료 대기 중...")
        
        last_modified = os.path.getmtime(folder_path)
        last_file_count = len(os.listdir(folder_path))
        
        while True:
            time.sleep(stability_time)
            
            current_modified = os.path.getmtime(folder_path)
            current_file_count = len(os.listdir(folder_path))
            
            # 폴더가 변경되지 않았으면 안정화된 것으로 판단
            if (current_modified == last_modified and 
                current_file_count == last_file_count):
                break
                
            last_modified = current_modified
            last_file_count = current_file_count
            self.log_message(f"📥 파일 수: {current_file_count}")
        
        self.log_message("✅ 다운로드 안정화 확인")

    def update_folder_selection(self, folder_path):
        """UI에서 폴더 선택 업데이트"""
        self.folder_label.config(text=folder_path, foreground="black")
        
        # One Click 모드가 아닐 때만 Bundle ID 자동 설정
        if not self.is_one_click_running:
            # Bundle ID 자동 설정
            bundle_id = os.path.basename(folder_path)
            bundle_id = unicodedata.normalize('NFC', bundle_id)
            self.bundle_id_entry.delete(0, tk.END)
            self.bundle_id_entry.insert(0, bundle_id)
            self.log_message(f"📝 Bundle ID: {bundle_id}")
        else:
            # One Click 모드에서는 기존 Bundle ID 유지
            self.log_message(f"📝 Bundle ID (유지): {self.one_click_bundle_id}")
        
        self.log_message(f"📂 선택된 폴더: {folder_path}")
            
    def wait_for_downloader_completion(self, process):
        """PDF 다운로더 완료 대기 후 다음 단계 진행"""
        try:
            # 프로세스 완료 대기
            process.wait()
            
            # 다운로드된 폴더 감지
            raw_db_path = os.path.expanduser("~/Desktop/Apps/qcjongmin/appauto/raw_DB/rawdbs")
            if os.path.exists(raw_db_path):
                # 가장 최근에 생성된 폴더 찾기
                folders = [f for f in glob.glob(os.path.join(raw_db_path, "*")) if os.path.isdir(f)]
                if folders:
                    latest_folder = max(folders, key=os.path.getctime)
                    self.selected_folder = latest_folder
                    self.folder_label.config(text=latest_folder, foreground="black")
                    
                    # Bundle ID 자동 설정
                    bundle_id = os.path.basename(latest_folder)
                    bundle_id = unicodedata.normalize('NFC', bundle_id)
                    self.bundle_id_entry.delete(0, tk.END)
                    self.bundle_id_entry.insert(0, bundle_id)
                    
                    self.log_message(f"✅ PDF 다운로드 완료. 폴더: {latest_folder}")
                    
                    # 다음 단계로 진행
                    self.root.after(100, self.one_click_step2_pdf_to_db)
                else:
                    raise Exception("다운로드된 폴더를 찾을 수 없습니다.")
            else:
                raise Exception("다운로드 경로를 찾을 수 없습니다.")
                
        except Exception as e:
            self.log_message(f"❌ PDF 다운로더 대기 중 오류: {e}")
            self.finish_one_click_process(success=False)
            
    def one_click_step2_pdf_to_db(self):
        """[2/10] PDF -> DB 변환 (수정 모드 건너뛰기)"""
        self.log_message("\n[2/10] PDF -> DB 변환 시작...")
        self.reset_internal_state()
        
        # 별도 스레드에서 PDF 처리 실행
        threading.Thread(
            target=self.one_click_process_all_pdfs,
            daemon=True
        ).start()
        
    def one_click_process_all_pdfs(self):
        """One Click용 PDF 처리 (수정 모드 건너뛰기)"""
        try:
            pdf_files = self.get_pdf_files(self.selected_folder)
            self.total_files = len(pdf_files)
            
            if self.total_files == 0:
                self.log_message("처리할 PDF 파일이 없습니다.")
                self.finish_one_click_process(success=False)
                return
                
            self.log_message(f"총 {self.total_files}개 PDF 파일 처리 시작")
            processor = PDFProcessor()
            
            for i, pdf_path in enumerate(pdf_files):
                try:
                    self.process_single_pdf(processor, pdf_path, i + 1)
                except Exception as e:
                    error_msg = f"파일 처리 중 오류: {os.path.basename(pdf_path)} - {e}"
                    self.log_message(error_msg)
                    self.failed_files.append((pdf_path, str(e)))
                self.processed_files += 1
                
            # 수정 모드 건너뛰고 바로 완료 처리
            self.one_click_finalize_pdf_processing()
            
        except Exception as e:
            self.log_message(f"PDF 처리 중 오류: {e}")
            self.finish_one_click_process(success=False)
            
    def one_click_finalize_pdf_processing(self):
        """One Click용 PDF 처리 완료 (수정 모드 건너뛰기)"""
        self.log_message("\n--- PDF 처리 결과 ---")
        
        # 이슈가 있어도 그냥 표시만 하고 진행
        if self.debug_issues or self.question_number_issues:
            self.log_message("⚠️ 일부 파일에 이슈가 있지만 계속 진행합니다:")
            for issue in self.debug_issues[:5]:  # 처음 5개만 표시
                self.log_message(f"  - {issue['filename']}")
            if len(self.debug_issues) > 5:
                self.log_message(f"  ... 외 {len(self.debug_issues) - 5}개")
        
        self.log_message("DB 파일명 변경 및 카테고리 업데이트 진행...")
        self.rename_db_files()
        self.run_category_update_logic_one_click()
        
    def run_category_update_logic_one_click(self):
        """One Click용 카테고리 업데이트"""
        try:
            processor = PDFProcessor()
            exam_name = os.path.basename(self.selected_folder)
            success, message = processor.update_all_db_categories(self.selected_folder, exam_name)
            self.log_message(message)
            
            if success:
                self.manage_final_db_files()
                self.log_message("✅ PDF -> DB 변환 완료")
                # 다음 단계로 진행
                self.root.after(100, self.one_click_step3_api)
            else:
                self.log_message("❌ 카테고리 업데이트 실패")
                self.finish_one_click_process(success=False)
                
        except Exception as e:
            self.log_message(f"카테고리 업데이트 중 오류: {e}")
            self.finish_one_click_process(success=False)
            
    def one_click_step3_api(self):
        """[3/10] 해설 생성"""
        self.log_message("\n[3/10] 해설 생성 시작...")
        self.one_click_run_external_script('2_pro_api.py', next_step=self.one_click_step4_audio)
        
    def one_click_step4_audio(self):
        """[4/10] 음성 생성"""
        self.log_message("\n[4/10] 음성 생성 시작...")
        self.one_click_run_external_script('3_description_audio.py', next_step=self.one_click_step5_ox_quiz)
        
    def one_click_step5_ox_quiz(self):
        """[5/10] OX Quiz 생성"""
        self.log_message("\n[5/10] OX Quiz 생성 시작...")
        self.one_click_run_external_script('5_OX_Quiz_Creating.py', next_step=self.one_click_step5_ox_db)
        
    # def one_click_step5_ox_db(self):
    #     """[5.5/10] OX Quiz DB 변환"""
    #     bundle_id = os.path.basename(self.selected_folder)
    #     self.one_click_run_external_script('ox_db.py', bundle_id, next_step=self.one_click_step6_create_app)
        
    def one_click_step6_create_app(self):
        """[6/10] Create App"""
        self.log_message("\n[6/10] Flutter 앱 생성 시작...")
        # One Click에서 저장된 Bundle ID 사용
        bundle_id = self.one_click_bundle_id
        self.one_click_run_external_script('8_AutoAppV2_new.py', bundle_id, next_step=self.one_click_step7_ox_dict_map)
        
    def one_click_step7_ox_dict_map(self):
        """[7/10] OX, Dict, Map Dart 파일 생성 (오류 무시)"""
        self.log_message("\n[7/10] OX, Dict, Map Dart 파일 생성 시작...")
        self.log_message("(dictionary.json, mindmap.json이 없어 일부 오류가 발생할 수 있습니다)")
        # One Click에서 저장된 Bundle ID 사용
        bundle_id = self.one_click_bundle_id
        self.one_click_run_external_script(
            '9_OX_Dict_Mindmap.py', 
            bundle_id, 
            next_step=self.one_click_step8_screenshot,
            ignore_errors=True
        )
        
    def one_click_step8_screenshot(self):
        """[8/10] 스크린샷 생성"""
        self.log_message("\n[8/10] 스크린샷 생성 시작...")
        # One Click에서 저장된 Bundle ID 사용
        bundle_id = self.one_click_bundle_id
        self.one_click_run_external_script('10_Screenshot.py', bundle_id, next_step=self.one_click_step9_produce)
        
    def one_click_step9_produce(self):
        """[9/10] Produce"""
        self.log_message("\n[9/10] App Store Connect에 앱 생성 시작...")
        # One Click에서 저장된 Bundle ID 사용
        bundle_id = self.one_click_bundle_id
        self.one_click_run_external_script('11_produce.py', bundle_id, next_step=self.one_click_step10_deliver)
        
    def one_click_step10_deliver(self):
        """[10/10] Deliver"""
        self.log_message("\n[10/10] 메타데이터 업로드 시작...")
        # One Click에서 저장된 Bundle ID 사용
        bundle_id = self.one_click_bundle_id
        self.one_click_run_external_script('12_deliver.py', bundle_id, next_step=self.one_click_complete)


    def finish_one_click_process(self, success=True):
        """One Click 프로세스 종료"""
        self.is_one_click_running = False
        self.one_click_bundle_id = None
        self.one_click_down_url = None  # ★ 이 줄 추가
        self.one_click_button.config(state="normal", text="One Click")
        self.set_ui_for_processing(False)
        
        if not success:
            self.log_message("\n❌ One Click 프로세스가 중단되었습니다.")
            messagebox.showerror("오류", "One Click 프로세스 실행 중 오류가 발생했습니다.\n로그를 확인해주세요.")
            
            
    def one_click_download_thread(self, urls, raw_db_path, before_folders):
        """One Click용 다운로드 스레드"""
        try:
            # pdf_downloader의 함수 직접 호출
            success, downloaded_folder = download_pdfs_from_urls(
                urls, 
                log_callback=self.log_message
            )
            
            if success and downloaded_folder:
                self.log_message(f"✅ PDF 다운로드 완료. 폴더: {downloaded_folder}")
                self.selected_folder = downloaded_folder
                
                # UI 업데이트
                self.root.after(0, self.update_folder_selection, downloaded_folder)
                
                # 다음 단계로 진행
                self.root.after(1000, self.one_click_step2_pdf_to_db)
            else:
                raise Exception("다운로드 실패 또는 폴더를 찾을 수 없습니다.")
                
        except Exception as e:
            self.log_message(f"❌ 다운로드 중 오류: {e}")
            self.root.after(0, lambda: self.finish_one_click_process(success=False))
            
    def one_click_complete(self):
        """One Click 프로세스 완료"""
        self.log_message("\n" + "="*50)
        self.log_message("🎉 ONE CLICK 프로세스 완료!")
        self.log_message("="*50)
        self.log_message("\n모든 작업이 성공적으로 완료되었습니다.")
        self.log_message("App Store Connect에서 앱 상태를 확인하세요.")
        
        # 완료 알림
        messagebox.showinfo(
            "완료", 
            "One Click 프로세스가 성공적으로 완료되었습니다!\n\n" +
            "생성된 앱은 App Store Connect에서 확인할 수 있습니다."
        )
        
        self.finish_one_click_process(success=True)
        
    def one_click_run_external_script(self, script_name, *args, next_step=None, ignore_errors=False):
        """One Click용 외부 스크립트 실행"""
        def run_in_thread():
            try:
                script_path = os.path.join(os.path.dirname(__file__), script_name)
                if not os.path.exists(script_path):
                    raise FileNotFoundError(f"{script_name} 파일을 찾을 수 없습니다.")
                    
                # 명령어 구성
                if script_name in ["8_AutoAppV2.py", "9_OX_Dict_Mindmap.py", "10_Screenshot.py", "11_produce.py", "12_deliver.py"]:
                    command = [sys.executable, script_path, self.selected_folder, args[0]]
                else:
                    command = [sys.executable, script_path, self.selected_folder] + list(args)
                    
                # 프로세스 실행
                process = subprocess.Popen(
                    command, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    encoding='utf-8', 
                    bufsize=1
                )
                
                # 출력 읽기
                for line in iter(process.stdout.readline, ''):
                    self.log_message(line.strip())
                    
                process.stdout.close()
                return_code = process.wait()
                
                if return_code == 0:
                    self.log_message(f"✅ {script_name} 완료")
                    if next_step:
                        self.root.after(100, next_step)
                else:
                    if ignore_errors:
                        self.log_message(f"⚠️ {script_name} 오류 발생 (무시하고 진행)")
                        if next_step:
                            self.root.after(100, next_step)
                    else:
                        self.log_message(f"❌ {script_name} 실패 (Return Code: {return_code})")
                        self.finish_one_click_process(success=False)
                        
            except Exception as e:
                self.log_message(f"스크립트 실행 중 오류: {e}")
                if ignore_errors and next_step:
                    self.root.after(100, next_step)
                else:
                    self.finish_one_click_process(success=False)
                    
        # 스레드에서 실행
        threading.Thread(target=run_in_thread, daemon=True).start()
        
    def start_simple_create_process(self):
        """Simple Create 프로세스 실행 - 8_AutoAppV2_new.py 실행"""
        if not self.selected_folder:
            messagebox.showerror("오류", "먼저 폴더를 선택해주세요.")
            return
        bundle_id = self.bundle_id_entry.get().strip()
        if not bundle_id:
            messagebox.showerror("오류", "Bundle ID를 입력해주세요.")
            return
        
        self.log_message("\n" + "="*50)
        self.log_message("Simple Create 프로세스 시작...")
        self.log_message(f"실행 스크립트: 8_AutoAppV2_new.py")
        self.log_message(f"Bundle ID: {bundle_id}")
        self.log_message("="*50)
        
        self.start_external_script_process('8_AutoAppV2_new.py', bundle_id)
        
    def finish_one_click_process(self, success=True):
        """One Click 프로세스 종료"""
        self.is_one_click_running = False
        self.one_click_button.config(state="normal", text="One Click")
        self.set_ui_for_processing(False)
        
        if not success:
            self.log_message("\n❌ One Click 프로세스가 중단되었습니다.")
            messagebox.showerror("오류", "One Click 프로세스 실행 중 오류가 발생했습니다.\n로그를 확인해주세요.")

    def set_ui_for_processing(self, is_processing: bool):
        """UI 요소들의 상태를 일괄 변경합니다."""
        processing_state = "disabled" if is_processing else "normal"
        self.folder_button.config(state=processing_state)
        self.downloader_button.config(state=processing_state)
        
        dependent_state = "disabled" if is_processing or not self.selected_folder else "normal"
        # 모든 버튼의 상태를 한 번에 설정 (simple_create_button 추가)
        all_buttons = [
            self.process_button, self.api_button, self.audio_button, self.studynote_button,
            self.ox_quiz_button, self.dictionary_button, self.mindmap_button, self.create_app_button,
            self.simple_create_button,  # ★ 추가
            self.ox_dict_mindmap_button, self.screenshot_button, self.produce_button,
            self.deliver_button, self.release_button
        ]
        for btn in all_buttons:
            btn.config(state=dependent_state)
        
        # 다운로더 버튼은 폴더 선택과 무관하게 항상 활성화 (단, 처리 중에는 비활성화)
        self.downloader_button.config(state=processing_state)

    def launch_pdf_downloader(self):
        """PDF 다운로더를 통합된 형태로 실행"""
        url = self.down_url_entry.get().strip()
        if not url:
            messagebox.showerror("오류", "Down URL을 입력해주세요.")
            return
            
        self.log_message("\n- PDF 다운로드 시작... -")
        self.set_ui_for_processing(True)
        
        # 다운로드를 별도 스레드에서 실행
        self.download_thread = threading.Thread(
            target=self.run_pdf_download_thread,
            args=(url,),
            daemon=True
        )
        self.download_thread.start()
    def run_pdf_download_thread(self, url):
        """PDF 다운로드를 실행하고 완료 시 자동으로 다음 단계 진행"""
        try:
            urls = [u.strip() for u in url.split('\n') if u.strip()]
            
            # 다운로드 실행
            success, downloaded_folder = download_pdfs_from_urls(
                urls, 
                log_callback=self.log_message
            )
            
            if success and downloaded_folder:
                # 다운로드된 폴더 자동 선택
                self.selected_folder = downloaded_folder
                
                # UI 업데이트 (메인 스레드에서 실행)
                self.root.after(0, self.after_download_complete, downloaded_folder)
            else:
                self.root.after(0, lambda: self.set_ui_for_processing(False))
                self.root.after(0, lambda: messagebox.showerror("오류", "PDF 다운로드 중 오류가 발생했습니다."))
                
        except Exception as e:
            self.log_message(f"다운로드 중 오류 발생: {e}")
            self.root.after(0, lambda: self.set_ui_for_processing(False))
            
    def after_download_complete(self, downloaded_folder):
        """다운로드 완료 후 처리"""
        # 폴더 선택 UI 업데이트
        self.folder_label.config(text=downloaded_folder, foreground="black")
        
        # Bundle ID 자동 설정
        bundle_id = os.path.basename(downloaded_folder)
        bundle_id = unicodedata.normalize('NFC', bundle_id)
        self.bundle_id_entry.delete(0, tk.END)
        self.bundle_id_entry.insert(0, bundle_id)
        
        self.log_message(f"\n✅ PDF 다운로드 완료")
        self.log_message(f"📂 다운로드 폴더: {downloaded_folder}")
        self.log_message(f"📝 Bundle ID: {bundle_id}")
        
        # 자동으로 PDF -> DB 변환 시작
        self.log_message("\n🔄 자동으로 PDF -> DB 변환을 시작합니다...")
        time.sleep(1)  # 잠시 대기
        self.start_pdf_to_db_process()

    def select_folder(self):
        initial_dir = self.default_folder if os.path.exists(self.default_folder) else "/"
        folder_path = filedialog.askdirectory(title="PDF 파일들이 있는 폴더를 선택하세요", initialdir=initial_dir)
        if folder_path:
            self.selected_folder = folder_path
            self.folder_label.config(text=folder_path, foreground="black")
            
            bundle_id = os.path.basename(folder_path)
            bundle_id = unicodedata.normalize('NFC', bundle_id)
            self.bundle_id_entry.delete(0, tk.END)
            self.bundle_id_entry.insert(0, bundle_id)

            self.set_ui_for_processing(False)
            self.log_message(f"폴더 선택됨: {folder_path}")
    
    def start_app_creation_process(self):
        self.start_generic_process('8_AutoAppV2.py')

    def start_ox_dict_mindmap_process(self):
        self.start_generic_process('9_OX_Dict_Mindmap.py')

    def start_screenshot_process(self):
        self.start_generic_process('10_Screenshot.py')
    
    def start_produce_process(self):
        self.start_generic_process('11_produce.py')

    def start_deliver_process(self):
        self.start_generic_process('12_deliver.py')
        
    def start_release_process(self):
        """ ★★★ 13. Fastlane Release 버튼의 새로운 동작 ★★★ """
        if not self.selected_folder:
            messagebox.showerror("오류", "먼저 폴더를 선택해주세요.")
            return
        bundle_id = self.bundle_id_entry.get().strip()
        if not bundle_id:
            messagebox.showerror("오류", "Bundle ID를 입력해주세요.")
            return
        
        self.open_ads_window_for_release()

    def open_ads_window_for_release(self):
        """ ★★★ 광고 ID 입력을 처리하고, 완료 후 subprocess를 실행하는 새 메소드 ★★★ """
        ads_window = tk.Toplevel(self.root)
        ads_window.title("광고 ID 및 Review ID 입력")
        ads_window.geometry("450x250")

        labels = ["Review ID:", "App ID:", "Interstitial Ad Unit ID:", "Rewarded Ad Unit ID:", "App Open Ad Unit ID:"]
        entries = {}

        for i, label_text in enumerate(labels):
            ttk.Label(ads_window, text=label_text).grid(row=i, column=0, padx=10, pady=5, sticky="e")
            entry = ttk.Entry(ads_window, width=40)
            entry.grid(row=i, column=1, padx=10, pady=5)
            entries[label_text] = entry

        def save_and_run():
            selected_folder = self.selected_folder
            bundle_id_val = self.bundle_id_entry.get().strip()
            project_folder = os.path.join(selected_folder, bundle_id_val)
            
            paths_to_check = {
                "Info.plist": os.path.join(project_folder, "ios", "Runner", "Info.plist"),
                "ad_helper.dart": os.path.join(project_folder, "lib", "ad_helper.dart"),
                "home.dart": os.path.join(project_folder, "lib", "home.dart")
            }

            for name, path in paths_to_check.items():
                if not os.path.exists(path):
                    messagebox.showerror("파일 오류", f"{name} 파일을 찾을 수 없습니다:\n{path}", parent=ads_window)
                    return
            
            user_appid = entries["App ID:"].get().strip()
            if user_appid:
                try:
                    with open(paths_to_check["Info.plist"], "rb") as f:
                        plist_data = plistlib.load(f)
                    plist_data["GADApplicationIdentifier"] = user_appid
                    with open(paths_to_check["Info.plist"], "wb") as f:
                        plistlib.dump(plist_data, f)
                    self.log_message("Info.plist -> GADApplicationIdentifier 업데이트 완료")
                except Exception as e:
                    messagebox.showerror("오류", f"Info.plist 수정 오류: {e}", parent=ads_window)
                    return

            try:
                with open(paths_to_check["ad_helper.dart"], "r", encoding="utf-8") as f:
                    content = f.read()
                
                id_map = {
                    "'ca-app-pub-3940256099942544/4411468910'": f"'{entries['Interstitial Ad Unit ID:'].get().strip()}'",
                    "'ca-app-pub-3940256099942544/1712485313'": f"'{entries['Rewarded Ad Unit ID:'].get().strip()}'",
                    "'ca-app-pub-3940256099942544/5575463023'": f"'{entries['App Open Ad Unit ID:'].get().strip()}'"
                }
                
                for old_id, new_id in id_map.items():
                    if new_id.strip("'"):
                        content = content.replace(old_id, new_id)

                with open(paths_to_check["ad_helper.dart"], "w", encoding="utf-8") as f:
                    f.write(content)
                self.log_message("ad_helper.dart 업데이트 완료")
            except Exception as e:
                messagebox.showerror("오류", f"ad_helper.dart 수정 오류: {e}", parent=ads_window)
                return

            user_review_id = entries["Review ID:"].get().strip()
            if user_review_id:
                try:
                    with open(paths_to_check["home.dart"], "r", encoding="utf-8") as f:
                        content = f.read()
                    old_url_pattern = re.compile(r"https://apps\.apple\.com/app/id\d+")
                    new_url = f"https://apps.apple.com/app/id{user_review_id}"
                    content = old_url_pattern.sub(new_url, content)
                    with open(paths_to_check["home.dart"], "w", encoding="utf-8") as f:
                        f.write(content)
                    self.log_message("home.dart -> 리뷰 URL 업데이트 완료")
                except Exception as e:
                    messagebox.showerror("오류", f"home.dart 수정 오류: {e}", parent=ads_window)
                    return
            
            ads_window.destroy()
            messagebox.showinfo("저장 완료", "광고 ID 저장이 완료되었습니다.\n이제 Fastlane 배포를 시작합니다.")
            
            self.start_external_script_process('13_release.py', bundle_id_val)

        ttk.Button(ads_window, text="저장하고 배포 시작", command=save_and_run).grid(row=len(labels), column=0, columnspan=2, pady=20)
        ads_window.transient(self.root)
        ads_window.grab_set()
        self.root.wait_window(ads_window)


    def start_generic_process(self, script_name):
        """Bundle ID를 필요로 하는 프로세스를 시작하는 범용 함수"""
        if not self.selected_folder:
            messagebox.showerror("오류", "먼저 폴더를 선택해주세요.")
            return
        bundle_id = self.bundle_id_entry.get().strip()
        if not bundle_id:
            messagebox.showerror("오류", "Bundle ID를 입력해주세요.")
            return
        self.start_external_script_process(script_name, bundle_id)

    def start_external_script_process(self, script_name: str, *args):
        """외부 스크립트 실행을 위한 범용 메소드"""
        if not self.selected_folder:
            messagebox.showerror("오류", "먼저 폴더를 선택해주세요.")
            return

        process_name = {
            "2_pro_api.py": "2. 해설 생성(API)",
            "3_description_audio.py": "3. 음성 생성(TTS)",
            "4_StudyNote.py": "4. Study Note 생성",
            "5_OX_Quiz_Creating.py": "5. OX Quiz 생성",
            "6_dictionary.py": "6. 용어사전 생성",
            "7_mindmap.py": "7. 마인드맵 생성",
            "8_AutoAppV2.py": "8. Flutter 앱 생성",
            "9_OX_Dict_Mindmap.py": "9. Dart 코드 생성 (OX, Dict, Mindmap)",
            "10_Screenshot.py": "10. 스크린샷 생성",
            "11_produce.py": "11. Fastlane Produce",
            "12_deliver.py": "12. Fastlane Deliver",
            "13_release.py": "13. Fastlane Release",
            "ox_db.py": "OX Quiz DB 변환"
        }.get(script_name, script_name)
        
        self.log_message("\n" + "="*50)
        self.log_message(f"{process_name} 스크립트 실행 시작...")
        if any(keyword in script_name for keyword in ["api", "audio", "StudyNote", "Quiz", "dictionary", "mindmap", "AutoApp", "Screenshot", "produce", "deliver", "release"]):
            self.log_message("이 작업은 인터넷 속도와 컴퓨터 사양에 따라 수 분 이상 소요될 수 있습니다.")

        self.set_ui_for_processing(True)
        
        command_args = [script_name]
        if script_name in ["8_AutoAppV2.py", "9_OX_Dict_Mindmap.py", "10_Screenshot.py", "11_produce.py", "12_deliver.py", "13_release.py"]:
            command_args.extend([self.selected_folder, args[0]])
        else:
            command_args.extend(list(args))
        
        threading.Thread(target=self.run_external_script_in_thread, args=command_args, daemon=True).start()

    def run_external_script_in_thread(self, script_name: str, *args):
        """스레드에서 범용적으로 외부 스크립트를 실행하고 자동 연계"""
        return_code = -1
        auto_continue = False
        try:
            script_path = os.path.join(os.path.dirname(__file__), script_name)
            if not os.path.exists(script_path):
                self.log_message(f"오류: {script_name} 파일을 찾을 수 없습니다.")
                return

            if script_name in ["8_AutoAppV2.py", "9_OX_Dict_Mindmap.py", "10_Screenshot.py", "11_produce.py", "12_deliver.py", "13_release.py"]:
                command = [sys.executable, script_path, args[0], args[1]]
            else:
                command = [sys.executable, script_path, self.selected_folder] + list(args)

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)

            for line in iter(process.stdout.readline, ''):
                self.log_message(line.strip())

            process.stdout.close()
            return_code = process.wait()
            
            if return_code == 0:
                self.log_message(f"\n✅ {script_name} 스크립트 실행이 성공적으로 완료되었습니다.")
                
                success_messages = {
                    "5_OX_Quiz_Creating": ("5단계 완료", "OX 퀴즈 생성이 완료되었습니다.\n자동으로 DB 변환을 시작합니다."),
                    "ox_db": ("OX 퀴즈 DB 생성 완료", "OX 퀴즈용 DB(quiz.db) 생성이 완료되었습니다."),
                    # "4_StudyNote": ("Study Note 생성 완료", "Study Note 관련 모든 프로세스가 완료되었습니다."),
                    # "6_dictionary": ("용어사전 생성 완료", "용어사전 관련 모든 프로세스(JSON, DB, TTS, Manifest)가 완료되었습니다."),
                    # "7_mindmap": ("마인드맵 생성 완료", "mindmap.json 파일이 성공적으로 생성되었습니다."),
                    "8_AutoAppV2": ("앱 생성 완료", "Flutter 앱 생성이 성공적으로 완료되었습니다."),
                    "9_OX_Dict_Mindmap": ("Dart 코드 생성 완료", "OX, Dictionary, Mindmap용 Dart 파일 생성이 완료되었습니다."),
                    "10_Screenshot": ("스크린샷 생성 완료", "스크린샷 생성이 성공적으로 완료되었습니다."),
                    "11_produce": ("Produce 완료", "App Store Connect에 앱 생성이 성공적으로 완료되었습니다."),
                    "12_deliver": ("Deliver 완료", "메타데이터 및 스크린샷 업로드가 성공적으로 완료되었습니다."),
                    "13_release": ("Release 완료", "빌드 파일이 App Store Connect에 성공적으로 업로드되었습니다.")
                }

                for key, (title, msg) in success_messages.items():
                    if key in script_name:
                        messagebox.showinfo(title, msg)
                        break
                
                # if "5_OX_Quiz_Creating" in script_name:
                #     bundle_id = os.path.basename(self.selected_folder)
                #     self.start_external_script_process('ox_db.py', bundle_id)
                #     auto_continue = True

            else:
                self.log_message(f"\n⚠️ {script_name} 스크립트 실행 중 오류가 발생했습니다. (Return Code: {return_code})")
                messagebox.showerror("오류", f"{script_name} 실행 중 오류가 발생했습니다. 로그를 확인해주세요.")

        except Exception as e:
            self.log_message(f"스크립트 실행 중 심각한 오류 발생: {e}")
        finally:
            if not auto_continue:
                self.root.after(100, lambda: self.set_ui_for_processing(False))

    def start_pdf_to_db_process(self):
        """1단계: PDF -> DB 변환 프로세스를 시작합니다."""
        if not self.selected_folder:
            messagebox.showerror("오류", "폴더를 먼저 선택해주세요.")
            return

        self.reset_internal_state()
        self.set_ui_for_processing(True)
        self.log_message("\n" + "="*50)
        self.log_message("1. PDF -> DB 변환 프로세스 시작...")
        
        threading.Thread(target=self.process_all_pdfs, daemon=True).start()

    def process_all_pdfs(self):
        try:
            pdf_files = self.get_pdf_files(self.selected_folder)
            self.total_files = len(pdf_files)
            
            if self.total_files == 0:
                self.log_message("처리할 PDF 파일이 없습니다.")
                self.root.after(100, lambda: self.set_ui_for_processing(False))
                return
                
            self.log_message(f"총 {self.total_files}개 PDF 파일 처리 시작")
            processor = PDFProcessor()
            
            for i, pdf_path in enumerate(pdf_files):
                try:
                    self.process_single_pdf(processor, pdf_path, i + 1)
                except Exception as e:
                    error_msg = f"파일 처리 중 오류: {os.path.basename(pdf_path)} - {e}"
                    self.log_message(error_msg)
                    self.failed_files.append((pdf_path, str(e)))
                self.processed_files += 1
                
            self.finalize_processing()
        except Exception as e:
            self.log_message(f"전체 처리 중 오류: {e}")
            self.root.after(100, lambda: self.set_ui_for_processing(False))

# in 0_Machine.py

    def process_single_pdf(self, processor: PDFProcessor, pdf_path: str, file_num: int):
        """[수정] DB 파일이 assets 폴더에 직접 생성되도록 경로 수정"""
        filename = os.path.basename(pdf_path)
        self.log_message(f"[{file_num}/{self.total_files}] 처리 시작: {filename}")
        
        # --- ▼▼▼ 수정된 부분 시작 ▼▼▼ ---

        # 1. assets 폴더 경로를 정의하고, 폴더가 없으면 생성합니다.
        assets_folder = os.path.join(self.selected_folder, "assets")
        os.makedirs(assets_folder, exist_ok=True)
        
        db_name = self.extract_db_name(pdf_path)
        # 2. db_path가 assets 폴더를 가리키도록 수정합니다.
        db_path = os.path.join(assets_folder, db_name)
        
        # --- ▲▲▲ 수정된 부분 끝 ▲▲▲ ---

        if os.path.exists(db_path):
            os.remove(db_path)
            
        match = re.search(r"^(.*?)\d{8}\(교사용\)\.pdf$", filename)
        exam_category = match.group(1) if match else "Unknown"
        
        debug_result = processor.process_pdf(pdf_path, db_path, exam_category)
        
        # (이하 함수 내용은 기존과 동일)
        last_number = debug_result.get('last_question_number', 0)
        self.db_last_numbers.append({'filename': filename, 'db_name': db_name, 'last_number': last_number})
        
        if self.first_db_last_number is None:
            self.first_db_last_number = last_number
        elif last_number != self.first_db_last_number:
            self.question_number_issues.append({'filename': filename, 'db_name': db_name, 'expected': self.first_db_last_number, 'actual': last_number})

        if debug_result['has_issues']:
            self.debug_issues.append({'filename': filename, 'db_name': db_name, 'issues': debug_result.get('issues', ['상세 정보 없음'])})
            self.log_message(f"⚠️ {filename}: 처리 중 이슈 발견. 최종 결과에서 확인하세요.")
        else:
            self.log_message(f"✅ {filename}: 성공적으로 처리됨")
            
    def finalize_processing(self):
        self.log_message("\n" + "="*50)
        self.log_message("모든 PDF 처리 완료. 최종 결과를 확인합니다...")
        
        issue_files_with_real_problems = [
            item for item in self.debug_issues 
            if any("누락" in detail or "미배정" in detail for detail in item.get('issues', []))
        ]
        
        all_issue_filenames = {item['filename'] for item in issue_files_with_real_problems}
        all_issue_filenames.update(item['filename'] for item in self.question_number_issues)

        self.log_message("\n--- 최종 디버깅 결과 ---")
        if not all_issue_filenames and not self.failed_files:
             self.log_message("✅ 모든 파일이 이슈 없이 완벽하게 처리되었습니다.")
        else:
            processed_filenames = {item['filename'] for item in self.db_last_numbers}
            success_files = processed_filenames - all_issue_filenames
            if success_files:
                self.log_message(f"\n✅ 성공적으로 처리된 파일 ({len(success_files)}개):")
                for filename in sorted(list(success_files)):
                     self.log_message(f"  - {filename}")

            if all_issue_filenames:
                 self.log_message(f"\n⚠️ 이슈가 발견된 파일 ({len(all_issue_filenames)}개):")
                 for issue_info in self.debug_issues:
                     if issue_info['filename'] in all_issue_filenames:
                         self.log_message(f"\n[파일: {issue_info['filename']}]")
                         for detail in issue_info.get('issues', []):
                             self.log_message(detail)
                 if self.question_number_issues:
                      self.log_message("\n[문제 번호 불일치 이슈]")
                      for issue in self.question_number_issues:
                           self.log_message(f"  - 파일: {issue['filename']}, 예상 문제 수: {issue['expected']}, 실제 문제 수: {issue['actual']}")

        if self.failed_files:
            self.log_message("\n--- 처리 실패 파일 ---")
            for pdf_path, error in self.failed_files:
                self.log_message(f"  - {os.path.basename(pdf_path)}: {error}")

        if all_issue_filenames or self.failed_files:
            filenames_added = set()
            self.issue_files_to_correct = []
            for item_list in [self.debug_issues, self.question_number_issues, [{'filename': os.path.basename(f[0]), 'db_name': ''} for f in self.failed_files]]:
                 for item in item_list:
                      if item['filename'] not in filenames_added:
                           self.issue_files_to_correct.append(item)
                           filenames_added.add(item['filename'])
            self.start_correction_mode()
        else:
            self.log_message("\n모든 파일이 정상 처리되었습니다. DB 파일명 변경 및 카테고리 업데이트를 시작합니다.")
            self.rename_db_files()
            self.run_category_update_logic()

# in 0_Machine.py

    def rename_db_files(self) -> Dict[str, str]:
        """[수정] assets 폴더 내에서 파일명을 변경하도록 경로 수정"""
        self.log_message("\n--- 데이터베이스 파일명 변경 및 ExamSession 업데이트 시작 ---")
        renamed_map = {}
        if not self.db_last_numbers:
            return renamed_map

        # --- ▼▼▼ 수정된 부분 시작 ▼▼▼ ---
        assets_folder = os.path.join(self.selected_folder, "assets")
        # --- ▲▲▲ 수정된 부분 끝 ▲▲▲ ---

        sorted_dbs = sorted(self.db_last_numbers, key=lambda x: x['db_name'], reverse=True)
        
        for i, db_info in enumerate(sorted_dbs):
            session_num = i + 1
            old_db_name = db_info['db_name']
            new_db_name = f"question{session_num}.db"
            
            # --- ▼▼▼ 수정된 부분 시작 ▼▼▼ ---
            old_db_path = os.path.join(assets_folder, old_db_name)
            new_db_path = os.path.join(assets_folder, new_db_name)
            # --- ▲▲▲ 수정된 부분 끝 ▲▲▲ ---

            if os.path.exists(old_db_path):
                try:
                    if os.path.exists(new_db_path):
                        os.remove(new_db_path)
                    os.rename(old_db_path, new_db_path)
                    renamed_map[old_db_name] = new_db_name
                    self.update_exam_session_in_db(new_db_path, session_num)
                    self.log_message(f"  - '{old_db_name}' -> '{new_db_name}' 변경 및 업데이트 완료")
                except Exception as e:
                    self.log_message(f"  - '{old_db_name}' 처리 실패: {e}")
        
        self.log_message("--- 데이터베이스 파일명 변경 및 업데이트 완료 ---")
        return renamed_map

    def update_exam_session_in_db(self, db_path: str, session_number: int):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE questions SET ExamSession = ?", (str(session_number),))
            conn.commit()
            conn.close()
        except Exception as e:
            self.log_message(f"    - '{os.path.basename(db_path)}'의 ExamSession 업데이트 실패: {e}")

    def run_category_update_logic(self):
        try:
            processor = PDFProcessor()
            all_pdfs = processor.get_pdf_files_info(self.selected_folder)
            if not all_pdfs:
                messagebox.showerror("오류", "폴더에서 처리할 PDF 파일을 찾을 수 없습니다.")
                self.set_ui_for_processing(False)
                return

            exam_name = os.path.basename(self.selected_folder)
            success, message = processor.update_all_db_categories(self.selected_folder, exam_name)
            
            self.log_message(message)
            
            if success:
                 self.log_message("\n✅ 1단계(PDF 변환 및 카테고리 업데이트) 완료.")
                 self.manage_final_db_files()
                 self.log_message("\n모든 작업 완료. 다음 단계를 진행해주세요.")
                 messagebox.showinfo("1단계 완료", "PDF 변환 및 카테고리 업데이트가 성공적으로 완료되었습니다.")
                 self.set_ui_for_processing(False)
            else:
                messagebox.showerror("오류", "카테고리 정보 업데이트 중 오류가 발생했습니다.")
                self.set_ui_for_processing(False)
        except Exception as e:
            self.log_message(f"카테고리 업데이트 중 심각한 오류 발생: {e}")
            self.set_ui_for_processing(False)
            
    def manage_final_db_files(self):
        self.log_message("\n--- 최종 DB 파일 정리 시작 ---")
        assets_folder = os.path.join(self.selected_folder, "assets")
        
        try:
            os.makedirs(assets_folder, exist_ok=True)
            self.log_message(f"'assets' 폴더 확인 및 생성: {assets_folder}")
            
            db_files_moved = 0
            for filename in os.listdir(self.selected_folder):
                if re.match(r'^question\d+\.db$', filename):
                    source_path = os.path.join(self.selected_folder, filename)
                    destination_path = os.path.join(assets_folder, filename)
                    
                    if os.path.exists(destination_path):
                        os.remove(destination_path)
                        
                    try:
                        os.rename(source_path, destination_path)
                        self.log_message(f"  - '{filename}' 파일을 'assets' 폴더로 이동 완료.")
                        db_files_moved += 1
                    except Exception as e:
                        self.log_message(f"  - 오류: '{filename}' 이동 실패 - {e}")
            
            if db_files_moved > 0:
                self.log_message(f"총 {db_files_moved}개의 DB 파일을 'assets' 폴더로 정리했습니다.")
            else:
                self.log_message("'assets' 폴더로 이동할 questionX.db 파일이 없습니다.")

        except Exception as e:
            self.log_message(f"DB 파일 정리 중 심각한 오류 발생: {e}")
        
        self.log_message("--- 최종 DB 파일 정리 완료 ---")
        
    def start_correction_mode(self):
        if not self.issue_files_to_correct:
            return

        response = messagebox.askyesno("디버그 수정 모드", "일부 파일에서 이슈가 발견되었습니다. \n수정 모드로 진입하여 PDF와 DB 파일을 직접 확인하시겠습니까?")
        if not response:
            self.log_message("--- 사용자가 수정을 건너뛰었습니다. ---")
            self.set_ui_for_processing(False)
            return

        if not DB_BROWSER_PATH or not os.path.exists(DB_BROWSER_PATH):
            messagebox.showerror("경고", f"DB 브라우저 경로가 잘못되었습니다.\n'{DB_BROWSER_PATH}'")
            self.set_ui_for_processing(False)
            return

        self.correction_frame.grid() # 숨겨진 프레임을 다시 보이게
        self.current_correction_index = -1
        self.next_correction_file()

    def next_correction_file(self):
        self.close_opened_processes()
        self.current_correction_index += 1
        if self.current_correction_index >= len(self.issue_files_to_correct):
            messagebox.showinfo("수정 완료", "모든 이슈 파일 검토 완료.")
            self.finish_correction_mode()
            return
        
        issue_info = self.issue_files_to_correct[self.current_correction_index]
        filename = issue_info['filename']
        db_name = self.extract_db_name(filename) 
        pdf_path = os.path.join(self.selected_folder, filename)
        db_path = os.path.join(self.selected_folder, db_name)

        self.correction_label.config(text=f"수정 중 ({self.current_correction_index + 1}/{len(self.issue_files_to_correct)}): {filename}")
        self.open_files_for_correction(pdf_path, db_path)

    def open_files_for_correction(self, pdf_path: str, db_path: str):
        try:
            if os.path.exists(pdf_path):
                proc = subprocess.Popen(["open", pdf_path] if sys.platform == "darwin" else ["xdg-open", pdf_path])
                self.opened_processes.append(proc)
            else:
                self.log_message(f"  - PDF 파일 없음: {pdf_path}")
        except Exception as e:
            self.log_message(f"  - PDF 파일 열기 실패: {e}")

        if os.path.exists(db_path) and os.path.exists(DB_BROWSER_PATH):
            try:
                proc = subprocess.Popen([DB_BROWSER_PATH, db_path])
                self.opened_processes.append(proc)
            except Exception as e:
                self.log_message(f"  - DB 파일 열기 실패: {e}")

    def close_opened_processes(self):
        for proc in self.opened_processes:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception: pass
        self.opened_processes = []
        
# in 0_Machine.py

    def finish_correction_mode(self):
        """[수정] 수정 모드 종료 시, 최종 단계를 실행하도록 변경"""
        self.close_opened_processes()
        self.correction_frame.grid_remove()  # 프레임 다시 숨기기
        
        self.log_message("\n--- 디버그 수정 완료. 최종 단계를 실행합니다. ---")
        
        # UI 멈춤을 방지하기 위해 별도 스레드에서 최종 단계 실행
        threading.Thread(target=self._run_final_steps_after_correction, daemon=True).start()

    def _run_final_steps_after_correction(self):
        """[추가] 수정 모드 완료 후, 파일 이름 변경 및 카테고리 업데이트를 순차적으로 실행"""
        try:
            self.log_message("DB 파일명 변경 및 카테고리 업데이트를 시작합니다.")
            
            # 1. DB 파일 이름 변경 (YYYYMMDD.db -> questionX.db)
            self.rename_db_files()
            
            # 2. 카테고리 정보 업데이트
            # 이 함수 내에서 모든 작업 완료 후 UI 버튼 활성화 및 알림창 표시 로직이 이미 포함되어 있습니다.
            self.run_category_update_logic()

        except Exception as e:
            self.log_message(f"수정 후 최종 단계 실행 중 오류 발생: {e}")
            # 오류 발생 시에도 UI는 다시 활성화되어야 합니다.
            self.root.after(100, lambda: self.set_ui_for_processing(False))


    def get_pdf_files(self, folder_path: str) -> List[str]:
        pdf_files = []
        pattern = re.compile(r"^.*\d{8}\(교사용\)\.pdf$")
        try:
            for filename in os.listdir(folder_path):
                if filename.lower().endswith('.pdf') and pattern.match(filename) and not filename.startswith('._'):
                    pdf_files.append(os.path.join(folder_path, filename))
        except Exception as e:
            self.log_message(f"폴더 스캔 중 오류: {e}")
        return sorted(pdf_files)

    def extract_db_name(self, pdf_filename: str) -> str:
        basename = os.path.basename(pdf_filename)
        match = re.search(r"(\d{8})\(교사용\)\.pdf$", basename)
        return f"{match.group(1)}.db" if match else f"{Path(pdf_filename).stem}.db"
        
    def log_message(self, message: str):
        def update_log():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        self.root.after(0, update_log)
    
def main():
    try:
        PDFProcessor()
    except NameError:
        print("오류: pdf_processor.py 또는 해당 클래스를 찾을 수 없습니다.")
        return
        
    root = tk.Tk()
    app = PDFBatchProcessor(root)
    root.mainloop()

if __name__ == "__main__":
    main()