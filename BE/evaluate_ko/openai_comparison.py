#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI API를 사용한 성능 비교 스크립트
AutoSchemaKG 프로젝트와 OpenAI GPT의 답변을 비교합니다.
"""

import os
import sys
import json
import time
import logging
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import openai
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('openai_comparison.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OpenAIComparison:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        OpenAI 비교 클래스 초기화
        
        Args:
            api_base_url: AutoSchemaKG 백엔드 서버 URL
        """
        self.api_base_url = api_base_url
        self.openai_client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # 결과 저장용
        self.comparison_results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "api_base_url": api_base_url,
                "openai_model": "gpt-4o",
                "total_questions": 0
            },
            "comparison_results": [],
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
    
    def get_atlas_answer(self, question: str, document_id: str) -> Dict[str, Any]:
        """
        AutoSchemaKG API를 통해 답변을 가져옵니다.
        
        Args:
            question: 질문
            document_id: 문서 ID
            
        Returns:
            AutoSchemaKG 답변 결과
        """
        try:
            start_time = time.time()
            
            # /chat 엔드포인트 호출
            response = requests.post(
                f"{self.api_base_url}/chat",
                json={
                    "question": question,
                    "document_id": document_id
                },
                timeout=60
            )
            
            api_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "answer": result.get("answer", ""),
                    "contexts": result.get("contexts", []),
                    "processing_time": api_time,
                    "context_count": len(result.get("contexts", [])),
                    "raw_response": result
                }
            else:
                return {
                    "success": False,
                    "error": f"API 호출 실패: {response.status_code}",
                    "processing_time": api_time,
                    "answer": "",
                    "contexts": [],
                    "context_count": 0
                }
                
        except Exception as e:
            logger.error(f"AutoSchemaKG API 호출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": 0,
                "answer": "",
                "contexts": [],
                "context_count": 0
            }
    
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

답변 시 다음 사항을 고려해주세요:
1. 계약서의 구체적인 조항을 인용하여 답변
2. 법적 관점에서 정확하고 상세한 분석 제공
3. 독소조항이나 위험 요소가 있다면 명확히 지적
4. 답변 근거가 되는 조항 번호나 내용을 구체적으로 제시
"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "당신은 계약서 분석 전문가입니다. 주어진 계약서를 바탕으로 정확하고 상세한 분석을 제공해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            api_time = time.time() - start_time
            
            answer = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "answer": answer,
                "processing_time": api_time,
                "model": "gpt-4o",
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time": 0,
                "answer": "",
                "model": "gpt-4o",
                "tokens_used": 0
            }
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        두 텍스트 간의 유사도를 계산합니다. (간단한 Jaccard 유사도)
        
        Args:
            text1: 첫 번째 텍스트
            text2: 두 번째 텍스트
            
        Returns:
            유사도 점수 (0-1)
        """
        try:
            # 간단한 단어 기반 Jaccard 유사도
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 and not words2:
                return 1.0
            if not words1 or not words2:
                return 0.0
                
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"유사도 계산 실패: {e}")
            return 0.0
    
    def run_comparison(self, questions_file: str, document_path: str, document_id: str, 
                      max_questions: Optional[int] = None) -> Dict[str, Any]:
        """
        성능 비교를 실행합니다.
        
        Args:
            questions_file: 질문 파일 경로
            document_path: 문서 파일 경로
            document_id: 문서 ID
            max_questions: 최대 질문 수 (None이면 모든 질문)
            
        Returns:
            비교 결과
        """
        logger.info("성능 비교 시작")
        
        # 질문 로드
        questions_data = self.load_questions(questions_file)
        questions = questions_data.get("questions", [])
        
        if max_questions:
            questions = questions[:max_questions]
        
        # 문서 로드
        document_content = self.load_document(document_path)
        
        self.comparison_results["metadata"]["total_questions"] = len(questions)
        
        successful_comparisons = 0
        total_atlas_time = 0
        total_openai_time = 0
        total_similarity = 0
        
        for i, question_data in enumerate(questions, 1):
            question_id = question_data.get("question_id", i)
            question = question_data.get("question", "")
            expected_answer = question_data.get("answer", "")
            
            logger.info(f"질문 {i}/{len(questions)} 처리 중: {question[:50]}...")
            
            # AutoSchemaKG 답변 가져오기
            atlas_result = self.get_atlas_answer(question, document_id)
            
            # OpenAI 답변 가져오기
            openai_result = self.get_openai_answer(question, document_content)
            
            # 유사도 계산
            similarity = 0.0
            if atlas_result["success"] and openai_result["success"]:
                similarity = self.calculate_similarity(
                    atlas_result["answer"], 
                    openai_result["answer"]
                )
            
            # 결과 저장
            comparison_result = {
                "question_id": question_id,
                "question": question,
                "expected_answer": expected_answer,
                "atlas_result": atlas_result,
                "openai_result": openai_result,
                "similarity": similarity,
                "processing_time": {
                    "atlas": atlas_result.get("processing_time", 0),
                    "openai": openai_result.get("processing_time", 0)
                }
            }
            
            self.comparison_results["comparison_results"].append(comparison_result)
            
            # 통계 업데이트
            if atlas_result["success"] and openai_result["success"]:
                successful_comparisons += 1
                total_atlas_time += atlas_result.get("processing_time", 0)
                total_openai_time += openai_result.get("processing_time", 0)
                total_similarity += similarity
            
            logger.info(f"질문 {i} 완료 - 유사도: {similarity:.3f}")
        
        # 분석 결과 생성
        self.comparison_results["analysis"] = {
            "summary": {
                "total_questions": len(questions),
                "successful_comparisons": successful_comparisons,
                "success_rate": (successful_comparisons / len(questions)) * 100 if questions else 0,
                "average_similarity": total_similarity / successful_comparisons if successful_comparisons > 0 else 0,
                "average_atlas_time": total_atlas_time / successful_comparisons if successful_comparisons > 0 else 0,
                "average_openai_time": total_openai_time / successful_comparisons if successful_comparisons > 0 else 0,
                "time_difference": (total_atlas_time - total_openai_time) / successful_comparisons if successful_comparisons > 0 else 0
            }
        }
        
        logger.info("성능 비교 완료")
        return self.comparison_results
    
    def save_results(self, output_file: str):
        """
        결과를 파일로 저장합니다.
        
        Args:
            output_file: 출력 파일 경로
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.comparison_results, f, ensure_ascii=False, indent=2)
            logger.info(f"결과 저장 완료: {output_file}")
        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")
            raise
    
    def print_summary(self):
        """
        비교 결과 요약을 출력합니다.
        """
        analysis = self.comparison_results.get("analysis", {})
        summary = analysis.get("summary", {})
        
        print("\n" + "="*60)
        print("성능 비교 결과 요약")
        print("="*60)
        print(f"총 질문 수: {summary.get('total_questions', 0)}")
        print(f"성공한 비교: {summary.get('successful_comparisons', 0)}")
        print(f"성공률: {summary.get('success_rate', 0):.1f}%")
        print(f"평균 유사도: {summary.get('average_similarity', 0):.3f}")
        print(f"평균 AutoSchemaKG 처리 시간: {summary.get('average_atlas_time', 0):.2f}초")
        print(f"평균 OpenAI 처리 시간: {summary.get('average_openai_time', 0):.2f}초")
        print(f"처리 시간 차이: {summary.get('time_difference', 0):.2f}초")
        print("="*60)


def main():
    """
    메인 실행 함수
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenAI와 AutoSchemaKG 성능 비교")
    parser.add_argument("--questions", required=True, help="질문 파일 경로")
    parser.add_argument("--document", required=True, help="문서 파일 경로")
    parser.add_argument("--document-id", required=True, help="문서 ID")
    parser.add_argument("--output", default="openai_comparison_results.json", help="출력 파일 경로")
    parser.add_argument("--max-questions", type=int, help="최대 질문 수")
    parser.add_argument("--api-url", default="http://localhost:8000", help="AutoSchemaKG API URL")
    
    args = parser.parse_args()
    
    # OpenAI API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    # 비교 실행
    comparison = OpenAIComparison(api_base_url=args.api_url)
    
    try:
        results = comparison.run_comparison(
            questions_file=args.questions,
            document_path=args.document,
            document_id=args.document_id,
            max_questions=args.max_questions
        )
        
        # 결과 저장
        comparison.save_results(args.output)
        
        # 요약 출력
        comparison.print_summary()
        
    except Exception as e:
        logger.error(f"비교 실행 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
