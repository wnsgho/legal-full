#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI GPT 전용 질문 테스트 스크립트
본문을 OpenAI에 넣고 질문에 대한 답변을 생성합니다.
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai
from dotenv import load_dotenv
import re

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('openai_only_test.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OpenAITester:
    def __init__(self, model: str = "gpt-4.1"):
        """
        OpenAI 테스터 초기화
        
        Args:
            model: 사용할 OpenAI 모델
        """
        self.model = model
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 결과 저장용
        self.test_results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "model": model,
                "total_questions": 0
            },
            "test_results": [],
            "analysis": {}
        }
    
    def load_questions(self, questions_file: str) -> Dict[str, Any]:
        """
        질문 파일을 로드합니다.
        
        Args:
            questions_file: 질문 파일 경로
            
        Returns:
            질문 데이터 딕셔너리
        """
        try:
            with open(questions_file, 'r', encoding='utf-8') as f:
                questions_data = json.load(f)
            logger.info(f"질문 파일 로드 완료: {questions_file}")
            return questions_data
        except Exception as e:
            logger.error(f"질문 파일 로드 실패: {e}")
            raise
    
    def load_document(self, document_path: str) -> str:
        """
        문서 파일을 로드합니다.
        
        Args:
            document_path: 문서 파일 경로
            
        Returns:
            문서 내용 문자열
        """
        try:
            with open(document_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"문서 파일 로드 완료: {document_path}")
            return content
        except Exception as e:
            logger.error(f"문서 파일 로드 실패: {e}")
            raise
    
    def get_openai_answer(self, question: str, document_content: str) -> Dict[str, Any]:
        """
        OpenAI API를 통해 답변을 가져옵니다.
        
        Args:
            question: 질문
            document_content: 문서 내용
            
        Returns:
            OpenAI 답변 결과
        """
        try:
            start_time = time.time()
            
            # 프롬프트 구성
            prompt = f"""
다음 계약서 내용을 바탕으로 질문에 답변해주세요.

계약서 내용:
{document_content}

질문: {question}

"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.1
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
    
    def run_test(self, questions_file: str, document_path: str, 
                max_questions: Optional[int] = None) -> Dict[str, Any]:
        """
        OpenAI 테스트를 실행합니다.
        
        Args:
            questions_file: 질문 파일 경로
            document_path: 문서 파일 경로
            max_questions: 최대 질문 수 (None이면 모든 질문)
            
        Returns:
            테스트 결과
        """
        logger.info("OpenAI 테스트 시작")
        
        # 질문 로드
        questions_data = self.load_questions(questions_file)
        questions = questions_data.get("questions", [])
        
        if max_questions:
            questions = questions[:max_questions]
        
        # 문서 로드
        document_content = self.load_document(document_path)
        
        self.test_results["metadata"]["total_questions"] = len(questions)
        
        successful_tests = 0
        total_time = 0
        total_tokens = 0
        
        for i, question_data in enumerate(questions, 1):
            question_id = question_data.get("question_id", i)
            question = question_data.get("question", "")
            expected_answer = question_data.get("answer", "")
            
            logger.info(f"질문 {i}/{len(questions)} 처리 중: {question[:50]}...")
            
            # OpenAI 답변 가져오기
            openai_result = self.get_openai_answer(question, document_content)
            
            # 결과 저장
            test_result = {
                "question_id": question_id,
                "question": question,
                "expected_answer": expected_answer,
                "openai_result": openai_result,
                "processing_time": openai_result.get("processing_time", 0)
            }
            
            self.test_results["test_results"].append(test_result)
            
            # 통계 업데이트
            if openai_result["success"]:
                successful_tests += 1
                total_time += openai_result.get("processing_time", 0)
                total_tokens += openai_result.get("tokens_used", 0)
            
            logger.info(f"질문 {i} 완료 - 처리시간: {openai_result.get('processing_time', 0):.2f}초")
        
        # 분석 결과 생성
        self.test_results["analysis"] = {
            "summary": {
                "total_questions": len(questions),
                "successful_tests": successful_tests,
                "success_rate": (successful_tests / len(questions)) * 100 if questions else 0,
                "average_processing_time": total_time / successful_tests if successful_tests > 0 else 0,
                "total_tokens_used": total_tokens,
                "average_tokens_per_question": total_tokens / successful_tests if successful_tests > 0 else 0
            }
        }
        
        logger.info("OpenAI 테스트 완료")
        return self.test_results
    
    def save_results(self, output_file: str):
        """
        결과를 파일로 저장합니다.
        
        Args:
            output_file: 출력 파일 경로
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, ensure_ascii=False, indent=2)
            logger.info(f"결과 저장 완료: {output_file}")
        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")
            raise
    
    def print_summary(self):
        """
        테스트 결과 요약을 출력합니다.
        """
        analysis = self.test_results.get("analysis", {})
        summary = analysis.get("summary", {})
        
        print("\n" + "="*60)
        print("OpenAI 테스트 결과 요약")
        print("="*60)
        print(f"모델: {self.model}")
        print(f"총 질문 수: {summary.get('total_questions', 0)}")
        print(f"성공한 테스트: {summary.get('successful_tests', 0)}")
        print(f"성공률: {summary.get('success_rate', 0):.1f}%")
        print(f"평균 처리 시간: {summary.get('average_processing_time', 0):.2f}초")
        print(f"총 토큰 사용량: {summary.get('total_tokens_used', 0):,}")
        print(f"질문당 평균 토큰: {summary.get('average_tokens_per_question', 0):.0f}")
        print("="*60)
    
    def print_detailed_results(self, max_results: int = 5):
        """
        상세 결과를 출력합니다.
        
        Args:
            max_results: 출력할 최대 결과 수
        """
        results = self.test_results.get("test_results", [])
        
        print(f"\n📋 상세 결과 (최대 {max_results}개)")
        print("-" * 80)
        
        for i, result in enumerate(results[:max_results], 1):
            question = result.get("question", "")
            openai_result = result.get("openai_result", {})
            answer = openai_result.get("answer", "")
            
            print(f"\n{i}. 질문: {question}")
            print(f"   처리시간: {openai_result.get('processing_time', 0):.2f}초")
            print(f"   토큰 사용량: {openai_result.get('tokens_used', 0):,}")
            print(f"   답변: {answer[:200]}...")
            print("-" * 80)

def main():
    """
    메인 실행 함수
    """
    parser = argparse.ArgumentParser(description="OpenAI GPT 전용 질문 테스트")
    parser.add_argument("--questions", required=True, help="질문 파일 경로")
    parser.add_argument("--document", required=True, help="문서 파일 경로")
    parser.add_argument("--output", default="openai_only_results.json", help="출력 파일 경로(미지정 시 문서 번호로 자동 명명)")
    parser.add_argument("--max-questions", type=int, help="최대 질문 수")
    parser.add_argument("--model", default="gpt-4.1", help="OpenAI 모델 (gpt-4.1, gpt-4, gpt-3.5-turbo)")
    parser.add_argument("--detailed", action="store_true", help="상세 결과 출력")
    
    args = parser.parse_args()
    
    # OpenAI API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    # 파일 존재 확인
    if not Path(args.questions).exists():
        logger.error(f"질문 파일을 찾을 수 없습니다: {args.questions}")
        sys.exit(1)
    
    if not Path(args.document).exists():
        logger.error(f"문서 파일을 찾을 수 없습니다: {args.document}")
        sys.exit(1)
    
    # 테스트 실행
    tester = OpenAITester(model=args.model)
    
    try:
        results = tester.run_test(
            questions_file=args.questions,
            document_path=args.document,
            max_questions=args.max_questions
        )
        
        # 결과 파일명 자동 결정: contract 번호 기반
        def derive_output_path(document_path: str, user_output: Optional[str]) -> str:
            if user_output and user_output != "openai_only_results.json":
                return user_output
            base = Path(document_path).stem  # e.g., contract_5
            match = re.search(r"contract[_\-\s]?(\d+)", base, re.IGNORECASE)
            if match:
                return f"openai_only_results_contract_{match.group(1)}.json"
            # 숫자 패턴이 없을 경우 전체 베이스명 사용
            return f"openai_only_results_{base}.json"

        output_path = derive_output_path(args.document, args.output)

        # 결과 저장
        tester.save_results(output_path)
        
        # 요약 출력
        tester.print_summary()
        
        # 상세 결과 출력
        if args.detailed:
            tester.print_detailed_results()
        
    except Exception as e:
        logger.error(f"테스트 실행 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
