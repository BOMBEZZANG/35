"""Test OX Quiz Generator with GPT-5.2."""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from src.exam_pipeline.core import QuestionDatabase
from src.exam_pipeline.ai_processor import OXQuizGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_ox_quiz_generator():
    """Test the OX Quiz Generator."""
    print("=" * 70)
    print("Testing OX Quiz Generator (GPT-5.2)")
    print("=" * 70)
    print()

    # Setup paths
    env_file = Path("config/.env")
    test_db_path = Path("test_output_4opt.db")
    test_assets_dir = Path("test_assets_ox")

    # Load environment variables
    load_dotenv(env_file)

    # Verify database exists
    if not test_db_path.exists():
        print(f"❌ Error: Database not found: {test_db_path}")
        print()
        print("Please run test_phase3.py (PDF extraction) and test_phase4.py (AI explanations) first.")
        return False

    # Verify it has questions with explanations
    import sqlite3
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM questions WHERE Answer_description IS NOT NULL AND Answer_description != ''")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        print(f"❌ Error: No questions with explanations found in database")
        print()
        print("Please run test_phase4.py first to generate explanations.")
        return False

    print(f"✓ Found {count} questions with explanations in database")
    print()

    # Create test assets directory
    test_assets_dir.mkdir(exist_ok=True)

    try:
        # Get API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("❌ Error: OPENAI_API_KEY not found in environment")
            print("Please set OPENAI_API_KEY in config/.env")
            return False

        model = "gpt-5.2"
        print(f"✓ Configuration loaded")
        print(f"  Model: {model}")
        print()

        # Initialize database repository
        db_repository = QuestionDatabase(test_db_path)
        print(f"✓ Database repository initialized")
        print()

        # Initialize OX Quiz Generator
        generator = OXQuizGenerator(
            openai_api_key=openai_api_key,
            db_repository=db_repository,
            assets_dir=test_assets_dir,
            model=model
        )
        print(f"✓ OX Quiz Generator initialized")
        print()

        # Generate quizzes
        print("=" * 70)
        print("Starting OX Quiz Generation")
        print("=" * 70)
        print()
        print("This will:")
        print("  1. Generate 1.txt files from database (category-based)")
        print("  2. Generate 100 OX quizzes in 4 batches of 25 using GPT-5.2")
        print("  3. Save to OX.json and quiz.db")
        print()

        success = generator.generate()

        if success:
            print()
            print("=" * 70)
            print("✅ OX Quiz Generation Complete!")
            print("=" * 70)
            print()

            # Verify outputs
            ox_json_path = test_assets_dir / "OX.json"
            quiz_db_path = test_assets_dir / "quiz.db"

            if ox_json_path.exists():
                import json
                with open(ox_json_path, 'r', encoding='utf-8') as f:
                    quizzes = json.load(f)
                print(f"✓ OX.json created: {len(quizzes)} quizzes")
                print()

                # Show first quiz as example
                if quizzes:
                    print("Example quiz:")
                    print(f"  Question ID: {quizzes[0].get('Question_id')}")
                    print(f"  Question: {quizzes[0].get('Big_Question')[:100]}...")
                    print(f"  Correct Option: {quizzes[0].get('Correct_Option')} ({'O' if quizzes[0].get('Correct_Option') == 1 else 'X'})")
                    print(f"  Category: {quizzes[0].get('Category')}")
                    print(f"  Explanation: {quizzes[0].get('Answer_description')[:100]}...")
                    print()

            if quiz_db_path.exists():
                conn = sqlite3.connect(quiz_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM questions")
                count = cursor.fetchone()[0]
                cursor.execute("SELECT Question_id, Big_Question, Correct_Option, Category FROM questions LIMIT 3")
                samples = cursor.fetchall()
                conn.close()

                print(f"✓ quiz.db created: {count} quizzes")
                print()
                print("Sample quizzes from database:")
                for q_id, question, correct_opt, category in samples:
                    print(f"  [{q_id}] {question[:60]}... (정답: {'O' if correct_opt == 1 else 'X'}, 카테고리: {category})")
                print()

            # Show output directory structure
            output_path = test_assets_dir / "output"
            if output_path.exists():
                categories = list(output_path.glob("*/"))
                print(f"✓ Created 1.txt files for {len(categories)} categories:")
                for cat in categories:
                    txt_file = cat / "1.txt"
                    if txt_file.exists():
                        size_kb = txt_file.stat().st_size / 1024
                        print(f"  - {cat.name}: {size_kb:.1f} KB")
                print()

            print("=" * 70)
            print("Test Passed!")
            print("=" * 70)
            return True

        else:
            print()
            print("=" * 70)
            print("❌ OX Quiz Generation Failed")
            print("=" * 70)
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_ox_quiz_generator()
    exit(0 if success else 1)
