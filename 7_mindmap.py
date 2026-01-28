# 7_mindmap.py

import os
import sys
import json
import logging
import re
from pathlib import Path
from openai import OpenAI
import time
from typing import Optional, List, Dict, Any

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)


class Config:
    """설정 파일을 관리하는 클래스"""
    def __init__(self, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"FATAL: 설정 파일 읽기 오류 '{config_path}': {e}")
            sys.exit(1)
        
        self.api_key = config_data.get("OPENAI_API_KEY")
        self.model_name = config_data.get("MODEL_NAME", "gpt-4o")
        
        if not self.api_key:
            logger.error("FATAL: config.json 파일에 OPENAI_API_KEY가 없습니다.")
            sys.exit(1)
        logger.info(f"설정 로드 완료: {config_path}")


class MindmapGenerator:
    """폴더 내 모든 카테고리의 텍스트를 종합하여 마인드맵 JSON을 생성하는 클래스"""

    def __init__(self, config: Config, selected_folder: str):
        self.client = OpenAI(api_key=config.api_key)
        self.model = config.model_name
        self.base_path = Path(selected_folder)
        self.source_path = self.base_path / "assets" / "output"
        self.final_json_path = self.base_path / "assets" / "mindmap.json"

    def _parse_json_response(self, response_text: str) -> Optional[Any]:
        """GPT 응답 텍스트에서 JSON을 파싱합니다. (오류 로깅 강화)"""
        logger.info("API 응답 파싱 시도...")
        logger.debug(f"--- API 원본 응답 ---\n{response_text}\n--------------------")
        
        try:
            match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text, re.DOTALL)
            if match:
                json_text = match.group(1).strip()
                logger.info("JSON 코드 블록을 감지하여 파싱합니다.")
            else:
                json_text = response_text
                logger.info("JSON 코드 블록을 찾지 못해 전체 응답 텍스트를 파싱 시도합니다.")
            
            parsed_data = json.loads(json_text)
            logger.info("JSON 파싱 성공.")
            return parsed_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 중 오류가 발생했습니다: {e}")
            logger.error(f"--- 파싱 실패한 텍스트 (앞 500자) ---\n{response_text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"JSON 응답 파싱 중 예상치 못한 예외 발생: {e}")
            return None

    def run_generation(self) -> bool:
        """전체 마인드맵 생성 프로세스를 실행합니다."""
        logger.info("마인드맵 생성을 시작합니다...")

        all_category_content = ""
        category_names = []
        if not self.source_path.exists() or not self.source_path.is_dir():
            logger.error(f"오류: 소스 폴더 '{self.source_path}'를 찾을 수 없습니다.")
            return False

        for category_path in sorted(self.source_path.iterdir()):
            if category_path.is_dir():
                source_file = category_path / "1.txt"
                if source_file.exists():
                    category_name = category_path.name
                    category_names.append(category_name)
                    logger.info(f"'{category_name}'의 1.txt 파일 로드 중...")
                    with open(source_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    all_category_content += f"\n\n### 카테고리: {category_name} ###\n\n{content}"
        
        if not all_category_content:
            logger.error("마인드맵을 생성할 텍스트 데이터를 찾지 못했습니다.")
            return False
        
        logger.info(f"총 {len(all_category_content)}자 분량의 텍스트를 API에 전송합니다.")

        folder_name = self.base_path.name
        
        system_message = f"""
당신은 주어진 텍스트의 핵심 내용을 분석하여 구조화된 마인드맵을 생성하는 전문가입니다.
최종 결과는 반드시 요청된 JSON 리스트 형식이어야 합니다. 다른 부가 설명은 절대 포함하지 마세요.
"""
        user_prompt = f"""
'{folder_name}' 전체에 대한 마인드맵을 생성하려고 합니다.
각 카테고리 이름({', '.join(category_names)})을 가장 첫 트리 레벨로 하고 각 주요 내용을 트리로 구성합니다.
단, 마인드맵의 형태는 JSON 리스트 파일 형태로 해주세요.
아래 예시 JSON 파일처럼 작성해주세요.
'title'은 명사(단어) 형태여야 합니다. 문장이나 설명 형태가 아닙니다.
총 4레벨까지 오도록 만들어주세요.

[
    {{
        "root": {{
            "title": "{folder_name}",
            "children": [
                {{
                    "title": "카테고리1 이름",
                    "children": [
                        {{
                            "title": "주요 개념 A",
                            "children": [
                                {{
                                    "title": "세부 항목 1"
                                }}
                            ]
                        }}
                    ]
                }},
                {{
                    "title": "카테고리2 이름"
                }}
            ]
        }}
    }}
]

--- 참고 텍스트 ---
{all_category_content}
"""

        try:
            logger.info(f"'{folder_name}' 전체에 대한 API 요청 전송... (모델: {self.model})")
            
            # ▼▼▼ 수정된 부분 ▼▼▼
            # 최대 출력 길이를 8192 토큰으로 늘려서 공간 부족 문제를 해결합니다.
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ],
                max_completion_tokens=8192
            )
            # ▲▲▲ 수정된 부분 ▲▲▲
            
            logger.info("API 응답 수신. 응답 객체 확인 중...")
            if not response.choices:
                logger.error("❌ API 응답에 'choices' 배열이 비어 있습니다. 처리를 중단합니다.")
                return False

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            logger.info(f"API 응답의 생성 중단 사유(finish_reason): {finish_reason}")

            if finish_reason == 'content_filter':
                logger.error("❌ API가 '콘텐츠 필터'에 의해 응답 생성을 중단했습니다.")
                logger.error("   입력된 텍스트('1.txt')에 OpenAI의 정책을 위반하는 내용이 포함되었을 수 있습니다.")
                return False
            
            if finish_reason == 'length':
                logger.error("❌ API가 최대 허용 길이에 도달하여 응답 생성을 중단했습니다.")
                logger.error("   max_completion_tokens 값을 더 늘려야 할 수 있습니다.")
                return False

            response_text = choice.message.content
            
            if not response_text or not response_text.strip():
                logger.error("❌ API가 비어있는 응답(empty content)을 반환했습니다. (finish_reason: %s)", finish_reason)
                return False

            mindmap_data = self._parse_json_response(response_text)
            
            if mindmap_data and isinstance(mindmap_data, list) and len(mindmap_data) > 0:
                logger.info(f"유효한 마인드맵 데이터 수신 (총 {len(mindmap_data)}개 루트 항목). 파일 저장을 시도합니다...")
                self.final_json_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.final_json_path, 'w', encoding='utf-8') as f:
                    json.dump(mindmap_data, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ 마인드맵이 성공적으로 저장되었습니다: {self.final_json_path}")
                return True
            else:
                if mindmap_data is None:
                    logger.error("❌ 마인드맵 생성 실패: API 응답을 JSON으로 파싱하지 못했습니다.")
                elif not isinstance(mindmap_data, list):
                    logger.error(f"❌ 마인드맵 생성 실패: 예상과 다른 데이터 타입이 수신되었습니다 (타입: {type(mindmap_data)}). 리스트가 필요합니다.")
                elif len(mindmap_data) == 0:
                    logger.error("❌ 마인드맵 생성 실패: API가 비어있는 리스트 '[]'를 반환했습니다.")
                else:
                    logger.error("❌ 마인드맵 생성 실패: 알 수 없는 이유로 데이터가 유효하지 않습니다.")
                return False

        except Exception as e:
            logger.error(f"마인드맵 생성 중 API 오류 발생: {e}", exc_info=True)
            return False

def main():
    if len(sys.argv) < 2:
        print("사용법: python 7_mindmap.py <path_to_data_folder>")
        sys.exit(1)
    
    selected_folder = sys.argv[1]
    
    script_directory = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_directory, "config.json")
    
    if not os.path.exists(config_path):
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        sys.exit(1)

    config = Config(config_path)
    generator = MindmapGenerator(config, selected_folder)
    
    success = generator.run_generation()
    if not success:
        logger.error("마인드맵 생성 과정에서 오류가 발생했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()