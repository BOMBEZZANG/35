"""
AI explanation generator using GPT-5.2 Responses API.

Generates Korean explanations for exam questions with async processing,
retry logic, and OCR support for image-based questions.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import List, Optional

from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..core.database import QuestionDatabase
from ..core.models import Question
from .ocr_service import OCRService

logger = logging.getLogger(__name__)


class ExplanationGenerator:
    """
    Generates Korean explanations for exam questions using GPT-5.2.

    Features:
    - Async processing with semaphore (max 5 concurrent requests)
    - Retry logic with exponential backoff
    - OCR support for image-based questions
    - Chunk-based batch processing (10 questions per chunk)
    """

    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-5.2",
        chunk_size: int = 10,
        max_concurrent: int = 5,
        max_retries: int = 3,
        reasoning_effort: str = "medium",
        verbosity: str = "medium",
    ):
        """
        Initialize explanation generator.

        Args:
            openai_api_key: OpenAI API key
            model: Model name (default: gpt-5.2)
            chunk_size: Questions per batch (default: 10)
            max_concurrent: Max concurrent API requests (default: 5)
            max_retries: Max retry attempts (default: 3)
            reasoning_effort: Reasoning level (none/low/medium/high/xhigh, default: medium)
            verbosity: Output verbosity (low/medium/high, default: medium)
        """
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        self.chunk_size = chunk_size
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity

        # Semaphore to limit concurrent requests
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # OCR service for image-based questions
        self.ocr_service = OCRService()

        logger.info(f"ExplanationGenerator initialized: model={model}, effort={reasoning_effort}")

    def _build_prompt(self, question: Question, ocr_text: str = "") -> str:
        """
        Build prompt for GPT-5.2 to generate Korean explanation.

        Args:
            question: Question object
            ocr_text: OCR extracted text from images

        Returns:
            Formatted prompt string
        """
        # Build question text
        question_text = question.big_question

        # Add OCR text if available
        if ocr_text:
            question_text += f"\n\n[이미지 텍스트]\n{ocr_text}"

        # Build options text
        options_text = []
        for i, option in enumerate(question.options):
            marker = "①②③④⑤"[i]
            if isinstance(option, bytes):
                options_text.append(f"{marker} [이미지]")
            else:
                options_text.append(f"{marker} {option}")

        options_str = "\n".join(options_text)

        # Correct answer marker
        correct_marker = "①②③④⑤"[question.correct_option - 1]

        prompt = f"""다음 문제의 정답에 대해 한국어로 명확하고 교육적인 해설을 작성해주세요.

문제: {question_text}

선택지:
{options_str}

정답: {correct_marker}

해설 작성 가이드라인:
1. 정답이 왜 옳은지 명확하게 설명하세요
2. 핵심 개념을 간단히 설명하세요
3. 오답이 왜 틀렸는지 간략히 언급하세요 (선택사항)
4. 학습자가 이해하기 쉽도록 친절하게 작성하세요
5. 2-3문장으로 간결하게 작성하세요

해설:"""

        return prompt

    async def _extract_ocr_text(self, question: Question) -> str:
        """
        Extract OCR text from question images.

        Args:
            question: Question object

        Returns:
            Combined OCR text from all images
        """
        ocr_texts = []

        # Extract from question image
        if question.question_image:
            text = await self.ocr_service.extract_text_from_blob(
                question.question_image,
                context=f"Question #{question.question_number}"
            )
            if text:
                ocr_texts.append(f"[문제 이미지]: {text}")

        # Extract from Big_Question_Special image
        if question.big_question_special_image:
            text = await self.ocr_service.extract_text_from_blob(
                question.big_question_special_image,
                context=f"Question #{question.question_number} (Special)"
            )
            if text:
                ocr_texts.append(f"[특수 이미지]: {text}")

        # Extract from option images
        for i, option in enumerate(question.options):
            if isinstance(option, bytes):
                text = await self.ocr_service.extract_text_from_blob(
                    option,
                    context=f"Question #{question.question_number} Option {i+1}"
                )
                if text:
                    ocr_texts.append(f"[선택지 {i+1}]: {text}")

        return "\n".join(ocr_texts)

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _generate_explanation_with_retry(self, prompt: str, question_id: int) -> str:
        """
        Generate explanation with retry logic using GPT-5.2 Responses API.

        Args:
            prompt: Question prompt
            question_id: Question ID for logging

        Returns:
            Generated explanation text
        """
        async with self.semaphore:
            try:
                logger.debug(f"Generating explanation for Question {question_id}")

                response = await self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    reasoning={"effort": self.reasoning_effort},
                    text={"verbosity": self.verbosity},
                    max_output_tokens=2000,
                )

                # Extract text from response
                # response.output is a list of output objects
                # Each output object has a 'content' field which is a list of content blocks
                output_content = response.output[0].content

                # If content is a list, join all text parts
                if isinstance(output_content, list):
                    explanation = " ".join(
                        block.text if hasattr(block, 'text') else str(block)
                        for block in output_content
                    ).strip()
                else:
                    explanation = str(output_content).strip()

                # Remove code fences if present
                explanation = re.sub(r"```[a-zA-Z]*|```", "", explanation).strip()

                logger.debug(f"Question {question_id}: Generated {len(explanation)} chars")
                return explanation

            except Exception as e:
                logger.error(f"Question {question_id}: API error - {e}")
                raise

    async def generate_explanation(self, question: Question) -> str:
        """
        Generate explanation for a single question.

        Args:
            question: Question object

        Returns:
            Generated explanation or error message
        """
        try:
            # Extract OCR text if question has images
            ocr_text = ""
            if question.has_images:
                ocr_text = await self._extract_ocr_text(question)

            # Build prompt
            prompt = self._build_prompt(question, ocr_text)

            # Generate explanation with retry
            explanation = await self._generate_explanation_with_retry(
                prompt,
                question.question_id
            )

            return explanation

        except Exception as e:
            error_msg = f"Failed to generate explanation: {str(e)}"
            logger.error(f"Question {question.question_id}: {error_msg}")
            return error_msg

    async def process_chunk(
        self,
        questions: List[Question],
        db_path: Path,
    ) -> int:
        """
        Process a chunk of questions asynchronously.

        Args:
            questions: List of questions to process
            db_path: Database path for saving results

        Returns:
            Number of questions successfully processed
        """
        tasks = [self.generate_explanation(q) for q in questions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Save results to database
        db = QuestionDatabase(db_path)
        success_count = 0

        for question, result in zip(questions, results):
            if isinstance(result, Exception):
                logger.error(f"Question {question.question_id} failed: {result}")
                continue

            try:
                db.update_answer_description(question.question_id, result)
                success_count += 1
                logger.info(f"✓ Question {question.question_id}: Explanation saved")
            except Exception as e:
                logger.error(f"Question {question.question_id}: Database save failed - {e}")

        db.close()
        return success_count

    async def process_database(self, db_path: Path) -> dict:
        """
        Process all questions without explanations in database.

        Args:
            db_path: Path to database file

        Returns:
            Statistics dictionary
        """
        logger.info(f"Processing database: {db_path}")

        # Get questions without explanations
        db = QuestionDatabase(db_path)
        questions = db.get_questions_without_explanations()
        db.close()

        if not questions:
            logger.info("No questions need explanations")
            return {"total": 0, "processed": 0, "failed": 0}

        logger.info(f"Found {len(questions)} questions without explanations")

        # Split into chunks
        chunks = [
            questions[i:i + self.chunk_size]
            for i in range(0, len(questions), self.chunk_size)
        ]

        logger.info(f"Processing {len(chunks)} chunks of {self.chunk_size} questions")

        # Process chunks sequentially (to respect rate limits)
        total_processed = 0
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)} ({len(chunk)} questions)")
            processed = await self.process_chunk(chunk, db_path)
            total_processed += processed

            # Brief pause between chunks
            if i < len(chunks):
                await asyncio.sleep(1)

        stats = {
            "total": len(questions),
            "processed": total_processed,
            "failed": len(questions) - total_processed,
        }

        logger.info(f"Completed: {total_processed}/{len(questions)} explanations generated")
        return stats

    def close(self):
        """Close services."""
        self.ocr_service.close()


async def generate_explanations(
    db_path: Path,
    openai_api_key: str,
    model: str = "gpt-5.2",
    reasoning_effort: str = "medium",
    verbosity: str = "medium",
) -> dict:
    """
    Convenience function to generate explanations for database.

    Args:
        db_path: Path to database file
        openai_api_key: OpenAI API key
        model: Model name (default: gpt-5.2)
        reasoning_effort: Reasoning level (default: medium)
        verbosity: Output verbosity (default: medium)

    Returns:
        Statistics dictionary
    """
    generator = ExplanationGenerator(
        openai_api_key=openai_api_key,
        model=model,
        reasoning_effort=reasoning_effort,
        verbosity=verbosity,
    )

    try:
        stats = await generator.process_database(db_path)
        return stats
    finally:
        generator.close()
