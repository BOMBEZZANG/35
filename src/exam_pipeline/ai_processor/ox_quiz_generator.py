"""OX Quiz Generator - Generate true/false quizzes from question database.

This module generates O/X (true/false) quizzes using GPT-5.2 based on
existing question explanations and content from the database.
"""

import json
import logging
import re
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

from ..core import QuestionDatabase

logger = logging.getLogger(__name__)


class OXQuizGenerator:
    """
    Generate O/X (true/false) quizzes using GPT-5.2.

    Features:
    - Generates 100 OX quizzes in batches of 25
    - Multi-strategy JSON parsing with 4 fallback strategies
    - Category-based distribution
    - Saves to both JSON and SQLite database
    """

    def __init__(
        self,
        openai_api_key: str,
        db_repository: QuestionDatabase,
        assets_dir: Path,
        model: str = "gpt-5.2",
    ):
        """
        Initialize OX Quiz Generator.

        Args:
            openai_api_key: OpenAI API key
            db_repository: Question database for reading questions
            assets_dir: Path to assets directory for output
            model: Model name (default: gpt-5.2)
        """
        self.db_repository = db_repository
        self.assets_dir = Path(assets_dir)

        # Initialize OpenAI client
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model

        # Output paths
        self.output_path = self.assets_dir / "output"
        self.final_json_path = self.assets_dir / "OX.json"
        self.final_db_path = self.assets_dir / "quiz.db"

        # Quiz data
        self.all_quiz_data: List[Dict] = []
        self.has_errors = False

        logger.info(f"OXQuizGenerator initialized with model: {self.model}")

    def _generate_txt_files_from_db(self) -> Dict[str, str]:
        """
        Generate 1.txt files from database for each category.

        Returns:
            Dictionary mapping category names to their content
        """
        logger.info("Generating 1.txt files from database...")

        # Get all questions with explanations
        questions = self.db_repository.get_all_questions()

        if not questions:
            logger.error("No questions found in database")
            return {}

        # Group questions by category
        category_data = defaultdict(list)

        for q in questions:
            # Get option text (handle both text and BLOB)
            options = []
            for opt_value in q.options:
                if isinstance(opt_value, bytes):
                    options.append("[이미지]")
                else:
                    options.append(opt_value)

            # Get correct option text
            try:
                correct_idx = int(q.correct_option) - 1
                if 0 <= correct_idx < len(options):
                    correct_option_text = options[correct_idx]
                else:
                    correct_option_text = "[알 수 없음]"
            except (ValueError, TypeError):
                correct_option_text = "[알 수 없음]"

            # Get question text (handle BLOB)
            if q.question_image:
                question_text = "[이미지]"
            else:
                question_text = q.big_question or ""

            # Format output
            output_text = (
                f"Question_id: {q.question_id}\n"
                f"Big_Question: {q.big_question or ''}\n"
                f"Question: {question_text}\n"
                f"Correct_Option: {q.correct_option} (옵션: {correct_option_text})\n"
                f"Answer_description: {q.answer_description or ''}\n"
                f"Date_information: {q.date_information or '[날짜 정보 없음]'}\n"
                "------------------------\n"
            )

            category = q.category or "Uncategorized"
            category_data[category].append(output_text)

        # Save to 1.txt files
        final_category_content = {}
        self.output_path.mkdir(exist_ok=True, parents=True)

        for category, entries in category_data.items():
            # Safe category name (remove filesystem-unsafe characters)
            safe_category_name = category.replace('/', '_').replace('\\', '_')
            category_folder = self.output_path / safe_category_name
            category_folder.mkdir(exist_ok=True)

            # Full content
            full_content = f"Category: {category}\n\n" + "".join(entries)
            final_category_content[safe_category_name] = full_content

            # Save to 1.txt
            txt_file_path = category_folder / "1.txt"
            with open(txt_file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            logger.info(f"Created 1.txt for category '{safe_category_name}': {txt_file_path}")

        logger.info(f"Generated 1.txt files for {len(final_category_content)} categories")
        return final_category_content

    def _parse_quiz_response(self, response_text: str) -> List[Dict]:
        """
        Parse GPT response with multiple fallback strategies.

        Enhanced JSON parsing with 4 fallback strategies to handle
        various response formats from GPT.

        Args:
            response_text: Raw response from GPT

        Returns:
            List of parsed quiz dictionaries
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

    def _generate_quizzes_in_batches(
        self,
        category_contents: Dict[str, str],
        category_names: List[str],
    ) -> bool:
        """
        Generate quizzes in batches of 25.

        Args:
            category_contents: Dictionary mapping category names to their content
            category_names: List of category names

        Returns:
            True if successful, False otherwise
        """
        if not category_contents:
            logger.error("No category content to process")
            return False

        total_categories = len(category_names)
        target_total_quizzes = 100
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
                    # Limit content length to avoid token limits
                    if len(content) > 15000:
                        content = content[:15000] + "... (내용 생략)"
                        logger.warning(f"Category '{category_name}' content limited to 15000 chars")
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
                    model=self.model,  # GPT-5.2
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_completion_tokens=8000
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
        """Save all quiz data to JSON file."""
        logger.info(f"Saving quizzes to JSON file: {self.final_json_path}")
        try:
            self.final_json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.final_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.all_quiz_data, f, ensure_ascii=False, indent=2)
            logger.info("✅ JSON file saved successfully")
        except Exception as e:
            logger.error(f"Error saving JSON file: {e}")
            self.has_errors = True

    def _save_to_db(self):
        """Save all quiz data to SQLite database."""
        logger.info(f"Saving quizzes to SQLite database: {self.final_db_path}")
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
            logger.info("✅ SQLite database saved successfully")
        except sqlite3.Error as e:
            logger.error(f"SQLite error: {e}")
            self.has_errors = True
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            self.has_errors = True

    def generate(self) -> bool:
        """
        Main generation process.

        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting O/X quiz generation...")

        # Step 1: Generate 1.txt files from database
        logger.info("\n=== Step 1: Generate 1.txt files from database ===")
        category_contents = self._generate_txt_files_from_db()
        if not category_contents:
            logger.error("Failed to generate 1.txt files from database")
            return False

        category_names = list(category_contents.keys())

        # Step 2: Generate O/X quizzes in batches
        logger.info("\n=== Step 2: Generate O/X quizzes ===")
        if not self._generate_quizzes_in_batches(category_contents, category_names):
            logger.error("Quiz generation failed")
            return False

        if not self.all_quiz_data:
            logger.error("No quiz data generated. Stopping process.")
            return False

        logger.info(f"Generated {len(self.all_quiz_data)} quizzes total. Starting final file save.")

        # Step 3: Final file save
        logger.info("\n=== Step 3: Final file save ===")

        # Ensure sequential Question_id numbering
        for i, quiz in enumerate(self.all_quiz_data):
            quiz['Question_id'] = i + 1

        # Save to JSON and DB
        self._save_to_json()
        self._save_to_db()

        if self.has_errors:
            logger.warning("Some errors occurred but files were generated with successful data")
            return True
        else:
            logger.info("✅ All tasks completed successfully!")

        return True


def generate_ox_quizzes(
    openai_api_key: str,
    db_repository: QuestionDatabase,
    assets_dir: Path,
    model: str = "gpt-5.2",
) -> bool:
    """
    Convenience function to generate OX quizzes.

    Args:
        openai_api_key: OpenAI API key
        db_repository: Question database
        assets_dir: Path to assets directory
        model: Model name (default: gpt-5.2)

    Returns:
        True if successful, False otherwise

    Example:
        >>> db_repo = QuestionDatabase(Path("test.db"))
        >>> success = generate_ox_quizzes("sk-...", db_repo, Path("assets"))
    """
    generator = OXQuizGenerator(openai_api_key, db_repository, assets_dir, model)
    return generator.generate()
