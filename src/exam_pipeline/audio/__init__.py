"""Audio generation and processing module."""

from .question_tts import QuestionTTSGenerator, generate_question_audio
from .lecture_importer import LectureImporter, import_lecture_audio
from .folder_watcher import FolderWatcher, watch_downloads

__all__ = [
    "QuestionTTSGenerator",
    "generate_question_audio",
    "LectureImporter",
    "import_lecture_audio",
    "FolderWatcher",
    "watch_downloads",
]
