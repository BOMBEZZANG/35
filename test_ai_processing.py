"""Test AI explanation generation with GPT-5.2."""

import asyncio
import logging
from pathlib import Path

from src.exam_pipeline.ai_processor import generate_explanations
from src.exam_pipeline.core.database import QuestionDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_explanation_generation():
    """Test explanation generation with GPT-5.2."""

    # Use the test database we created earlier
    db_path = Path("test_output_4opt.db")

    if not db_path.exists():
        print(f"Error: Test database not found: {db_path}")
        print("Run test_pdf_extraction.py first to create sample database")
        return

    # Load API key from config
    import json
    with open("config.json", "r") as f:
        config = json.load(f)

    openai_api_key = config["OPENAI_API_KEY"]

    print("\n" + "=" * 80)
    print("Testing AI Explanation Generation with GPT-5.2")
    print("=" * 80)

    # Check database status
    db = QuestionDatabase(db_path)
    all_questions = db.get_all_questions()
    questions_without_explanations = db.get_questions_without_explanations()
    db.close()

    print(f"\nDatabase: {db_path}")
    print(f"  Total questions: {len(all_questions)}")
    print(f"  Without explanations: {len(questions_without_explanations)}")

    if not questions_without_explanations:
        print("\n✓ All questions already have explanations!")
        return

    # Limit to first 3 questions for testing (to save API costs)
    print(f"\n[Test Mode] Processing only first 3 questions to save costs")
    print("=" * 80)

    # Temporarily save only 3 questions to process
    db = QuestionDatabase(db_path)
    test_questions = questions_without_explanations[:3]

    # Mark others as processed to skip them
    for q in questions_without_explanations[3:]:
        db.update_answer_description(q.question_id, "[Skipped in test]")
    db.close()

    # Generate explanations
    print("\nGenerating explanations with GPT-5.2...")
    print(f"  Model: gpt-5.2")
    print(f"  Reasoning effort: medium")
    print(f"  Verbosity: medium")
    print()

    stats = await generate_explanations(
        db_path=db_path,
        openai_api_key=openai_api_key,
        model="gpt-5.2",
        reasoning_effort="medium",
        verbosity="medium",
    )

    print("\n" + "=" * 80)
    print("Generation Complete")
    print("=" * 80)
    print(f"  Total questions: {stats['total']}")
    print(f"  Successfully processed: {stats['processed']}")
    print(f"  Failed: {stats['failed']}")

    # Show sample explanations
    if stats['processed'] > 0:
        print("\n" + "=" * 80)
        print("Sample Explanations")
        print("=" * 80)

        db = QuestionDatabase(db_path)
        for q in test_questions[:stats['processed']]:
            updated_q = db.get_question_by_id(q.question_id)
            print(f"\nQuestion #{updated_q.question_number}:")
            print(f"  Text: {updated_q.big_question[:80]}...")
            print(f"  Correct answer: {updated_q.correct_option}")
            print(f"  Explanation: {updated_q.answer_description}")
            print()
        db.close()

    print("=" * 80)
    print("✓ Test completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_explanation_generation())
