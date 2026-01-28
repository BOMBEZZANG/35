# 6_dictionary.py (음성 생성 제거 버전)

import os
import sys
import json
import sqlite3
import re
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# --- 라이브러리 임포트 ---
try:
    from openai import OpenAI
except ImportError as e:
    print(f"오류: 필수 라이브러리가 설치되지 않았습니다. 누락된 라이브러리: {e.name}")
    print("pip install openai")
    sys.exit(1)

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- 설정 관리 클래스 ---
class Config:
    """설정 파일을 관리하는 클래스"""
    def __init__(self, config_path: str):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"FATAL: 설정 파일 읽기 오류 '{config_path}': {e}")
            sys.exit(1)
        
        self.api_key = config_data.get("OPENAI_API_KEY")
        self.model_name = config_data.get("MODEL_NAME", "gpt-4o")
        
        if not self.api_key:
            logger.error("FATAL: config.json 파일에 OPENAI_API_KEY 키가 없습니다.")
            sys.exit(1)
        
        logger.info(f"설정 로드 완료: {config_path}")

# --- 메인 처리 클래스 ---
class DictionaryProcessor:
    """용어사전 생성의 전체 워크플로우를 관리하는 클래스"""

    def __init__(self, base_folder_path: str, config: Config):
        self.base_path = Path(base_folder_path)
        self.config = config
        
        self.output_path = self.base_path / "assets" / "output"
        self.assets_path = self.base_path / "assets"
        
        self.json_path = self.assets_path / "dictionary.json"
        self.db_path = self.assets_path / "dictionary.db"
        self.manifest_path = self.assets_path / "dictionary_manifest.json"

        try:
            self.openai_client = OpenAI(api_key=self.config.api_key)
        except Exception as e:
            logger.error(f"API 클라이언트 초기화 실패: {e}")
            sys.exit(1)

    def run_pipeline(self):
        """3단계 파이프라인을 순차적으로 실행합니다."""
        logger.info("="*20 + " 용어사전 생성 파이프라인 시작 " + "="*20)
        
        if self._step1_generate_json():
            if self._step2_convert_to_db():
                if self._step3_generate_manifest():
                    logger.info("\n✅ 모든 작업이 성공적으로 완료되었습니다!")
                    return True
        
        logger.error("\n❌ 파이프라인 실행 중 오류가 발생하여 중단되었습니다.")
        return False

    # --- 단계 1: JSON 파일 생성 (GPT API) ---
    def _step1_generate_json(self) -> bool:
        logger.info("\n" + "-"*15 + " 단계 1: GPT로 용어사전 JSON 생성 시작 " + "-"*15)
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

        self.assets_path.mkdir(parents=True, exist_ok=True)
        
        if not self.output_path.exists() or not self.output_path.is_dir():
            logger.error(f"오류: 퀴즈 소스 경로를 찾을 수 없습니다. '{self.output_path}' 폴더가 필요합니다.")
            return False

        category_folders = [d for d in self.output_path.iterdir() if d.is_dir()]
        if not category_folders:
            logger.error(f"오류: '{self.output_path}' 폴더에서 처리할 카테고리를 찾지 못했습니다.")
            return False

        all_terms = []
        for category_path in category_folders:
            try:
                category_name = category_path.name
                source_text_path = category_path / "1.txt"
                if not source_text_path.exists():
                    logger.warning(f"경고: '{source_text_path}' 파일이 없어 건너뜁니다.")
                    continue

                with open(source_text_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                system_prompt = "용어해설집을 하나의 컨텐츠로 만들어서 이 용어를 계속 암기할 수 있도록 만드려고 합니다."
                user_prompt = f"""
샘플문제(1.txt)를 참조하여 용어해설집을 생성해 주세요.

용어의 분류 과목으로는 '{category_name}' 입니다.
'{category_name}'에 대한 핵심 용어 100개를 만들어주세요.

{{
"term": "용존 산소 (DO)",
"definition": "물 속에 녹아 있는 산소의 양. 하수에서 DO가 낮을수록 오염도가 높음을 의미합니다.",
"category": "{category_name}"
}}
이와 같은 JSON 배열 형태로만 출력해 주세요. 다른 설명은 절대 추가하지 마세요.
"""
                logger.info(f"'{category_name}' 카테고리에 대한 용어 생성 API 요청 전송...")
                response = self.openai_client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                response_content = response.choices[0].message.content
                
                if response_content is None:
                    logger.error(f"❌ '{category_name}'에 대한 API 응답 내용이 비어있습니다. 건너뜁니다.")
                    continue

                match = re.search(r'\[\s*{.*}\s*\]', response_content, re.DOTALL)
                if match:
                    json_data = json.loads(match.group(0))
                    all_terms.extend(json_data)
                    logger.info(f"✅ '{category_name}' 카테고리에서 {len(json_data)}개의 용어 생성 성공.")
                else:
                    logger.error(f"❌ '{category_name}' 응답에서 유효한 JSON 배열을 찾지 못했습니다.")

            except Exception as e:
                logger.error(f"'{category_path.name}' 처리 중 오류 발생: {e}", exc_info=True)
                return False

        if not all_terms:
            logger.error("생성된 용어가 하나도 없습니다. 프로세스를 중단합니다.")
            return False

        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(all_terms, f, ensure_ascii=False, indent=2)
            
        logger.info(f"총 {len(all_terms)}개의 용어를 '{self.json_path}'에 성공적으로 저장했습니다.")
        return True

    # --- 단계 2: DB 변환 ---
    def _step2_convert_to_db(self) -> bool:
        logger.info("\n" + "-"*15 + " 단계 2: JSON을 SQLite DB로 변환 시작 " + "-"*15)
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DROP TABLE IF EXISTS dictionary")
            cursor.execute('''
                CREATE TABLE dictionary (
                    id INTEGER PRIMARY KEY,
                    term TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    category TEXT
                )
            ''')
            
            current_id = 1
            for item in data:
                cursor.execute(
                    "INSERT INTO dictionary (id, term, definition, category) VALUES (?, ?, ?, ?)",
                    (current_id, item.get('term'), item.get('definition'), item.get('category'))
                )
                current_id += 1
            
            conn.commit()
            logger.info(f"✅ 총 {len(data)}개의 용어를 '{self.db_path}'에 성공적으로 저장했습니다.")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"DB 변환 중 오류 발생: {e}", exc_info=True)
            return False

    # --- 단계 3: 매니페스트 파일 생성 ---
    def _step3_generate_manifest(self) -> bool:
        logger.info("\n" + "-"*15 + " 단계 3: Manifest.json 생성 시작 " + "-"*15)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, term, definition, category FROM dictionary ORDER BY id")
            rows = cursor.fetchall()
            conn.close()

            manifest_data = []
            for row_id, term, definition, category in rows:
                manifest_data.append({
                    "id": row_id,
                    "term": term,
                    "definition": definition,
                    "category": category
                })

            with open(self.manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Manifest 파일을 성공적으로 생성했습니다: {self.manifest_path}")
            return True
        except Exception as e:
            logger.error(f"Manifest 생성 중 오류 발생: {e}", exc_info=True)
            return False

# --- 메인 실행 로직 ---
def main():
    if len(sys.argv) < 2:
        print("사용법: python 6_dictionary.py <path_to_data_folder>")
        sys.exit(1)
        
    data_folder = sys.argv[1]
    if not os.path.isdir(data_folder):
        print(f"오류: '{data_folder}'는 유효한 디렉토리가 아닙니다.")
        sys.exit(1)
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    config = Config(config_path)
    processor = DictionaryProcessor(data_folder, config)
    processor.run_pipeline()

if __name__ == "__main__":
    main()