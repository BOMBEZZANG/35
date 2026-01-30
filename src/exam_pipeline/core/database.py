"""Database management with SQLite for exam questions."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from .exceptions import DatabaseError
from .models import OXQuiz, Question


class QuestionDatabase:
    """
    Repository pattern for managing exam questions in SQLite.

    Supports both 4-option and 5-option question formats.
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self) -> None:
        """Establish database connection with proper settings."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row  # Access columns by name
            self.conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to database: {e}")

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "QuestionDatabase":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def create_tables(self) -> None:
        """
        Create database tables with updated schema.

        Includes support for 5-option questions and timestamps.
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()

            # Main questions table with 5-option support
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    Question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Question_Number TEXT,
                    Big_Question TEXT,
                    Big_Question_Special BLOB,
                    Question BLOB,

                    Option1 BLOB,
                    Option2 BLOB,
                    Option3 BLOB,
                    Option4 BLOB,
                    Option5 BLOB,

                    Correct_Option INTEGER,
                    Option_Count INTEGER DEFAULT 4,

                    Category TEXT,
                    ExamSession TEXT,
                    Answer_description TEXT,
                    audio TEXT,
                    Date_information TEXT,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Create indexes for performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_category ON questions(Category)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exam_session ON questions(ExamSession)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_option_count ON questions(Option_Count)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_date_information ON questions(Date_information)"
            )

            # Schema version tracking
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_info (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute("INSERT OR IGNORE INTO schema_info (version) VALUES (?)", (self.SCHEMA_VERSION,))

            self.conn.commit()

        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to create tables: {e}")

    def migrate_from_old_schema(self) -> None:
        """
        Migrate database from old schema (without Option5) to new schema.

        Safe to run multiple times (idempotent).
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()

            # Check if Option5 column exists
            cursor.execute("PRAGMA table_info(questions)")
            columns = [row[1] for row in cursor.fetchall()]

            if "Option5" not in columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN Option5 BLOB")

            if "Option_Count" not in columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN Option_Count INTEGER DEFAULT 4")

            if "created_at" not in columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            if "updated_at" not in columns:
                cursor.execute("ALTER TABLE questions ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            # Update Option_Count for existing rows
            cursor.execute("UPDATE questions SET Option_Count = 4 WHERE Option_Count IS NULL")

            self.conn.commit()

        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to migrate schema: {e}")

    def insert_question(self, question: Question) -> int:
        """
        Insert a new question into the database.

        Args:
            question: Question object to insert

        Returns:
            int: ID of inserted question

        Raises:
            DatabaseError: If insert fails
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()

            # Prepare options (pad with NULL if needed)
            options = question.options + [None] * (5 - len(question.options))

            cursor.execute(
                """
                INSERT INTO questions (
                    Question_Number, Big_Question, Big_Question_Special, Question,
                    Option1, Option2, Option3, Option4, Option5,
                    Correct_Option, Option_Count, Category, ExamSession,
                    Answer_description, audio, Date_information
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question.question_number,
                    question.big_question,
                    question.big_question_special_image,
                    question.question_image,
                    *options,
                    question.correct_option,
                    question.option_count,
                    question.category,
                    question.exam_session,
                    question.answer_description,
                    question.audio_path,
                    question.date_information,
                ),
            )

            self.conn.commit()
            return cursor.lastrowid

        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to insert question: {e}")

    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        """
        Retrieve a question by ID.

        Args:
            question_id: Question ID

        Returns:
            Question object or None if not found
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM questions WHERE Question_id = ?", (question_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_question(row)
            return None

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve question: {e}")

    def get_all_questions(self, limit: Optional[int] = None, offset: int = 0) -> List[Question]:
        """
        Retrieve all questions with optional pagination.

        Args:
            limit: Maximum number of questions to return
            offset: Number of questions to skip

        Returns:
            List of Question objects
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()

            if limit:
                cursor.execute(
                    "SELECT * FROM questions ORDER BY Question_id LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            else:
                cursor.execute("SELECT * FROM questions ORDER BY Question_id")

            return [self._row_to_question(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve questions: {e}")

    def get_questions_by_category(self, category: str) -> List[Question]:
        """
        Retrieve all questions for a specific category.

        Args:
            category: Category name

        Returns:
            List of Question objects
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM questions WHERE Category = ? ORDER BY Question_id",
                (category,),
            )

            return [self._row_to_question(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve questions by category: {e}")

    def get_questions_by_option_count(self, option_count: int) -> List[Question]:
        """
        Retrieve all questions with specific option count.

        Args:
            option_count: Number of options (4 or 5)

        Returns:
            List of Question objects
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM questions WHERE Option_Count = ? ORDER BY Question_id",
                (option_count,),
            )

            return [self._row_to_question(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve questions by option count: {e}")

    def get_questions_without_explanations(self) -> List[Question]:
        """
        Retrieve questions that don't have AI explanations yet.

        Returns:
            List of Question objects
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT * FROM questions
                WHERE Answer_description IS NULL OR Answer_description = ''
                ORDER BY Question_id
                """
            )

            return [self._row_to_question(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve questions without explanations: {e}")

    def update_answer_description(self, question_id: int, description: str) -> None:
        """
        Update answer description for a question.

        Args:
            question_id: Question ID
            description: AI-generated explanation
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE questions
                SET Answer_description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE Question_id = ?
                """,
                (description, question_id),
            )
            self.conn.commit()

        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to update answer description: {e}")

    def update_audio_path(self, question_id: int, audio_path: str) -> None:
        """
        Update audio file path for a question.

        Args:
            question_id: Question ID
            audio_path: Path to audio file
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE questions
                SET audio = ?, updated_at = CURRENT_TIMESTAMP
                WHERE Question_id = ?
                """,
                (audio_path, question_id),
            )
            self.conn.commit()

        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to update audio path: {e}")

    def get_categories(self) -> List[str]:
        """
        Get all unique categories.

        Returns:
            List of category names
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT DISTINCT Category FROM questions WHERE Category IS NOT NULL ORDER BY Category"
            )

            return [row[0] for row in cursor.fetchall()]

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve categories: {e}")

    def get_question_count(self) -> int:
        """
        Get total number of questions in database.

        Returns:
            int: Total question count
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM questions")
            return cursor.fetchone()[0]

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to count questions: {e}")

    def _row_to_question(self, row: sqlite3.Row) -> Question:
        """
        Convert database row to Question object.

        Args:
            row: SQLite row

        Returns:
            Question object
        """
        option_count = row["Option_Count"] or 4
        options = [row[f"Option{i}"] for i in range(1, option_count + 1)]

        # Parse timestamps
        created_at = None
        updated_at = None

        if row["created_at"]:
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except (ValueError, TypeError):
                pass

        if row["updated_at"]:
            try:
                updated_at = datetime.fromisoformat(row["updated_at"])
            except (ValueError, TypeError):
                pass

        return Question(
            question_id=row["Question_id"],
            question_number=row["Question_Number"],
            big_question=row["Big_Question"],
            question_image=row["Question"],
            big_question_special_image=row["Big_Question_Special"],
            options=options,
            correct_option=row["Correct_Option"],
            option_count=option_count,
            category=row["Category"],
            exam_session=row["ExamSession"],
            answer_description=row["Answer_description"],
            audio_path=row["audio"],
            date_information=row["Date_information"],
            created_at=created_at,
            updated_at=updated_at,
        )


class OXQuizDatabase:
    """Repository for O/X quiz questions."""

    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to database: {e}")

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> "OXQuizDatabase":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    def create_table(self) -> None:
        """Create O/X quiz table."""
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    Question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Big_Question TEXT,
                    Option1 TEXT DEFAULT 'O',
                    Option2 TEXT DEFAULT 'X',
                    Correct_Option INTEGER,
                    Category TEXT,
                    Answer_description TEXT
                )
                """
            )
            self.conn.commit()

        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to create O/X quiz table: {e}")

    def insert_quiz(self, quiz: OXQuiz) -> int:
        """
        Insert O/X quiz question.

        Args:
            quiz: OXQuiz object

        Returns:
            int: ID of inserted quiz
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO questions (
                    Big_Question, Option1, Option2, Correct_Option,
                    Category, Answer_description
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    quiz.big_question,
                    quiz.option1,
                    quiz.option2,
                    quiz.correct_option,
                    quiz.category,
                    quiz.answer_description,
                ),
            )
            self.conn.commit()
            return cursor.lastrowid

        except sqlite3.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to insert O/X quiz: {e}")

    def get_all_quizzes(self) -> List[OXQuiz]:
        """
        Retrieve all O/X quizzes.

        Returns:
            List of OXQuiz objects
        """
        if not self.conn:
            raise DatabaseError("Database not connected")

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM questions ORDER BY Question_id")

            quizzes = []
            for row in cursor.fetchall():
                quizzes.append(
                    OXQuiz(
                        question_id=row["Question_id"],
                        big_question=row["Big_Question"],
                        correct_option=row["Correct_Option"],
                        category=row["Category"],
                        answer_description=row["Answer_description"],
                    )
                )

            return quizzes

        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve O/X quizzes: {e}")
