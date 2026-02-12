"""Test PDF extraction with 6-stage image assignment algorithm."""

import logging
from pathlib import Path

from src.exam_pipeline.pdf_extractor import PDFParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_pdf_extraction():
    """Test PDF parsing with a sample file."""

    # Find sample PDF from downloaded files
    pdf_dir = Path.home() / "Desktop/Apps/qcjongmin/appauto/raw_DB/rawdbs/프로그래밍기능사"

    if not pdf_dir.exists():
        print(f"Error: PDF directory not found: {pdf_dir}")
        return

    # Get first PDF file
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"Error: No PDF files found in {pdf_dir}")
        return

    pdf_path = pdf_files[0]
    print(f"\nTesting with: {pdf_path.name}")
    print("=" * 80)

    # Test with 4-option parser
    print("\n[4-Option Parser]")
    parser_4opt = PDFParser(option_count=4)

    try:
        questions, all_images = parser_4opt.parse_pdf(pdf_path, exam_name="프로그래밍기능사")

        print(f"\n✓ Successfully parsed PDF")
        print(f"  Total questions: {len(questions)}")
        print(f"  Total images: {len(all_images)}")

        # Check unassigned images
        unassigned = [img for img in all_images if not img['assigned']]
        print(f"  Unassigned images: {len(unassigned)}")

        # Sample first question
        if questions:
            q1 = questions[0]
            print(f"\n  Sample Question #{q1.get('question_number')}:")
            print(f"    Text: {q1.get('Big_Question', '')[:100]}...")
            print(f"    Has Question Image: {q1.get('Question') is not None}")
            print(f"    Has Big_Question_Special: {q1.get('Big_Question_Special') is not None}")

            for i in range(4):
                opt_val = q1['Options'][i]
                if isinstance(opt_val, bytes):
                    opt_display = f"[Image, {len(opt_val)} bytes]"
                else:
                    opt_display = opt_val[:50] if opt_val else "[Empty]"
                print(f"    Option {i+1}: {opt_display}")

            correct = q1.get('Correct_option_index')
            if correct is not None:
                print(f"    Correct Answer: {correct + 1}")

        # Test database save
        print(f"\n[Testing Database Save]")
        output_db = Path("test_output_4opt.db")
        parser_4opt.save_to_database(
            questions,
            output_db,
            category="프로그래밍기능사",
            exam_session=pdf_path.stem.replace("프로그래밍기능사", "")  # Extract date
        )
        print(f"  ✓ Saved to: {output_db}")

        # Verify database
        from src.exam_pipeline.core.database import QuestionDatabase
        db = QuestionDatabase(output_db)
        saved_questions = db.get_questions_by_category("프로그래밍기능사")
        print(f"  ✓ Verified: {len(saved_questions)} questions in database")

        print("\n" + "=" * 80)
        print("✓ All tests passed!")

    except Exception as e:
        print(f"\n✗ Error during parsing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_extraction()
