# 5_OX_Quiz_Creating.py

import os
import sys
import json
import logging
import re
import sqlite3
from pathlib import Path
from openai import OpenAI
import time
from collections import defaultdict

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)


class Config:
    """설정 파일을 관리하는 클래스"""
    def __init__(self, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"FATAL: 설정 파일 읽기 오류 '{config_path}': {e}")
            sys.exit(1)
        
        self.api_key = config_data.get("OPENAI_API_KEY")
        self.model_name = config_data.get("MODEL_NAME", "o3-2025-04-16")
        
        if not self.api_key:
            logger.error("FATAL: config.json 파일에 OPENAI_API_KEY가 없습니다.")
            sys.exit(1)
        logger.info(f"설정 로드 완료: {config_path}")


class OxQuizGenerator:
    """1.txt 파일들을 기반으로 OX 퀴즈를 생성하고, JSON 및 DB 파일로 저장하는 클래스"""

    def __init__(self, config: Config, selected_folder: str):
        self.client = OpenAI(api_key=config.api_key)
        self.model = config.model_name
        self.base_path = Path(selected_folder)
        # 최종 산출물 경로 정의
        self.final_json_path = self.base_path / "assets" / "OX.json"
        self.final_db_path = self.base_path / "assets" / "quiz.db"
        # 1.txt 파일들이 저장될 경로
        self.output_path = self.base_path / "assets" / "output"
        self.all_quiz_data = []
        self.has_errors = False

    def _get_sorted_db_files(self):
        """DB 파일들을 찾아서 정렬하여 반환합니다."""
        assets_path = self.base_path / "assets"
        if not assets_path.exists():
            logger.error(f"Assets 폴더를 찾을 수 없습니다: {assets_path}")
            return []
        
        # 'question'으로 시작하는 db파일만 대상으로 합니다
        db_files = list(assets_path.glob("question*.db"))
        
        # 파일명 숫자를 기준으로 오름차순 정렬 (question1, question2, ...)
        db_files.sort(key=lambda p: int(re.search(r'(\d+)', p.name).group(1)) if re.search(r'(\d+)', p.name) else 0)
        
        logger.info(f"'{assets_path}'에서 {len(db_files)}개의 DB 파일을 찾았습니다.")
        return db_files

    def _generate_txt_files_from_db(self):
        """DB 파일들을 읽어서 카테고리별로 1.txt 파일을 생성합니다."""
        logger.info("DB 파일에서 1.txt 파일들을 생성하는 중...")
        
        db_files_to_process = self._get_sorted_db_files()
        if not db_files_to_process:
            logger.error("처리할 DB 파일이 없습니다.")
            return {}
            
        # 최신 3개 파일만 처리
        db_files_to_process = db_files_to_process[:3]
        logger.info(f"최신 {len(db_files_to_process)}개 DB 파일을 처리합니다: {[p.name for p in db_files_to_process]}")
        
        category_data = defaultdict(list)
        
        for db_path in db_files_to_process:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # questions 테이블에서 데이터 읽기
                cursor.execute("""
                    SELECT Question_id, Big_Question, Question, Correct_Option, 
                           Option1, Option2, Option3, Option4, Answer_description, 
                           Category, Date_information 
                    FROM questions
                """)
                
                for row in cursor.fetchall():
                    (question_id, big_q, q_text, correct_opt, opt1, opt2, opt3, opt4, desc, cat, date_info) = row
                    
                    # 옵션들 처리 (이미지인 경우 대체 텍스트 사용)
                    options = [o if isinstance(o, str) else "[이미지]" for o in [opt1, opt2, opt3, opt4]]
                    question_text = q_text if isinstance(q_text, str) else "[이미지]"
                    
                    # 정답 옵션 텍스트 가져오기
                    try:
                        correct_option_text = options[int(correct_opt) - 1]
                    except (ValueError, IndexError, TypeError):
                        correct_option_text = "[알 수 없음]"
                    
                    # 출력 텍스트 생성
                    output_text = (
                        f"Question_id: {question_id}\n"
                        f"Big_Question: {big_q or ''}\n"
                        f"Question: {question_text}\n"
                        f"Correct_Option: {correct_opt} (옵션: {correct_option_text})\n"
                        f"Answer_description: {desc or ''}\n"
                        f"Date_information: {date_info or '[날짜 정보 없음]'}\n"
                        "------------------------\n"
                    )
                    
                    category_data[cat or "Uncategorized"].append(output_text)
                
                conn.close()
                logger.info(f"DB 파일 '{db_path.name}' 처리 완료")
                
            except sqlite3.Error as e:
                logger.error(f"DB 파일 '{db_path.name}' 읽기 오류: {e}")
                continue
        
        # 카테고리별로 1.txt 파일 생성
        final_category_content = {}
        self.output_path.mkdir(exist_ok=True, parents=True)
        
        for category, entries in category_data.items():
            # 안전한 카테고리명 생성 (파일시스템에서 사용할 수 없는 문자 제거)
            safe_category_name = category.replace('/', '_').replace('\\', '_')
            category_folder = self.output_path / safe_category_name
            category_folder.mkdir(exist_ok=True)
            
            # 전체 내용 구성
            full_content = f"Category: {category}\n\n" + "".join(entries)
            final_category_content[safe_category_name] = full_content
            
            # 1.txt 파일로 저장
            txt_file_path = category_folder / "1.txt"
            with open(txt_file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            logger.info(f"카테고리 '{safe_category_name}'의 1.txt 파일 생성 완료: {txt_file_path}")
        
        logger.info(f"총 {len(final_category_content)}개 카테고리의 1.txt 파일 생성이 완료되었습니다.")
        return final_category_content

    def _collect_all_category_content(self):
        """모든 카테고리의 내용을 수집하고 요약합니다."""
        source_path = self.output_path
        
        if not source_path.exists() or not source_path.is_dir():
            logger.error(f"퀴즈 소스 경로를 찾을 수 없습니다: {source_path}")
            logger.error(f"'{self.base_path / 'assets'}' 폴더 내에 'output' 폴더가 존재하는지 확인해주세요.")
            return None, []

        category_folders = [d for d in source_path.iterdir() if d.is_dir()]
        if not category_folders:
            logger.error(f"'{source_path}' 폴더에서 카테고리 폴더를 찾을 수 없습니다.")
            return None, []

        category_contents = {}
        category_names = []
        
        for category_path in category_folders:
            category_name = category_path.name
            txt_file_path = category_path / "1.txt"
            
            if not txt_file_path.exists():
                logger.warning(f"파일을 찾을 수 없어 건너뜁니다: {txt_file_path}")
                continue
                
            logger.info(f"카테고리 '{category_name}' 내용을 수집 중...")
            with open(txt_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 내용이 너무 길면 앞부분만 사용 (토큰 제한 고려)
            if len(content) > 15000:  # 대략적인 문자 수 제한
                content = content[:15000] + "... (내용 생략)"
                logger.warning(f"'{category_name}' 카테고리 내용이 길어서 15000자로 제한했습니다.")
                
            category_contents[category_name] = content
            category_names.append(category_name)
            
        logger.info(f"총 {len(category_names)}개 카테고리의 내용을 수집했습니다: {category_names}")
        return category_contents, category_names

    def _parse_quiz_response(self, response_text: str) -> list:
        """
        Enhanced GPT response parsing with better error handling and multiple parsing strategies
        """
        logger.info(f"Parsing response of length: {len(response_text)}")
        
        # Strategy 1: Look for JSON code blocks
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1).strip()
                logger.info("Found JSON code block, attempting to parse...")
                return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON code block parsing failed: {e}")
        
        # Strategy 2: Look for JSON array patterns
        try:
            # More flexible pattern matching for JSON arrays
            json_pattern = r'\[\s*\{[\s\S]*?\}\s*\]'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                logger.info("Found JSON array pattern, attempting to parse...")
                return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON array pattern parsing failed: {e}")
        
        # Strategy 3: Try to find and fix common JSON issues
        try:
            # Remove any text before first '[' and after last ']'
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_text = response_text[start_idx:end_idx+1]
                logger.info("Extracted JSON array boundaries, attempting to parse...")
                return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON boundary extraction parsing failed: {e}")
        
        # Strategy 4: Try to extract individual question objects and rebuild array
        try:
            # Find all individual question objects
            question_pattern = r'\{\s*"Question_id"[^}]*\}'
            questions = re.findall(question_pattern, response_text, re.DOTALL)
            
            if questions:
                logger.info(f"Found {len(questions)} individual question objects, attempting to rebuild array...")
                # Try to parse each question individually
                valid_questions = []
                for i, q in enumerate(questions):
                    try:
                        parsed_q = json.loads(q)
                        valid_questions.append(parsed_q)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse question {i+1}")
                        continue
                
                if valid_questions:
                    logger.info(f"Successfully parsed {len(valid_questions)} questions")
                    return valid_questions
        except Exception as e:
            logger.warning(f"Individual question extraction failed: {e}")
        
        # If all strategies fail, log detailed error information
        logger.error("All parsing strategies failed. Analyzing response...")
        logger.error(f"Response length: {len(response_text)}")
        logger.error(f"Response preview (first 500 chars): {response_text[:500]}")
        logger.error(f"Response end (last 500 chars): {response_text[-500:]}")
        
        # Check for common error patterns
        if "omitted due to length" in response_text.lower():
            logger.error("Response was truncated due to length - consider reducing quiz count per request")
        elif "complexity" in response_text.lower():
            logger.error("Response was truncated due to complexity - consider simplifying the prompt")
        
        return []

    def _generate_quizzes_in_batches(self):
        """
        Generate quizzes in smaller batches to avoid response size issues
        """
        category_contents, category_names = self._collect_all_category_content()
        
        if not category_contents:
            logger.error("No category content to process.")
            return False
        
        total_categories = len(category_names)
        target_total_quizzes = 100
        
        # Calculate batch size (aim for ~25 quizzes per batch)
        batch_size = 25
        num_batches = (target_total_quizzes + batch_size - 1) // batch_size
        
        logger.info(f"Generating {target_total_quizzes} quizzes in {num_batches} batches of ~{batch_size} each")
        
        all_generated_quizzes = []
        current_question_id = 1
        
        for batch_num in range(num_batches):
            start_quiz = batch_num * batch_size + 1
            end_quiz = min((batch_num + 1) * batch_size, target_total_quizzes)
            quizzes_in_batch = end_quiz - start_quiz + 1
            
            logger.info(f"Generating batch {batch_num + 1}/{num_batches}: quizzes {start_quiz}-{end_quiz} ({quizzes_in_batch} quizzes)")
            
            # Distribute quizzes among categories for this batch
            quizzes_per_category = quizzes_in_batch // total_categories
            remaining_quizzes = quizzes_in_batch % total_categories
            
            batch_distribution = {}
            for i, category_name in enumerate(category_names):
                count = quizzes_per_category
                if i < remaining_quizzes:
                    count += 1
                batch_distribution[category_name] = count
            
            # Generate prompt for this batch
            system_prompt = """당신은 주어진 자료를 바탕으로 OX 퀴즈를 만드는 전문가입니다. 
각 카테고리별로 지정된 개수만큼 정확히 퀴즈를 생성해야 합니다.
반드시 JSON 배열 형식으로만 응답하며, 다른 부가 설명이나 텍스트를 포함해서는 안 됩니다."""
            
            content_sections = []
            for category_name in category_names:
                quiz_count = batch_distribution[category_name]
                if quiz_count > 0:  # Only include categories with quizzes in this batch
                    content = category_contents[category_name]
                    content_sections.append(f"""
=== [{category_name}] 카테고리 ({quiz_count}개 퀴즈) ===
{content}
""")
            
            user_prompt = f"""
아래 내용을 바탕으로 OX (참/거짓) 퀴즈를 생성해 주세요.

### 이번 배치 퀴즈 분배:
{chr(10).join([f"- {name}: {count}개 퀴즈" for name, count in batch_distribution.items() if count > 0])}

### 중요 규칙:
- 각 문제는 명확하게 참(O) 또는 거짓(X)으로 답할 수 있어야 합니다
- 해설은 왜 정답이 O 또는 X인지 구체적인 근거를 들어 간결하게 설명해야 합니다
- 전체적으로 정답 O와 X의 비율이 대략 50:50이 되도록 합니다
- 각 카테고리에서 지정된 개수만큼 정확히 생성해야 합니다
- 오직 JSON 배열로만 출력하며 다른 텍스트는 포함하지 마세요

### 각 퀴즈의 JSON 형식:
{{
  "Question_id": <{current_question_id}부터 시작하는 문제 번호>,
  "Big_Question": "<O/X 형식 질문 서술문>",
  "Option1": "O",
  "Option2": "X", 
  "Correct_Option": <1(O) 또는 2(X)>,
  "Category": "<카테고리명>",
  "Answer_description": "<정답에 대한 구체적인 해설>"
}}

### 내용:
{''.join(content_sections)}

JSON 배열 형식으로만 퀴즈를 생성해 주세요.
"""
            
            try:
                logger.info(f"Sending API request for batch {batch_num + 1}...")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_completion_tokens=8000  # Smaller limit for batches
                    # temperature parameter removed - o3 model only supports default value
                )
                
                if response.choices:
                    finish_reason = response.choices[0].finish_reason
                    logger.info(f"API response received. Finish reason: {finish_reason}")
                    
                    if finish_reason == 'content_filter':
                        logger.error(f"Content filter blocked response for batch {batch_num + 1}")
                        self.has_errors = True
                        continue
                    
                    response_text = response.choices[0].message.content or ""
                    batch_quizzes = self._parse_quiz_response(response_text)
                    
                    if batch_quizzes:
                        # Update question IDs to be sequential
                        for quiz in batch_quizzes:
                            quiz['Question_id'] = current_question_id
                            current_question_id += 1
                        
                        all_generated_quizzes.extend(batch_quizzes)
                        logger.info(f"✅ Batch {batch_num + 1} completed: {len(batch_quizzes)} quizzes generated")
                        
                        # Log category distribution for this batch
                        batch_categories = {}
                        for quiz in batch_quizzes:
                            cat = quiz.get('Category', 'Unknown')
                            batch_categories[cat] = batch_categories.get(cat, 0) + 1
                        
                        for cat, count in batch_categories.items():
                            expected = batch_distribution.get(cat, 0)
                            logger.info(f"  - {cat}: {count} generated (expected: {expected})")
                        
                    else:
                        logger.error(f"❌ Failed to parse batch {batch_num + 1}")
                        self.has_errors = True
                        continue
                
                # Small delay between batches to avoid rate limiting
                if batch_num < num_batches - 1:
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Error generating batch {batch_num + 1}: {e}")
                self.has_errors = True
                continue
        
        if all_generated_quizzes:
            self.all_quiz_data = all_generated_quizzes
            logger.info(f"✅ All batches completed! Total quizzes generated: {len(all_generated_quizzes)}")
            
            # Final category count summary
            final_categories = {}
            for quiz in all_generated_quizzes:
                cat = quiz.get('Category', 'Unknown')
                final_categories[cat] = final_categories.get(cat, 0) + 1
            
            logger.info("Final quiz distribution:")
            for cat, count in final_categories.items():
                logger.info(f"  - {cat}: {count} quizzes")
            
            return True
        else:
            logger.error("❌ No quizzes were successfully generated in any batch")
            return False

    def _save_to_json(self):
        """취합된 모든 퀴즈 데이터를 JSON 파일로 저장합니다."""
        logger.info(f"생성된 퀴즈를 JSON 파일로 저장합니다: {self.final_json_path}")
        try:
            self.final_json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.final_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_quiz_data, f, ensure_ascii=False, indent=2)
            logger.info("JSON 파일 저장이 완료되었습니다.")
        except Exception as e:
            logger.error(f"JSON 파일 저장 중 오류 발생: {e}")
            self.has_errors = True

    def _save_to_db(self):
        """취합된 모든 퀴즈 데이터를 SQLite DB 파일로 저장합니다."""
        logger.info(f"생성된 퀴즈를 SQLite DB 파일로 저장합니다: {self.final_db_path}")
        try:
            self.final_db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.final_db_path))
            cursor = conn.cursor()

            cursor.execute("DROP TABLE IF EXISTS questions")
            
            cursor.execute("""
            CREATE TABLE questions (
                Question_id INTEGER PRIMARY KEY,
                Big_Question TEXT NOT NULL,
                Option1 TEXT NOT NULL,
                Option2 TEXT NOT NULL,
                Correct_Option INTEGER NOT NULL,
                Category TEXT,
                Answer_description TEXT
            )
            """)

            to_insert = []
            for quiz in self.all_quiz_data:
                to_insert.append((
                    quiz.get('Question_id'),
                    quiz.get('Big_Question'),
                    quiz.get('Option1', 'O'),
                    quiz.get('Option2', 'X'),
                    quiz.get('Correct_Option'),
                    quiz.get('Category'),
                    quiz.get('Answer_description')
                ))

            cursor.executemany("""
            INSERT INTO questions (Question_id, Big_Question, Option1, Option2, Correct_Option, Category, Answer_description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, to_insert)

            conn.commit()
            conn.close()
            logger.info("SQLite DB 파일 저장이 완료되었습니다.")
        except sqlite3.Error as e:
            logger.error(f"SQLite DB 작업 중 오류 발생: {e}")
            self.has_errors = True
        except Exception as e:
            logger.error(f"DB 파일 저장 중 예상치 못한 오류 발생: {e}")
            self.has_errors = True

    def run_generation(self):
        """
        Updated main generation process using batch approach
        """
        logger.info("Starting O/X quiz generation...")
        
        # *** Step 1: Generate 1.txt files from DB ***
        logger.info("\n=== Step 1: Generate 1.txt files from DB ===")
        category_data = self._generate_txt_files_from_db()
        if not category_data:
            logger.error("Failed to generate 1.txt files from DB.")
            return False
        
        # *** Step 2: Generate O/X quizzes in batches ***
        logger.info("\n=== Step 2: Generate O/X quizzes ===")
        if not self._generate_quizzes_in_batches():
            logger.error("Quiz generation failed.")
            return False

        if not self.all_quiz_data:
            logger.error("No quiz data generated. Stopping process.")
            return False

        logger.info(f"Generated {len(self.all_quiz_data)} quizzes total. Starting final file save.")

        # *** Step 3: Final file save ***
        logger.info("\n=== Step 3: Final file save ===")
        
        # Ensure sequential Question_id numbering
        for i, quiz in enumerate(self.all_quiz_data):
            quiz['Question_id'] = i + 1

        # Save to JSON and DB
        self._save_to_json()
        self._save_to_db()

        if self.has_errors:
            logger.warning("Some errors occurred but files were generated with successful data.")
            return True
        else:
            logger.info("All tasks completed successfully!")
        
        return True


def main():
    """스크립트 실행을 위한 메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python 5_OX_Quiz_Creating.py <selected_folder_path>")
        sys.exit(1)
    
    selected_folder = sys.argv[1]
    
    script_directory = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_directory, "config.json")
    
    if not os.path.exists(config_path):
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)

    config = Config(config_path)
    generator = OxQuizGenerator(config, selected_folder)
    
    success = generator.run_generation()
    if not success:
        logger.error("퀴즈 생성 및 변환 과정에서 하나 이상의 오류가 발생했습니다.")
        sys.exit(1)


if __name__ == "__main__":
    main()