"""
Question TTS generator using Edge-TTS (Microsoft Azure TTS).

Generates Korean audio explanations for exam questions with async processing,
retry logic, and FFmpeg compression.

Supports Korean voices: 선희 (SunHi), 현수 (Hyunsu), 인준 (InJoon)
"""

import asyncio
import logging
import random
import re
import subprocess
from pathlib import Path
from typing import List, Optional

import edge_tts

from ..core.database import QuestionDatabase
from ..core.models import Question

logger = logging.getLogger(__name__)

# Korean voice mapping
KOREAN_VOICES = {
    "선희": "ko-KR-SunHiNeural",
    "현수": "ko-KR-HyunsuNeural",
    "인준": "ko-KR-InJoonNeural",
}


class QuestionTTSGenerator:
    """
    Generates Korean audio for exam questions using Edge-TTS.

    Features:
    - Async processing with semaphore (max 10 concurrent requests)
    - Retry logic with exponential backoff (5 retries)
    - FFmpeg compression to 32kbps, 16kHz
    - Database update with audio paths
    - Multiple Korean voices: 선희, 현수, 인준
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        max_retries: int = 5,
        voice: str = "선희",
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ):
        """
        Initialize TTS generator.

        Args:
            max_concurrent: Max concurrent TTS requests (default: 10)
            max_retries: Max retry attempts (default: 5)
            voice: Korean voice name - 선희/현수/인준 (default: 선희)
            rate: Speaking rate adjustment, e.g., "+10%", "-5%" (default: +0%)
            pitch: Pitch adjustment, e.g., "+5Hz", "-10Hz" (default: +0Hz)
        """
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries

        # Validate and set voice
        if voice not in KOREAN_VOICES:
            logger.warning(f"Unknown voice '{voice}', using '선희' as default")
            voice = "선희"

        self.voice_name = KOREAN_VOICES[voice]
        self.rate = rate
        self.pitch = pitch

        # Semaphore to limit concurrent requests
        self.semaphore = asyncio.Semaphore(max_concurrent)

        logger.info(f"Edge-TTS initialized: voice={voice} ({self.voice_name}), rate={rate}, pitch={pitch}")

    def _build_audio_text(self, question: Question) -> str:
        """
        Build audio text from question data.

        Args:
            question: Question object

        Returns:
            Formatted audio text string
        """
        parts = [f"{question.question_number}번. "]

        # Add big question
        if question.big_question:
            parts.append(f"{question.big_question}. ")

        # Add main question (if text)
        if question.question_image is None:
            # Question is stored in big_question for text-only
            pass
        elif isinstance(question.question_image, str):
            parts.append(f"{question.question_image}. ")

        # Add options (numbered 일, 이, 삼, 사, 오)
        option_labels = ["일", "이", "삼", "사", "오"]
        for i, option in enumerate(question.options):
            if option and isinstance(option, str):
                label = option_labels[i] if i < len(option_labels) else str(i + 1)
                parts.append(f"{label}. {option}. ")

        # Add correct answer
        if question.correct_option:
            parts.append(f"정답은 {question.correct_option}번 입니다. ")

        # Add explanation
        if question.answer_description:
            # Remove redundant ending
            cleaned_desc = re.sub(
                r"따라서 정답은 [1-5]입니다\.",
                "",
                question.answer_description
            ).strip()
            if cleaned_desc:
                parts.append(f"{cleaned_desc}. ")

        return "".join(parts)

    def _compress_audio(self, input_file: Path) -> None:
        """
        Compress audio file using FFmpeg (32kbps, 16kHz).

        Args:
            input_file: Path to MP3 file
        """
        if not input_file.exists():
            return

        output_file_compressed = input_file.with_name(
            input_file.stem + "_compressed.mp3"
        )

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(input_file),
                    "-b:a", "32k",
                    "-ar", "16000",
                    "-y",
                    "-loglevel", "error",
                    str(output_file_compressed)
                ],
                check=True
            )

            # Replace original with compressed
            input_file.unlink()
            output_file_compressed.rename(input_file)

            logger.debug(f"Compressed: {input_file.name}")

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg compression failed for {input_file.name}: {e}")
        except Exception as e:
            logger.error(f"Audio compression error for {input_file.name}: {e}")

    async def _synthesize_speech_with_retry(
        self,
        text: str,
        output_file: Path,
    ) -> bool:
        """
        Synthesize speech with retry logic using Edge-TTS.

        Args:
            text: Text to synthesize
            output_file: Output MP3 file path

        Returns:
            True if successful, False otherwise
        """
        async with self.semaphore:
            base_delay = 1.0

            for attempt in range(self.max_retries):
                try:
                    # Create communicate object
                    communicate = edge_tts.Communicate(
                        text=text,
                        voice=self.voice_name,
                        rate=self.rate,
                        pitch=self.pitch
                    )

                    # Ensure output directory exists
                    output_file.parent.mkdir(parents=True, exist_ok=True)

                    # Save to file
                    await communicate.save(str(output_file))

                    # Compress audio
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._compress_audio, output_file)

                    logger.info(f"✓ Generated: {output_file.name}")
                    return True

                except Exception as e:
                    if attempt < self.max_retries - 1:
                        delay = (base_delay * 2**attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Edge-TTS error, retrying in {delay:.2f}s "
                            f"({attempt + 1}/{self.max_retries}): {output_file.name} - {e}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Edge-TTS failed after {self.max_retries} retries: "
                            f"{output_file.name} - {e}"
                        )
                        return False

            return False

    async def generate_for_question(
        self,
        question: Question,
        output_file: Path,
        skip_existing: bool = True,
    ) -> bool:
        """
        Generate audio for a single question.

        Args:
            question: Question object
            output_file: Output MP3 file path
            skip_existing: Skip if file already exists (default: True)

        Returns:
            True if successful, False otherwise
        """
        # Check if file exists
        if skip_existing and output_file.exists() and output_file.stat().st_size > 0:
            logger.info(f"File exists (skipped): {output_file.name}")
            return True

        # Build audio text
        audio_text = self._build_audio_text(question)

        # Skip if no meaningful text
        if audio_text.strip() == f"{question.question_number}번.":
            logger.warning(f"No audio text for question {question.question_id}")
            return False

        # Synthesize speech
        return await self._synthesize_speech_with_retry(audio_text, output_file)

    async def generate_for_database(
        self,
        db_path: Path,
        output_dir: Path,
        category_index: int,
        skip_existing: bool = True,
    ) -> dict:
        """
        Generate audio for all questions in database.

        Args:
            db_path: Path to database file
            output_dir: Base output directory
            category_index: Category index (e.g., 1 for question1)
            skip_existing: Skip existing files (default: True)

        Returns:
            Statistics dictionary
        """
        logger.info(f"Generating audio for: {db_path.name}")

        # Create output directory
        question_dir = output_dir / f"question{category_index}"
        question_dir.mkdir(parents=True, exist_ok=True)

        # Get all questions
        db = QuestionDatabase(db_path)
        questions = db.get_all_questions()

        if not questions:
            logger.warning(f"No questions found in {db_path.name}")
            db.close()
            return {"total": 0, "success": 0, "failed": 0}

        logger.info(f"Found {len(questions)} questions in {db_path.name}")

        # Generate audio tasks
        tasks = []
        for question in questions:
            output_file = question_dir / f"question_{question.question_id}.mp3"
            tasks.append(
                self.generate_for_question(question, output_file, skip_existing)
            )

        # Execute tasks
        logger.info(f"Starting {len(tasks)} TTS tasks (max {self.max_concurrent} concurrent)")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count results
        success_count = sum(1 for r in results if r is True)
        failed_count = len(results) - success_count

        # Update database with audio paths
        updated_count = 0
        for question in questions:
            audio_file = question_dir / f"question_{question.question_id}.mp3"
            if audio_file.exists() and audio_file.stat().st_size > 0:
                relative_path = f"assets/audio/question{category_index}/question_{question.question_id}.mp3"
                try:
                    db.update_audio_path(question.question_id, relative_path)
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Failed to update audio path for question {question.question_id}: {e}")

        db.close()

        logger.info(
            f"✓ Completed: {success_count}/{len(questions)} generated, "
            f"{updated_count} database paths updated"
        )

        return {
            "total": len(questions),
            "success": success_count,
            "failed": failed_count,
            "db_updated": updated_count,
        }


async def generate_question_audio(
    db_path: Path,
    output_dir: Path,
    category_index: int,
    skip_existing: bool = True,
) -> dict:
    """
    Convenience function to generate question audio.

    Args:
        db_path: Path to database file
        output_dir: Base output directory (will create questionN subdirectory)
        category_index: Category index (e.g., 1 for question1)
        skip_existing: Skip existing files (default: True)

    Returns:
        Statistics dictionary
    """
    generator = QuestionTTSGenerator()

    try:
        stats = await generator.generate_for_database(
            db_path,
            output_dir,
            category_index,
            skip_existing
        )
        return stats
    except Exception as e:
        logger.error(f"Audio generation failed: {e}")
        return {"total": 0, "success": 0, "failed": 0, "db_updated": 0}
