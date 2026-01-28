# 0_Machine.py (전체 수정)

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

try:
    from pdf_processor import PDFProcessor
except ImportError:
    print("pdf_processor.py 파일이 필요합니다. 이 파일과 같은 폴더에 있어야 합니다.")
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
        
        # 버튼 라인 1 (row=1)
        button_line_1_frame = ttk.Frame(main_frame)
        button_line_1_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
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
        self.ox_dict_mindmap_button = ttk.Button(button_line_2_frame, text="9. OX,Dict,Map", command=self.start_ox_dict_mindmap_process, state="disabled")
        self.screenshot_button = ttk.Button(button_line_2_frame, text="10. 스크린샷", command=self.start_screenshot_process, state="disabled")
        self.produce_button = ttk.Button(button_line_2_frame, text="11. Produce", command=self.start_produce_process, state="disabled")
        self.deliver_button = ttk.Button(button_line_2_frame, text="12. Deliver", command=self.start_deliver_process, state="disabled")
        self.release_button = ttk.Button(button_line_2_frame, text="13. Release", command=self.start_release_process, state="disabled")

        for btn in [self.mindmap_button, self.create_app_button, self.ox_dict_mindmap_button, self.screenshot_button, self.produce_button, self.deliver_button, self.release_button]:
            btn.pack(side=tk.LEFT, padx=2)

        # Bundle ID 입력 (row=3)
        app_creation_frame = ttk.LabelFrame(main_frame, text="App Generation", padding="5")
        app_creation_frame.grid(row=3, column=0, pady=(10, 0), sticky=(tk.W, tk.E))
        
        ttk.Label(app_creation_frame, text="Bundle ID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.bundle_id_entry = ttk.Entry(app_creation_frame, width=40)
        self.bundle_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
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

    def set_ui_for_processing(self, is_processing: bool):
        """UI 요소들의 상태를 일괄 변경합니다."""
        processing_state = "disabled" if is_processing else "normal"
        self.folder_button.config(state=processing_state)
        self.downloader_button.config(state=processing_state)
        
        dependent_state = "disabled" if is_processing or not self.selected_folder else "normal"
        # 모든 버튼의 상태를 한 번에 설정
        all_buttons = [
            self.process_button, self.api_button, self.audio_button, self.studynote_button,
            self.ox_quiz_button, self.dictionary_button, self.mindmap_button, self.create_app_button,
            self.ox_dict_mindmap_button, self.screenshot_button, self.produce_button,
            self.deliver_button, self.release_button
        ]
        for btn in all_buttons:
            btn.config(state=dependent_state)
        
        # 다운로더 버튼은 폴더 선택과 무관하게 항상 활성화 (단, 처리 중에는 비활성화)
        self.downloader_button.config(state=processing_state)

    def launch_pdf_downloader(self):
        """pdf_downloader.py 스크립트를 별도의 프로세스로 실행합니다."""
        script_name = "pdf_downloader.py"
        self.log_message(f"\n- {script_name} 실행... -")
        try:
            script_path = os.path.join(os.path.dirname(__file__), script_name)
            if not os.path.exists(script_path):
                messagebox.showerror("오류", f"{script_name} 파일을 찾을 수 없습니다.")
                return
            subprocess.Popen([sys.executable, script_path])
        except Exception as e:
            messagebox.showerror("실행 오류", f"{script_name}을(를) 실행하는 중 오류가 발생했습니다: {e}")
            self.log_message(f"오류: {script_name} 실행 실패 - {e}")

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
                    "4_StudyNote": ("Study Note 생성 완료", "Study Note 관련 모든 프로세스가 완료되었습니다."),
                    "6_dictionary": ("용어사전 생성 완료", "용어사전 관련 모든 프로세스(JSON, DB, TTS, Manifest)가 완료되었습니다."),
                    "7_mindmap": ("마인드맵 생성 완료", "mindmap.json 파일이 성공적으로 생성되었습니다."),
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
                
                if "5_OX_Quiz_Creating" in script_name:
                    bundle_id = os.path.basename(self.selected_folder)
                    self.start_external_script_process('ox_db.py', bundle_id)
                    auto_continue = True

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