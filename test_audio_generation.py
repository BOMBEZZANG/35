"""Test audio generation with Edge-TTS."""

import asyncio
import logging
from pathlib import Path

from src.exam_pipeline.audio import generate_question_audio
from src.exam_pipeline.core.database import QuestionDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_audio_generation():
    """Test audio generation with Edge-TTS."""

    # Use the test database we created earlier
    db_path = Path("test_output_4opt.db")

    if not db_path.exists():
        print(f"Error: Test database not found: {db_path}")
        print("Run test_pdf_extraction.py first to create sample database")
        return

    print("\n" + "=" * 80)
    print("Testing Audio Generation with Edge-TTS")
    print("=" * 80)

    # Check database status
    db = QuestionDatabase(db_path)
    all_questions = db.get_all_questions()
    db.close()

    print(f"\nDatabase: {db_path}")
    print(f"  Total questions: {len(all_questions)}")

    # Create test audio directory
    audio_output_dir = Path("test_audio_output")
    audio_output_dir.mkdir(exist_ok=True)

    # Test with first 3 questions only (to save time)
    print(f"\n[Test Mode] Processing only first 3 questions")
    print("=" * 80)

    # Temporarily create a small test database with 3 questions
    test_db_path = Path("test_audio_3q.db")

    # Copy first 3 questions to new database
    db = QuestionDatabase(db_path)
    test_questions = db.get_all_questions(limit=3)
    db.close()

    # Create new database with 3 questions
    test_db = QuestionDatabase(test_db_path)
    test_db.create_tables()
    for q in test_questions:
        test_db.insert_question(q)
    test_db.close()

    print("\nGenerating audio with Edge-TTS...")
    print(f"  Voice: 선희 (ko-KR-SunHiNeural)")
    print(f"  Output: {audio_output_dir}/question1/")
    print()

    # Generate audio
    stats = await generate_question_audio(
        db_path=test_db_path,
        output_dir=audio_output_dir,
        category_index=1,
        skip_existing=False,  # Always regenerate for testing
    )

    print("\n" + "=" * 80)
    print("Generation Complete")
    print("=" * 80)
    print(f"  Total questions: {stats['total']}")
    print(f"  Successfully generated: {stats['success']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Database paths updated: {stats['db_updated']}")

    # List generated files
    if stats['success'] > 0:
        print("\n" + "=" * 80)
        print("Generated Audio Files")
        print("=" * 80)

        question_dir = audio_output_dir / "question1"
        for audio_file in sorted(question_dir.glob("*.mp3")):
            file_size_kb = audio_file.stat().st_size / 1024
            print(f"  {audio_file.name} ({file_size_kb:.1f} KB)")

    # Verify database updates
    print("\n" + "=" * 80)
    print("Database Verification")
    print("=" * 80)

    test_db = QuestionDatabase(test_db_path)
    for q in test_db.get_all_questions():
        audio_status = "✓" if q.audio_path else "✗"
        print(f"  Question {q.question_id}: {audio_status} {q.audio_path or '(no audio path)'}")
    test_db.close()

    print("\n" + "=" * 80)
    print("✓ Test completed successfully!")
    print("=" * 80)
    print(f"\nGenerated files are in: {audio_output_dir}/question1/")


if __name__ == "__main__":
    asyncio.run(test_audio_generation())
