"""AI processing module for generating explanations and educational content."""

from .explanation_generator import ExplanationGenerator, generate_explanations
from .ocr_service import OCRService
from .ox_quiz_generator import OXQuizGenerator, generate_ox_quizzes

__all__ = [
    "ExplanationGenerator",
    "generate_explanations",
    "OCRService",
    "OXQuizGenerator",
    "generate_ox_quizzes",
]
