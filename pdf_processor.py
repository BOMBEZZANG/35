"""
PDF 처리 모듈 - 1_PDF_To_DB.py의 함수들을 GUI에서 사용할 수 있도록 래핑
"""

import os
import re
import sqlite3
from typing import List, Dict, Tuple, Optional
import sys
from pathlib import Path

# 1_PDF_To_DB.py의 함수들을 import
# 파일이 같은 디렉토리에 있다고 가정
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("pdf_to_db", "1_PDF_To_DB.py")
    pdf_to_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pdf_to_db)
except Exception as e:
    print(f"1_PDF_To_DB.py 파일을 로드할 수 없습니다: {e}")
    sys.exit(1)


class PDFProcessor:
    """PDF 처리를 담당하는 클래스"""
    
    def __init__(self):
        """PDFProcessor 초기화"""
        pass
        
    def process_pdf(self, pdf_path: str, db_path: str, exam_category: str) -> Dict:
        """
        단일 PDF 파일을 처리하여 SQLite DB로 변환합니다.
        """
        try:
            # 1. 데이터베이스 설정
            pdf_to_db.setup_database_original(db_path)
            
            # 2. 파일명에서 정보 추출
            pdf_filename = os.path.basename(pdf_path)
            match = re.search(r"^(.*?)\d{8}\(교사용\)\.pdf$", pdf_filename)
            exam_name_from_filename = match.group(1) if match else None
            db_name = os.path.basename(db_path) # db_name 추출
            
            # 3. PDF 파싱 실행
            extracted_questions, all_images = pdf_to_db.parse_exam_pdf_with_cross_page_support(
                pdf_path, exam_name_from_filename
            )
            
            if not extracted_questions:
                return {
                    'success': False,
                    'has_issues': True,
                    'issues': ["추출된 문제가 없습니다"],
                    'processed_questions': 0,
                    'unassigned_images': len(all_images) if all_images else 0
                }
            
            # 4. 데이터베이스에 저장 [수정] db_name 인자 추가
            pdf_to_db.save_questions_to_db_original(db_path, db_name, extracted_questions, exam_category)
            
            # 5. 최종 디버깅 체크
            debug_result = self.check_final_debug_status(db_path, all_images)
            debug_result['success'] = True
            debug_result['processed_questions'] = len(extracted_questions)
            
            return debug_result
            
        except Exception as e:
            return {
                'success': False,
                'has_issues': True,
                'issues': [f"처리 중 오류 발생: {str(e)}"],
                'processed_questions': 0,
                'unassigned_images': 0
            }
    
    def get_last_question_number(self, db_path: str) -> int:
        """
        DB 파일에서 마지막 문제번호를 추출합니다.
        """
        try:
            return pdf_to_db.get_last_question_number_from_db(db_path)
        except Exception as e:
            print(f"마지막 문제번호 추출 중 오류: {e}")
            return 0
    
    def check_final_debug_status(self, db_path: str, all_images: List[Dict]) -> Dict:
        """
        [수정] 최종 디버깅 상태를 확인하고, 반환된 딕셔너리를 그대로 사용합니다.
        """
        try:
            # final_assignment_debug_check는 이제 직접 딕셔너리를 반환합니다.
            debug_result_dict = pdf_to_db.final_assignment_debug_check(db_path, all_images)
            
            # 반환된 딕셔너리를 기반으로 최종 결과 구성
            return {
                'success': True,
                'has_issues': debug_result_dict.get('has_issues', True),
                'issues': debug_result_dict.get('issues', []), # 상세 이슈 리스트
                'last_question_number': debug_result_dict.get('last_question_number', 0),
            }
            
        except Exception as e:
            return {
                'success': False,
                'has_issues': True,
                'issues': [f"디버그 확인 중 오류: {str(e)}"],
                'last_question_number': 0
            }

    def get_pdf_files_info(self, folder_path: str) -> List[Dict]:
        """
        폴더에서 PDF 파일들의 정보를 가져옵니다.
        """
        pdf_files = []
        pattern = re.compile(r"^(.*?)(\d{8})\(교사용\)\.pdf$")
        
        try:
            for filename in os.listdir(folder_path):
                if filename.lower().endswith('.pdf'):
                    match = pattern.match(filename)
                    if match:
                        subject_name = match.group(1)
                        date_str = match.group(2)
                        
                        pdf_info = {
                            'filename': filename,
                            'full_path': os.path.join(folder_path, filename),
                            'subject': subject_name,
                            'date': date_str,
                            'db_name': f"{date_str}.db"
                        }
                        pdf_files.append(pdf_info)
                        
        except Exception as e:
            print(f"폴더 스캔 중 오류: {e}")
            
        return sorted(pdf_files, key=lambda x: x['date'])
    
    def validate_pdf_file(self, pdf_path: str) -> Tuple[bool, str]:
        """
        PDF 파일이 처리 가능한지 검증합니다.
        """
        try:
            if not os.path.exists(pdf_path):
                return False, "파일이 존재하지 않습니다"
            if os.path.getsize(pdf_path) == 0:
                return False, "파일 크기가 0입니다"
            filename = os.path.basename(pdf_path)
            pattern = re.compile(r"^.*\d{8}\(교사용\)\.pdf$")
            if not pattern.match(filename):
                return False, "파일명 패턴이 맞지 않습니다"
            with open(pdf_path, 'rb') as f:
                if f.read(4) != b'%PDF':
                    return False, "유효한 PDF 파일이 아닙니다"
            return True, "검증 성공"
        except Exception as e:
            return False, f"검증 중 오류: {str(e)}"

    def update_all_db_categories(self, folder_path: str, exam_name: str) -> Tuple[bool, str]:
        """
        [수정] 폴더 내 'assets' 하위 폴더의 모든 DB에 카테고리 정보를 일괄 업데이트합니다.
        """
        log_messages = []
        try:
            all_pdfs = self.get_pdf_files_info(folder_path)
            if not all_pdfs:
                return False, "처리할 PDF 파일이 없습니다."

            master_pdf_path = all_pdfs[-1]['full_path']
            log_messages.append(f"기준 PDF 파일: '{os.path.basename(master_pdf_path)}'")
            log_messages.append("카테고리 범위 분석 중...")

            category_ranges = pdf_to_db.extract_category_ranges(master_pdf_path)

            if not category_ranges:
                return False, "오류: 기준 PDF에서 카테고리 정보를 추출하지 못했습니다."

            log_messages.append("카테고리 범위 분석 완료:")
            for cat in category_ranges:
                log_messages.append(f"  - {cat['name']}: 문제 {cat['start_q_num']} ~ {cat['end_q_num']}")

            assets_path = os.path.join(folder_path, "assets")
            if not os.path.isdir(assets_path):
                log_messages.append(f"오류: 'assets' 폴더를 찾을 수 없습니다. ({assets_path})")
                log_messages.append("먼저 'PDF->DB 변환'을 실행하여 'assets' 폴더와 DB 파일이 생성되었는지 확인하세요.")
                return False, "\n".join(log_messages)

            db_files_to_update = [f for f in os.listdir(assets_path) if re.match(r'^question\d+\.db$', f)]
            
            if not db_files_to_update:
                log_messages.append(f"'assets' 폴더에서 업데이트할 DB 파일(questionX.db)이 없습니다.")
                return True, "\n".join(log_messages)

            log_messages.append(f"\n총 {len(db_files_to_update)}개의 DB 파일에 카테고리 정보 적용 시작...")
            for db_filename in sorted(db_files_to_update):
                db_path = os.path.join(assets_path, db_filename)
                try:
                    pdf_to_db.apply_categories_to_db(db_path, category_ranges, exam_name)
                    log_messages.append(f"  - '{os.path.join('assets', db_filename)}' 업데이트 성공")
                except Exception as e:
                    log_messages.append(f"  - '{os.path.join('assets', db_filename)}' 업데이트 실패: {e}")
            
            log_messages.append("카테고리 정보 일괄 업데이트 완료!")
            return True, "\n".join(log_messages)

        except Exception as e:
            return False, f"카테고리 업데이트 중 오류 발생: {e}"

# 독립 실행을 위한 테스트 함수
def test_single_pdf(pdf_path: str):
    processor = PDFProcessor()
    filename = os.path.basename(pdf_path)
    match = re.search(r"(\d{8})\(교사용\)\.pdf$", filename)
    db_name = f"{match.group(1)}.db" if match else f"{Path(pdf_path).stem}.db"
    db_path = os.path.join(os.path.dirname(pdf_path), db_name)
    match = re.search(r"^(.*?)\d{8}\(교사용\)\.pdf$", filename)
    exam_category = match.group(1) if match else "Unknown"
    
    print(f"처리 시작: {filename}")
    result = processor.process_pdf(pdf_path, db_path, exam_category)
    print("\n--- 처리 결과 ---")
    print(f"  - 성공: {result.get('success')}")
    print(f"  - 처리된 문제 수: {result.get('processed_questions')}")
    print(f"  - 이슈 있음: {result.get('has_issues')}")
    if result.get('issues'):
        print("  - 이슈 상세:")
        for issue in result['issues']:
            print(f"    {issue}")
    print("------------------")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_single_pdf(sys.argv[1])
    else:
        print("사용법: python pdf_processor.py <PDF파일경로>")