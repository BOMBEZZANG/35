"""
PDF parser with 6-stage image assignment algorithm.

Preserves the exact parsing logic from the original implementation,
extended to support both 4-option and 5-option exam formats.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from ..core.database import QuestionDatabase
from ..core.models import Question

logger = logging.getLogger(__name__)


class QuestionMarker:
    """Stores information about question start point."""

    def __init__(self, page_num: int, question_num: int, bbox: fitz.Rect, block_index: int):
        self.page_num = page_num
        self.question_num = question_num
        self.bbox = bbox
        self.block_index = block_index


class QuestionRange:
    """Stores information about question boundaries."""

    def __init__(self, start_marker: QuestionMarker, end_marker: Optional[QuestionMarker] = None):
        self.start_marker = start_marker
        self.end_marker = end_marker
        self.start_page = start_marker.page_num
        self.end_page = end_marker.page_num if end_marker else start_marker.page_num


class PDFParser:
    """
    Parses Korean exam PDFs with 6-stage image assignment algorithm.

    Supports both 4-option and 5-option exam formats.
    """

    def __init__(self, option_count: int = 4):
        """
        Initialize PDF parser.

        Args:
            option_count: Number of options per question (4 or 5)
        """
        if option_count not in (4, 5):
            raise ValueError("option_count must be 4 or 5")

        self.option_count = option_count

        # Define patterns based on option count
        if option_count == 4:
            self.option_splitter_pattern = re.compile(r'([①②③④❶❷❸❹])')
            self.option_map = {'①': 0, '②': 1, '③': 2, '④': 3, '❶': 0, '❷': 1, '❸': 2, '❹': 3}
            self.correct_option_markers = "❶❷❸❹"
        else:  # 5 options
            self.option_splitter_pattern = re.compile(r'([①②③④⑤❶❷❸❹❺])')
            self.option_map = {'①': 0, '②': 1, '③': 2, '④': 3, '⑤': 4, '❶': 0, '❷': 1, '❸': 2, '❹': 3, '❺': 4}
            self.correct_option_markers = "❶❷❸❹❺"

        self.question_start_pattern = re.compile(r"^\s*([1-9]\d*)\.(?!\d)\s*(.*)")

    def map_all_question_starts(self, doc: fitz.Document) -> List[QuestionMarker]:
        """Map all question start points in the document."""
        question_markers = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]

            for block_index, block in enumerate(blocks):
                if not block.get('lines') or not block['lines'][0].get('spans'):
                    continue

                first_line_spans = block['lines'][0]['spans']
                if not first_line_spans:
                    continue

                first_line_text = "".join(span['text'] for span in first_line_spans).strip()

                if re.match(r'^\s*\d+과목\s*:', first_line_text):
                    continue

                q_match = self.question_start_pattern.match(first_line_text)

                if q_match:
                    question_num = int(q_match.group(1))
                    bbox = fitz.Rect(block['bbox'])
                    marker = QuestionMarker(page_num, question_num, bbox, block_index)
                    question_markers.append(marker)

        question_markers.sort(key=lambda x: x.question_num)
        return question_markers

    def determine_question_ranges(self, question_markers: List[QuestionMarker], doc: fitz.Document) -> List[QuestionRange]:
        """Determine the range of each question considering page boundaries."""
        question_ranges = []

        for i, current_marker in enumerate(question_markers):
            next_marker = question_markers[i + 1] if i + 1 < len(question_markers) else None
            question_range = QuestionRange(current_marker, next_marker)
            if next_marker is None:
                # For last question, extend range to end of document
                question_range.end_page = len(doc) - 1

            question_ranges.append(question_range)

        return question_ranges

    def get_blocks_in_range(self, doc: fitz.Document, question_range: QuestionRange) -> List[dict]:
        """Collect all blocks within a specific question range."""
        blocks_in_range = []

        for page_num in range(question_range.start_page, question_range.end_page + 1):
            page = doc.load_page(page_num)
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]

            for block_index, block in enumerate(blocks):
                if not block.get('lines'):
                    continue

                if page_num == question_range.start_page:
                    if block_index < question_range.start_marker.block_index:
                        continue

                if (question_range.end_marker and
                        page_num == question_range.end_page and
                        block_index >= question_range.end_marker.block_index):
                    break

                block_with_page = block.copy()
                block_with_page['page_num'] = page_num
                blocks_in_range.append(block_with_page)

        return blocks_in_range

    def get_all_images(self, doc: fitz.Document) -> List[dict]:
        """Collect all images from the document with central management."""
        all_images = []
        image_id_counter = 0

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_images = page.get_images(full=True)

            for img_index, img in enumerate(page_images):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_bbox = page.get_image_bbox(img)

                    image_data = {
                        'id': image_id_counter,
                        'page_num': page_num,
                        'bbox': image_bbox,
                        'data': image_bytes,
                        'assigned': False
                    }
                    all_images.append(image_data)
                    image_id_counter += 1
                except Exception as e:
                    logger.debug(f"Failed to extract image {xref} on page {page_num}: {e}")

        return all_images

    def clean_text(self, text: str, category_to_remove: Optional[str] = None) -> str:
        """Remove watermarks and unwanted text."""
        cleaned = re.sub(r'◐.*?◑', '', text)
        cleaned = cleaned.replace('최강 자격증 기출문제 전자문제집 CBT : www.comcbt.com', '')
        cleaned = cleaned.replace('전자문제집 CBT : www.comcbt.com', '')
        if category_to_remove:
            cleaned = cleaned.replace(category_to_remove, '')
        return cleaned.strip()

    def build_formatted_text(self, spans: List[Dict]) -> str:
        """Build formatted text with superscript/subscript tags."""
        line_builder = []
        for s in spans:
            text = s['text']
            if s['flags'] & 1:
                line_builder.append(f"<sup>{text}</sup>")
            elif s['flags'] & 2:
                line_builder.append(f"<sub>{text}</sub>")
            else:
                line_builder.append(text)
        return "".join(line_builder)

    def find_best_image(self, image_list: List[Dict], marker_bbox: fitz.Rect, doc: fitz.Document) -> Optional[Dict]:
        """Find the best matching image for an option marker (Stage 1)."""
        candidate_image, min_dist = None, float('inf')
        TOLERANCE_Y = 5

        for img in image_list:
            if img['assigned']:
                continue

            has_overlap = max(marker_bbox.y0, img['bbox'].y0) < min(marker_bbox.y1, img['bbox'].y1)
            gap_y = img['bbox'].y0 - marker_bbox.y1
            is_within_tolerance = (gap_y > 0 and gap_y <= TOLERANCE_Y)
            is_vertically_aligned = has_overlap or is_within_tolerance
            is_right_of_marker = img['bbox'].x1 > marker_bbox.x1

            page = doc.load_page(img['page_num'])
            img_column_midpoint = page.rect.width / 2

            marker_is_left = marker_bbox.x1 < img_column_midpoint
            image_is_left = img['bbox'].x1 < img_column_midpoint
            in_same_column = (marker_is_left == image_is_left)

            if is_vertically_aligned and is_right_of_marker and in_same_column:
                dist = img['bbox'].x0 - marker_bbox.x1
                if dist < min_dist:
                    min_dist, candidate_image = dist, img

        return candidate_image

    def process_question_range(self, doc: fitz.Document, question_range: QuestionRange,
                               category_to_remove: Optional[str], all_images: List[Dict]) -> dict:
        """
        Process a specific question range (Stage 1 image assignment).

        This is the core parsing logic that extracts question text, options,
        and performs the first stage of image assignment.
        """
        blocks_in_range = self.get_blocks_in_range(doc, question_range)
        images_in_range = [
            img for img in all_images
            if question_range.start_page <= img['page_num'] <= question_range.end_page
        ]

        q_data = {
            "Big_Question": "",
            "Big_Question_Special": None,
            "Question": None,
            "Options": [""] * self.option_count,
            "Correct_option_index": None,
            "question_bbox": None,
            "options_bboxes": [None] * self.option_count,
            "option_marker_bboxes": [None] * self.option_count,
            "question_number_marker_bbox": None,
            "page_num": question_range.start_page
        }

        if not blocks_in_range:
            return {}

        is_last_question = question_range.end_marker is None

        # Calculate page column midpoint
        page = doc.load_page(question_range.start_page)
        column_midpoint = page.rect.width / 2

        first_block = blocks_in_range[0]
        first_line_spans = first_block['lines'][0]['spans'] if first_block.get('lines') else []
        first_line_formatted_text = self.build_formatted_text(first_line_spans)
        q_match = self.question_start_pattern.match(first_line_formatted_text.strip())

        if not q_match:
            first_line_plain_text = "".join(s['text'] for s in first_line_spans).strip()
            q_match = self.question_start_pattern.match(first_line_plain_text)
            if not q_match:
                return {}

        q_num_str = q_match.group(1)
        q_data["question_number"] = q_num_str

        first_line = first_block['lines'][0]
        q_num_marker_bbox = next((fitz.Rect(span['bbox']) for span in first_line['spans'] if q_num_str in span['text']), None)
        q_data["question_number_marker_bbox"] = q_num_marker_bbox

        full_question_text = self.clean_text(q_match.group(2), category_to_remove)
        question_only_bbox = fitz.Rect(first_block['bbox'])
        is_option_part = False
        last_option_index = None
        stop_parsing = False
        last_option_marker_bbox = None

        for block in blocks_in_range:
            # Update column_midpoint when page changes
            if 'page_num' in block and block.get('page_num') != page.number:
                page = doc.load_page(block['page_num'])
                column_midpoint = page.rect.width / 2

            for line in block.get('lines', []):
                line_text_plain = "".join([s['text'] for s in line.get('spans', [])]).strip()

                if is_last_question and is_option_part and ("전자문제집 CBT" in line_text_plain or "www.comcbt.com" in line_text_plain):
                    stop_parsing = True
                    break

                line_text_formatted = self.build_formatted_text(line.get('spans', []))
                if re.match(r'^\s*\d+과목\s*:', line_text_plain):
                    continue
                cleaned_line_text = self.clean_text(line_text_formatted, category_to_remove).strip()
                if not cleaned_line_text:
                    continue

                split_parts = self.option_splitter_pattern.split(cleaned_line_text)

                if len(split_parts) > 1:
                    is_option_part = True
                    for i in range(1, len(split_parts), 2):
                        marker, text = split_parts[i], split_parts[i + 1].strip() if (i + 1) < len(split_parts) else ""
                        if marker in self.option_map:
                            opt_idx = self.option_map[marker]
                            q_data["Options"][opt_idx] += text
                            last_option_index = opt_idx
                            if q_data["options_bboxes"][opt_idx] is None:
                                q_data["options_bboxes"][opt_idx] = fitz.Rect(line['bbox'])
                            else:
                                q_data["options_bboxes"][opt_idx].include_rect(line['bbox'])
                            for span in line.get('spans', []):
                                if marker in span['text']:
                                    current_marker_bbox = fitz.Rect(span['bbox'])
                                    q_data["option_marker_bboxes"][opt_idx] = current_marker_bbox
                                    last_option_marker_bbox = current_marker_bbox
                                    break
                            if marker in self.correct_option_markers:
                                q_data["Correct_option_index"] = opt_idx

                elif is_option_part and last_option_index is not None and last_option_marker_bbox is not None:
                    line_bbox = fitz.Rect(line['bbox'])

                    # Check if current line is in same column as last option marker
                    marker_is_left = last_option_marker_bbox.x1 < column_midpoint
                    line_is_left = line_bbox.x1 < column_midpoint

                    if marker_is_left == line_is_left:
                        q_data["Options"][last_option_index] += " " + cleaned_line_text
                        if q_data["options_bboxes"][last_option_index]:
                            q_data["options_bboxes"][last_option_index].include_rect(line_bbox)

                elif not is_option_part and not line_text_plain.startswith(q_num_str):
                    full_question_text += " " + cleaned_line_text
                    question_only_bbox.include_rect(block['bbox'])

            if stop_parsing:
                break

        q_data["Big_Question"] = " ".join(full_question_text.split())
        q_data["question_bbox"] = question_only_bbox

        # Stage 1: Assign images next to option markers
        for i in range(self.option_count):
            marker_bbox = q_data["option_marker_bboxes"][i]
            if not marker_bbox or (isinstance(q_data["Options"][i], str) and q_data["Options"][i].strip()):
                continue
            if isinstance(q_data["Options"][i], bytes):
                continue

            same_page_images = [img for img in images_in_range if img['page_num'] == q_data['page_num']]
            best_image = self.find_best_image(same_page_images, marker_bbox, doc)

            if best_image:
                best_image['assigned'] = True
                q_data["Options"][i] = best_image['data']
                continue

            other_page_images = [img for img in images_in_range if img['page_num'] != q_data['page_num']]
            best_image = self.find_best_image(other_page_images, marker_bbox, doc)

            if best_image:
                best_image['assigned'] = True
                q_data["Options"][i] = best_image['data']

        # Stage 1: Assign image between question text and first option
        opt1_marker_bbox = q_data["option_marker_bboxes"][0]
        question_bbox = q_data["question_bbox"]
        if opt1_marker_bbox and question_bbox:
            candidate_image, min_dist = None, float('inf')
            images_to_check = sorted(images_in_range, key=lambda img: img['page_num'] != q_data['page_num'])

            for img in images_to_check:
                if img['assigned']:
                    continue
                is_vertically_correct = img['bbox'].y1 <= opt1_marker_bbox.y0 and img['bbox'].y0 >= question_bbox.y1
                is_horizontally_aligned = max(img['bbox'].x0, question_bbox.x0) < min(img['bbox'].x1, question_bbox.x1)
                if is_vertically_correct and is_horizontally_aligned:
                    dist = img['bbox'].y0 - question_bbox.y1
                    if dist < min_dist:
                        min_dist, candidate_image = dist, img
            if candidate_image:
                candidate_image['assigned'] = True
                q_data["Question"] = candidate_image['data']

        return q_data

    def is_ignorable_header_footer_text(self, text: str, exam_name: Optional[str]) -> bool:
        """Check if text is ignorable header/footer."""
        cleaned = text
        cleaned = re.sub(r'◐.*?◑', '', cleaned).strip()
        cleaned = cleaned.replace('최강 자격증 기출문제 전자문제집 CBT : www.comcbt.com', '').strip()
        cleaned = cleaned.replace('전자문제집 CBT : www.comcbt.com', '').strip()
        if exam_name:
            cleaned = cleaned.replace(exam_name, '').strip()
        if re.match(r'^\s*\d+과목\s*:', cleaned):
            cleaned = ""
        return not bool(cleaned)

    def assign_cross_column_images(self, doc: fitz.Document, all_questions: List[Dict],
                                   all_images: List[Dict], exam_name: Optional[str]):
        """Stage 2: Assign images from different columns or next page."""
        unassigned_images = [img for img in all_images if not img['assigned']]
        if not unassigned_images:
            return

        page_width = doc[0].rect.width
        column_midpoint = page_width / 2

        for image in unassigned_images:
            page_num = image['page_num']
            img_bbox = image['bbox']

            is_topmost = True
            page = doc.load_page(page_num)
            blocks = page.get_text("dict")["blocks"]
            for other_img in all_images:
                if other_img['id'] == image['id'] or other_img['page_num'] != page_num:
                    continue
                if (other_img['bbox'].x0 < column_midpoint) == (img_bbox.x0 < column_midpoint) and other_img['bbox'].y1 < img_bbox.y0:
                    is_topmost = False
                    break
            if not is_topmost:
                continue

            for block in blocks:
                block_bbox = fitz.Rect(block['bbox'])
                if (block_bbox.x0 < column_midpoint) == (img_bbox.x0 < column_midpoint) and block_bbox.y1 < img_bbox.y0:
                    block_text = "".join(span['text'] for line in block.get('lines', []) for span in line.get('spans', []))
                    if not self.is_ignorable_header_footer_text(block_text, exam_name):
                        is_topmost = False
                        break
            if not is_topmost:
                continue

            img_col_is_left = img_bbox.x0 < column_midpoint

            if not img_col_is_left:
                target_question, vertical_reference_question = None, None
                same_page_left_q = [q for q in all_questions if q.get('page_num') == page_num and q.get('question_bbox') and q['question_bbox'].x1 < column_midpoint]
                if same_page_left_q:
                    target_question = max(same_page_left_q, key=lambda q: q['question_bbox'].y1)

                same_page_right_q = [q for q in all_questions if q.get('page_num') == page_num and q.get('question_bbox') and q['question_bbox'].x0 > column_midpoint]
                if same_page_right_q:
                    vertical_reference_question = min(same_page_right_q, key=lambda q: q['question_bbox'].y0)

                if not target_question or not vertical_reference_question:
                    continue

                first_opt_marker_bbox = vertical_reference_question.get('option_marker_bboxes', [None] * self.option_count)[0]
                if not first_opt_marker_bbox:
                    continue

                if img_bbox.y1 < first_opt_marker_bbox.y0 and target_question.get('Question') is None:
                    target_question['Question'] = image['data']
                    image['assigned'] = True

            else:
                if page_num == 0:
                    continue

                prev_page_q = [q for q in all_questions if q.get('page_num') == page_num - 1 and q.get('question_number')]
                if not prev_page_q:
                    continue

                potential_target = max(prev_page_q, key=lambda q: int(q['question_number']))
                first_opt_marker_bbox = potential_target.get('option_marker_bboxes', [None] * self.option_count)[0]

                if not first_opt_marker_bbox:
                    continue

                if img_bbox.y1 < first_opt_marker_bbox.y0:
                    if potential_target.get('Question') is None:
                        potential_target['Question'] = image['data']
                        image['assigned'] = True

    def assign_bottom_column_images(self, doc: fitz.Document, all_questions: List[Dict],
                                    all_images: List[Dict], exam_name: Optional[str]):
        """Stage 3: Assign bottommost images in columns."""
        unassigned_images = [img for img in all_images if not img['assigned']]
        if not unassigned_images:
            return

        page_width = doc[0].rect.width
        column_midpoint = page_width / 2
        page_blocks_cache = {p: doc.load_page(p).get_text("dict")["blocks"] for p in set(img['page_num'] for img in unassigned_images)}

        for image in unassigned_images:
            img_bbox, page_num = image['bbox'], image['page_num']
            img_col_is_left = img_bbox.x0 < column_midpoint

            is_bottommost = True
            for other_img in all_images:
                if other_img['id'] == image['id'] or other_img['page_num'] != page_num:
                    continue
                other_img_col_is_left = other_img['bbox'].x0 < column_midpoint
                if other_img_col_is_left == img_col_is_left and other_img['bbox'].y0 > img_bbox.y1:
                    is_bottommost = False
                    break
            if not is_bottommost:
                continue

            for block in page_blocks_cache.get(page_num, []):
                block_bbox = fitz.Rect(block['bbox'])
                block_col_is_left = block_bbox.x0 < column_midpoint
                if block_col_is_left == img_col_is_left and block_bbox.y0 > img_bbox.y1:
                    block_text = "".join(span['text'] for line in block.get('lines', []) for span in line.get('spans', []))
                    if not self.is_ignorable_header_footer_text(block_text, exam_name):
                        is_bottommost = False
                        break
            if not is_bottommost:
                continue

            candidate_questions = []
            for q in all_questions:
                q_bbox = q.get('question_bbox')
                if not q_bbox or q.get('page_num') != page_num:
                    continue
                q_col_is_left = q_bbox.x0 < column_midpoint
                if q_col_is_left == img_col_is_left and q_bbox.y1 < img_bbox.y0:
                    candidate_questions.append(q)
            if not candidate_questions:
                continue

            target_question = max(candidate_questions, key=lambda q: q['question_bbox'].y1)

            if target_question.get('Question') is None:
                target_question['Question'] = image['data']
                image['assigned'] = True

    def assign_images_below_options(self, all_questions: List[Dict], all_images: List[Dict]):
        """Stage 4: Assign images below option markers."""
        unassigned_images = [img for img in all_images if not img['assigned']]
        if not unassigned_images:
            return

        sorted_questions = sorted(all_questions, key=lambda q: int(q.get('question_number', 0)))
        num_questions = len(sorted_questions)

        for i, current_q in enumerate(sorted_questions):
            for opt_idx in range(self.option_count):
                option_marker_bbox = current_q.get('option_marker_bboxes', [None] * self.option_count)[opt_idx]
                if not option_marker_bbox:
                    continue

                option_content = current_q['Options'][opt_idx]
                if isinstance(option_content, bytes) or (isinstance(option_content, str) and option_content.strip()):
                    continue

                bottom_boundary_bbox = None
                if opt_idx < self.option_count - 1:
                    next_marker_bbox = current_q.get('option_marker_bboxes', [None] * self.option_count)[opt_idx + 1]
                    if next_marker_bbox:
                        bottom_boundary_bbox = next_marker_bbox

                if bottom_boundary_bbox is None and i + 1 < num_questions:
                    next_q = sorted_questions[i + 1]
                    bottom_boundary_bbox = next_q.get('question_number_marker_bbox')

                if not bottom_boundary_bbox:
                    continue

                for image in unassigned_images:
                    if image['assigned'] or image['page_num'] != current_q['page_num']:
                        continue

                    img_bbox = image['bbox']
                    is_below_option = img_bbox.y0 > option_marker_bbox.y0
                    is_above_boundary = img_bbox.y1 < bottom_boundary_bbox.y0

                    if is_below_option and is_above_boundary:
                        current_q['Options'][opt_idx] = image['data']
                        image['assigned'] = True
                        break

    def assign_special_question_images(self, all_questions: List[Dict], all_images: List[Dict]):
        """Stage 5: Assign images overlapping question text as Big_Question_Special."""
        unassigned_images = [img for img in all_images if not img['assigned']]
        if not unassigned_images:
            return

        for question in all_questions:
            if question.get('Big_Question_Special') is not None:
                continue

            question_bbox = question.get('question_bbox')
            opt1_marker_bbox = question.get('option_marker_bboxes', [None] * self.option_count)[0]

            if not question_bbox or not opt1_marker_bbox:
                continue

            for image in unassigned_images:
                if image['assigned']:
                    continue

                if image['page_num'] != question['page_num']:
                    continue

                img_bbox = image['bbox']

                is_overlapping = img_bbox.intersects(question_bbox)
                is_above_option1 = img_bbox.y1 < opt1_marker_bbox.y0

                if is_overlapping and is_above_option1:
                    question['Big_Question_Special'] = image['data']
                    image['assigned'] = True
                    break

    def assign_bottom_of_page_special_images(self, doc: fitz.Document, all_questions: List[Dict], all_images: List[Dict]):
        """Stage 6: Assign images at page bottom as Big_Question_Special."""
        unassigned_images = [img for img in all_images if not img['assigned']]
        if not unassigned_images:
            return

        page_heights = {i: doc[i].rect.height for i in range(len(doc))}

        for image in unassigned_images:
            if image['assigned']:
                continue

            for question in all_questions:
                if question.get('Big_Question_Special') is not None:
                    continue
                if image['page_num'] != question.get('page_num'):
                    continue

                question_bbox = question.get('question_bbox')
                if not question_bbox:
                    continue

                is_overlapping = image['bbox'].intersects(question_bbox)

                page_height = page_heights.get(question['page_num'])
                if not page_height:
                    continue

                is_at_bottom = question_bbox.y1 > (page_height * 0.70)

                if is_overlapping and is_at_bottom:
                    question['Big_Question_Special'] = image['data']
                    image['assigned'] = True
                    break

    def parse_pdf(self, pdf_path: Path, exam_name: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Parse PDF and extract questions with 6-stage image assignment.

        Args:
            pdf_path: Path to PDF file
            exam_name: Exam name for watermark removal

        Returns:
            Tuple of (questions_list, all_images_list)
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF: {e}")

        logger.info(f"Parsing PDF: {pdf_path.name}")

        # Collect all images
        all_images = self.get_all_images(doc)
        logger.info(f"Found {len(all_images)} images")

        # Map question markers
        question_markers = self.map_all_question_starts(doc)
        if not question_markers:
            logger.warning("No question markers found in PDF")
            doc.close()
            return [], all_images

        logger.info(f"Found {len(question_markers)} questions")

        # Determine question ranges
        question_ranges = self.determine_question_ranges(question_markers, doc)

        # Stage 1: Process each question range
        all_questions = []
        for question_range in question_ranges:
            question_data = self.process_question_range(doc, question_range, exam_name, all_images)
            if question_data.get("question_number"):
                all_questions.append(question_data)

        logger.info(f"Stage 1 complete: Processed {len(all_questions)} questions")

        # Stage 2: Cross-column images
        self.assign_cross_column_images(doc, all_questions, all_images, exam_name)
        logger.info("Stage 2 complete: Cross-column image assignment")

        # Stage 3: Bottom column images
        self.assign_bottom_column_images(doc, all_questions, all_images, exam_name)
        logger.info("Stage 3 complete: Bottom column image assignment")

        # Stage 4: Images below options
        self.assign_images_below_options(all_questions, all_images)
        logger.info("Stage 4 complete: Images below options assignment")

        # Stage 5: Special question images
        self.assign_special_question_images(all_questions, all_images)
        logger.info("Stage 5 complete: Special question images assignment")

        # Stage 6: Bottom of page special images
        self.assign_bottom_of_page_special_images(doc, all_questions, all_images)
        logger.info("Stage 6 complete: Bottom of page special images assignment")

        doc.close()

        # Check for unassigned images
        unassigned = [img for img in all_images if not img['assigned']]
        if unassigned:
            logger.warning(f"{len(unassigned)} images remain unassigned")

        return all_questions, all_images

    def save_to_database(self, questions_data: List[dict], db_path: Path, category: str, exam_session: str):
        """
        Save parsed questions to database.

        Args:
            questions_data: List of question dictionaries
            db_path: Path to database file
            category: Category name
            exam_session: Exam session identifier (format: YYYYMMDD)
        """
        db = QuestionDatabase(db_path)
        db.create_tables()

        for q_data in questions_data:
            if not q_data.get("question_number"):
                continue

            # Prepare options (support both 4 and 5 options)
            options = q_data.get("Options", [])
            option_list = []
            for i in range(self.option_count):
                opt_val = options[i] if i < len(options) else None
                option_list.append(opt_val if opt_val else None)

            # Correct option (1-indexed for database)
            correct_option_num = q_data.get("Correct_option_index")
            if correct_option_num is not None:
                correct_option_num += 1

            # Create Question model (question_id will be set by database)
            question = Question(
                question_id=0,  # Will be set by database auto-increment
                question_number=q_data.get("question_number"),
                big_question=q_data.get("Big_Question") if q_data.get("Big_Question") else "",
                big_question_special_image=q_data.get("Big_Question_Special"),
                question_image=q_data.get("Question"),
                options=option_list,
                correct_option=correct_option_num,
                option_count=self.option_count,
                category=category,
                exam_session=exam_session,
                answer_description=None,
                audio_path=None,
                date_information=self._format_date_info(exam_session)
            )

            db.insert_question(question)

        db.close()
        logger.info(f"Saved {len(questions_data)} questions to database")

    def _format_date_info(self, exam_session: str) -> Optional[str]:
        """Format exam session date (YYYYMMDD) to Korean format (YYYY년 MM월)."""
        try:
            if len(exam_session) == 8 and exam_session.isdigit():
                year = exam_session[:4]
                month = exam_session[4:6]
                return f"{year}년 {month}월"
        except Exception:
            pass
        return None
