#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 OpenAI 채팅 스크립트
업로드된 계약서 파일을 읽어서 OpenAI에 전달하고 질문에 답변합니다.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import openai
from openai import OpenAI

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleOpenAIChat:
    def __init__(self, model: str = "gpt-4.1-2025-04-14"):
        """
        간단한 OpenAI 채팅 초기화

        Args:
            model: 사용할 OpenAI 모델
        """
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def load_contract_content(self, file_id: str) -> str:
        """
        업로드된 계약서 파일 내용을 로드합니다.

        Args:
            file_id: 파일 ID

        Returns:
            계약서 내용
        """
        try:
            # uploads 디렉토리에서 파일 찾기
            uploads_dir = Path(__file__).parent.parent.parent / "uploads"
            logger.info(f"파일 찾는 중: {uploads_dir}")

            # 파일 정보를 uploaded_files에서 가져오기
            server_dir = Path(__file__).parent.parent
            sys.path.append(str(server_dir))

            # server.py에서 업로드된 파일 정보 가져오기 시도
            try:
                from server import uploaded_files
                if file_id in uploaded_files:
                    file_info = uploaded_files[file_id]
                    file_path = uploads_dir / file_info['filename']
                    logger.info(f"파일 정보 찾음: {file_path}")

                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        logger.info(f"계약서 내용 로드 완료: {len(content)} 문자")
                        return content
            except ImportError:
                logger.warning("server 모듈을 import할 수 없습니다.")

            # 대안: 최근 파일 찾기
            if uploads_dir.exists():
                files = list(uploads_dir.glob("*.md"))
                if files:
                    latest_file = max(files, key=lambda f: f.stat().st_mtime)
                    logger.info(f"최근 파일 사용: {latest_file}")
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.info(f"계약서 내용 로드 완료: {len(content)} 문자")
                    return content

            return ""

        except Exception as e:
            logger.error(f"계약서 파일 로드 실패: {e}")
            return ""

    def get_openai_answer(self, question: str, contract_content: str) -> Dict[str, Any]:
        """
        OpenAI API를 통해 답변을 가져옵니다.

        Args:
            question: 질문
            contract_content: 계약서 내용

        Returns:
            OpenAI 답변 결과
        """
        try:
            start_time = time.time()

            # 메시지 구성 (시스템 프롬프트 없이 바로 질문과 계약서 내용 전달)
            if contract_content:
                messages = [
                    {"role": "user", "content": f"다음은 계약서 내용입니다:\n\n{contract_content}\n\n이 계약서에 대해 다음 질문에 답변해주세요: {question}"}
                ]
            else:
                messages = [
                    {"role": "user", "content": question}
                ]

            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000,
                temperature=1.0
            )

            api_time = time.time() - start_time
            answer = response.choices[0].message.content.strip()

            return {
                "success": True,
                "answer": answer,
                "processing_time": api_time,
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0
            }

        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": 0,
                "answer": "",
                "model": self.model,
                "tokens_used": 0
            }

    def chat(self, question: str, file_id: str = None) -> Dict[str, Any]:
        """
        채팅 함수

        Args:
            question: 질문
            file_id: 파일 ID (선택사항)

        Returns:
            채팅 결과
        """
        logger.info(f"간단한 OpenAI 채팅 시작: {question[:50]}...")

        # 계약서 내용 로드
        contract_content = ""
        if file_id:
            contract_content = self.load_contract_content(file_id)

        # OpenAI 답변 가져오기
        result = self.get_openai_answer(question, contract_content)

        return result

def main():
    """
    메인 실행 함수 (테스트용)
    """
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        return

    # 테스트 실행
    tester = SimpleOpenAIChat()

    # 샘플 질문
    test_question = "이 계약서에서 가장 위험한 조항이 무엇인가요?"

    try:
        result = tester.chat(test_question)
        print(f"질문: {test_question}")
        print(f"답변: {result.get('answer', '오류 발생')[:200]}...")
        print(f"처리시간: {result.get('processing_time', 0):.2f}초")
        print(f"토큰 사용량: {result.get('tokens_used', 0)}")
    except Exception as e:
        logger.error(f"테스트 실패: {e}")

if __name__ == "__main__":
    main()
