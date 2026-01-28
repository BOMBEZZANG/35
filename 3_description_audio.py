import asyncio
import aiosqlite
import sqlite3
import os
import glob
import re
import sys
import subprocess
import logging
from datetime import datetime
from google.cloud import texttospeech
import time
import random
from google.api_core import exceptions as google_exceptions

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 유틸리티 함수 ---
def get_db_files_to_process(db_folder: str) -> list:
    """
    [수정됨] 'assets' 폴더 내에서 처리할 DB 파일 목록(question1.db ~ question3.db)을 정렬하고 반환합니다.
    """
    assets_path = os.path.join(db_folder, "assets")

    if not os.path.isdir(assets_path):
        logger.warning(f"'assets' 폴더를 찾을 수 없어 DB 파일을 읽을 수 없습니다: {assets_path}")
        return []
    
    all_dbs = [f for f in os.listdir(assets_path) if f.endswith('.db')]
    
    db_with_metadata = []
    
    for db in all_dbs:
        if match := re.match(r"question(\d+)\.db", db):
            number = int(match.group(1))
            
            if 1 <= number <= 3:
                full_path = os.path.join(assets_path, db)
                db_with_metadata.append({'type': 'question', 'sort_key': number, 'file': full_path})

    db_with_metadata.sort(key=lambda x: (0 if x['type'] == 'question' else 1, x['sort_key']))
    
    return [item['file'] for item in db_with_metadata]

def compress_audio(input_file: str):
    """FFmpeg를 사용해 오디오 파일을 압축합니다. (동기 함수)"""
    if not os.path.exists(input_file): return
    output_file_compressed = input_file.replace(".mp3", "_compressed.mp3")
    try:
        subprocess.run(
            ["ffmpeg", "-i", input_file, "-b:a", "32k", "-ar", "16000", "-y", "-loglevel", "error", output_file_compressed],
            check=True
        )
        os.remove(input_file)
        os.rename(output_file_compressed, input_file)
    except Exception as e:
        logger.error(f"오디오 압축 실패 {input_file}: {e}")

# --- 비동기 TTS 및 DB 처리 ---
async def text_to_speech_async(tts_client: texttospeech.TextToSpeechAsyncClient, text: str, output_file: str, semaphore: asyncio.Semaphore):
    """
    단일 텍스트를 비동기적으로 MP3로 변환 및 압축합니다.
    (503 오류 발생 시 자동 재시도 로직 추가)
    """
    async with semaphore:
        max_retries = 5
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                synthesis_input = texttospeech.SynthesisInput(text=text)
                voice = texttospeech.VoiceSelectionParams(language_code="ko-KR", name="ko-KR-Standard-D")
                audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.9, pitch=-4.0)

                response = await tts_client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
                
                with open(output_file, "wb") as out:
                    out.write(response.audio_content)
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, compress_audio, output_file)
                
                logger.info(f"음성 파일 생성 및 압축 완료: {os.path.basename(output_file)}")
                return

            except google_exceptions.ServiceUnavailable as e:
                if attempt < max_retries - 1:
                    delay = (base_delay * 2**attempt) + random.uniform(0, 1)
                    logger.warning(f"TTS 실패 (503 오류), {delay:.2f}초 후 재시도 ({attempt + 1}/{max_retries}): {os.path.basename(output_file)}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"TTS 변환/압축 최종 실패 (재시도 초과) {os.path.basename(output_file)}: {e}")
                    return
            except Exception as e:
                logger.error(f"TTS 변환/압축 실패 {os.path.basename(output_file)}: {e}")
                return

async def add_audio_column_if_not_exists(conn: aiosqlite.Connection):
    """'audio' 칼럼이 없으면 추가합니다."""
    async with conn.cursor() as cursor:
        await cursor.execute("PRAGMA table_info(questions)")
        columns = [col[1] for col in await cursor.fetchall()]
        if "audio" not in columns:
            await cursor.execute("ALTER TABLE questions ADD COLUMN audio TEXT")
            logger.info("'audio' 칼럼이 추가되었습니다.")
    await conn.commit()

async def update_audio_paths_in_db(conn: aiosqlite.Connection, output_dir: str, question_index: int):
    """생성된 오디오 파일 경로를 DB에 업데이트합니다."""
    logger.info("DB에 오디오 경로 업데이트 시작...")
    updated_count = 0
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT Question_id FROM questions")
        rows = await cursor.fetchall()
        
        for row in rows:
            question_id = row[0]
            audio_file = os.path.join(output_dir, f"question_{question_id}.mp3")
            if os.path.exists(audio_file):
                relative_path = f"assets/audio/question{question_index}/question_{question_id}.mp3"
                await cursor.execute(
                    "UPDATE questions SET audio = ? WHERE Question_id = ?",
                    (relative_path, question_id)
                )
                updated_count += 1
    
    await conn.commit()
    logger.info(f"총 {updated_count}개의 오디오 경로를 DB에 업데이트했습니다.")

async def process_single_db(tts_client: texttospeech.TextToSpeechAsyncClient, db_path: str, index: int, audio_base_dir: str, skip_existing: bool = True):
    """단일 DB 파일에 대해 음성 생성 및 경로 업데이트를 모두 수행합니다."""
    db_name = os.path.basename(db_path)
    logger.info(f"\n--- [{index}] DB 처리 시작: {db_name} ---")

    output_dir_name = f"question{index}"
    output_dir = os.path.join(audio_base_dir, output_dir_name)
    os.makedirs(output_dir, exist_ok=True)
    
    conn = None
    try:
        conn = await aiosqlite.connect(db_path)
        
        await add_audio_column_if_not_exists(conn)
        
        cursor = await conn.execute("SELECT Question_id, Big_Question, Question, Option1, Option2, Option3, Option4, Correct_Option, Answer_description FROM questions")
        rows = await cursor.fetchall()
        await cursor.close()
        
        if not rows:
            logger.warning(f"{db_name}에 처리할 데이터가 없습니다.")
            return

        tasks = []
        semaphore = asyncio.Semaphore(10)

        for row in rows:
            question_id, big_question, question, opt1, opt2, opt3, opt4, correct_opt, answer_desc = row
            
            parts = [f"{question_id}번. "]
            if isinstance(big_question, str): parts.append(f"{big_question}. ")
            if isinstance(question, str): parts.append(f"{question}. ")
            if isinstance(opt1, str): parts.append(f"일. {opt1}. ")
            if isinstance(opt2, str): parts.append(f"이. {opt2}. ")
            if isinstance(opt3, str): parts.append(f"삼. {opt3}. ")
            if isinstance(opt4, str): parts.append(f"사. {opt4}. ")
            if isinstance(correct_opt, int): parts.append(f"정답은 {correct_opt}번 입니다. ")
            if isinstance(answer_desc, str):
                cleaned_desc = re.sub(r"따라서 정답은 [1-4]입니다\.", "", answer_desc).strip()
                if cleaned_desc: parts.append(f"{cleaned_desc}. ")
            
            audio_text = "".join(parts)
            
            if audio_text.strip() != f"{question_id}번.":
                output_file = os.path.join(output_dir, f"question_{question_id}.mp3")
                
                # [수정 1] skip_existing 파라미터로 건너뛰기 여부 제어
                if skip_existing and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    logger.info(f"파일이 이미 존재함 (건너뜀): {os.path.basename(output_file)}")
                    continue
                
                tasks.append(text_to_speech_async(tts_client, audio_text, output_file, semaphore))

        if not tasks:
            logger.warning(f"{db_name}에서 음성으로 변환할 텍스트가 없습니다.")
            return

        logger.info(f"{db_name}: 총 {len(tasks)}개 문제의 음성 파일 동시 생성 시작...")
        await asyncio.gather(*tasks)
        logger.info(f"{db_name}: 모든 음성 파일 생성 완료.")
        
        await update_audio_paths_in_db(conn, output_dir, index)

    except Exception as e:
        logger.error(f"{db_name} 처리 중 오류 발생: {e}", exc_info=True)
    finally:
        if conn:
            await conn.close()
            logger.info(f"DB 연결 종료: {db_name}")

# [추가 3] 누락된 파일 확인 및 재생성 함수
async def check_and_regenerate_missing_files(tts_client: texttospeech.TextToSpeechAsyncClient, db_path: str, index: int, audio_base_dir: str):
    """누락된 음성 파일을 확인하고 재생성합니다."""
    db_name = os.path.basename(db_path)
    logger.info(f"\n--- [{index}] 누락된 파일 확인: {db_name} ---")
    
    output_dir_name = f"question{index}"
    output_dir = os.path.join(audio_base_dir, output_dir_name)
    
    conn = None
    missing_files = []
    
    try:
        conn = await aiosqlite.connect(db_path)
        cursor = await conn.execute("SELECT Question_id FROM questions")
        rows = await cursor.fetchall()
        await cursor.close()
        
        for row in rows:
            question_id = row[0]
            expected_file = os.path.join(output_dir, f"question_{question_id}.mp3")
            if not os.path.exists(expected_file) or os.path.getsize(expected_file) == 0:
                missing_files.append(question_id)
        
        if missing_files:
            logger.warning(f"{db_name}: {len(missing_files)}개의 누락된 파일 발견: {missing_files}")
            logger.info(f"누락된 파일 재생성을 시작합니다...")
            
            # skip_existing=False로 설정하여 모든 누락된 파일 재생성
            await process_single_db(tts_client, db_path, index, audio_base_dir, skip_existing=False)
        else:
            logger.info(f"{db_name}: 모든 파일이 정상적으로 존재합니다.")
            
    except Exception as e:
        logger.error(f"누락된 파일 확인 중 오류: {e}")
    finally:
        if conn:
            await conn.close()

# main 함수 수정 - force_regenerate 파라미터 추가
async def main(db_folder: str, force_regenerate: bool = False):
    """메인 실행 함수"""
    try:
        tts_client = texttospeech.TextToSpeechAsyncClient()
        logger.info("Google Cloud TTS 비동기 클라이언트 초기화 성공")
    except Exception as e:
        logger.error(f"Google Cloud TTS 클라이언트 초기화 실패: {e}")
        return

    logger.info("="*50)
    logger.info("오디오 생성 및 DB 업데이트 프로세스 시작")
    if force_regenerate:
        logger.info("강제 재생성 모드 활성화 - 기존 파일 무시")
    logger.info("="*50)
    
    start_time = time.time()
    
    target_dbs = get_db_files_to_process(db_folder)
    if not target_dbs:
        logger.warning(f"처리할 DB 파일이 없습니다. 'assets' 폴더를 확인해주세요: {db_folder}")
        return

    logger.info(f"처리 대상 DB 파일 ({len(target_dbs)}개): {[os.path.basename(p) for p in target_dbs]}")
    
    audio_base_dir = os.path.join(db_folder, "assets", "audio")
    os.makedirs(audio_base_dir, exist_ok=True)
    
    # 첫 번째 단계: 일반 처리
    for i, db_path in enumerate(target_dbs, 1):
        match = re.search(r'question(\d+)\.db', os.path.basename(db_path))
        if match:
            question_index = int(match.group(1))
            
            # [수정 2] 첫 번째 DB 처리 전 초기 딜레이 추가
            if i == 1:
                logger.info("첫 번째 DB 처리 전 3초 대기...")
                await asyncio.sleep(3)
            
            # force_regenerate가 True면 skip_existing=False로 설정
            await process_single_db(tts_client, db_path, question_index, audio_base_dir, 
                                  skip_existing=not force_regenerate)
    
    # [추가 3] 두 번째 단계: 누락된 파일 확인 및 재생성
    if not force_regenerate:  # 강제 재생성 모드가 아닐 때만 누락 파일 체크
        logger.info("\n" + "="*50)
        logger.info("누락된 파일 확인 및 재생성 단계 시작")
        logger.info("="*50)
        
        await asyncio.sleep(2)  # 잠시 대기
        
        for i, db_path in enumerate(target_dbs, 1):
            match = re.search(r'question(\d+)\.db', os.path.basename(db_path))
            if match:
                question_index = int(match.group(1))
                await check_and_regenerate_missing_files(tts_client, db_path, question_index, audio_base_dir)

    end_time = time.time()
    logger.info("\n" + "="*50)
    logger.info(f"모든 작업 완료. 총 소요 시간: {end_time - start_time:.2f}초")
    logger.info("="*50)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        # --force 옵션 체크
        force_regenerate = '--force' in sys.argv
        
        if os.path.isdir(folder_path):
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(main(folder_path, force_regenerate))
        else:
            print(f"오류: '{folder_path}'는 유효한 디렉토리가 아닙니다.")
    else:
        print("사용법: python 3_description_audio.py <DB 파일들이 있는 폴더 경로> [--force]")
        print("  --force: 기존 파일을 무시하고 모든 파일을 재생성합니다.")