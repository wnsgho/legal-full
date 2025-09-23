#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 질문 파일을 사용한 자동 평가 스크립트
API 서버의 /chat 엔드포인트를 사용하여 질문을 하나씩 전송하고 결과를 분석합니다.
"""

import os
import sys
import json
import time
import requests
import argparse
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

# UTF-8 로깅 설정
try:
    from atlas_rag.utils.utf8_logging import setup_utf8_logging
    setup_utf8_logging()
except ImportError:
    # atlas_rag 모듈이 없는 경우 기본 로깅 설정
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """평가 결과를 저장하는 데이터 클래스"""
    question_id: int
    original_question_id: int
    question: str
    expected_answer: str
    actual_answer: str
    success: bool
    processing_time: float
    category: str
    difficulty: str
    points: int
    similarity_score: Optional[float] = None
    context_count: int = 0
    api_processing_time: float = 0.0
    error_message: Optional[str] = None

class AutoEvaluator:
    """자동 평가 클래스"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000", timeout: int = 30):
        self.api_base_url = api_base_url.rstrip('/')
        self.timeout = timeout
        self.results: List[EvaluationResult] = []
        
    def test_api_connection(self) -> bool:
        """API 서버 연결 테스트"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ API 서버 연결 성공")
                return True
            else:
                logger.error(f"❌ API 서버 응답 오류: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ API 서버 연결 실패: {e}")
            return False
    
    def send_question(self, question: str, max_tokens: int = 2048, temperature: float = 0.5) -> Dict[str, Any]:
        """단일 질문을 API로 전송"""
        url = f"{self.api_base_url}/chat"
        
        payload = {
            "question": question,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        logger.debug(f"🔍 API 요청 시작 - 타임아웃: {self.timeout}초")
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ API 요청 실패: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "answer": f"API 오류: {response.status_code}",
                    "context_count": 0,
                    "processing_time": 0
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ API 요청 타임아웃: {self.timeout}초")
            return {
                "success": False,
                "answer": "API 요청 타임아웃",
                "context_count": 0,
                "processing_time": self.timeout
            }
        except Exception as e:
            logger.error(f"❌ API 요청 오류: {e}")
            return {
                "success": False,
                "answer": f"API 요청 오류: {str(e)}",
                "context_count": 0,
                "processing_time": 0
            }
    
    def calculate_similarity(self, expected: str, actual: str) -> float:
        """답변 유사도 계산 (개선된 키워드 기반)"""
        if not expected or not actual:
            return 0.0
        
        # 텍스트 전처리
        expected_clean = self._clean_text(expected)
        actual_clean = self._clean_text(actual)
        
        # 키워드 추출 (불용어 제거)
        expected_keywords = set(expected_clean.split())
        actual_keywords = set(actual_clean.split())
        
        if not expected_keywords:
            return 0.0
        
        # 교집합 계산
        intersection = expected_keywords.intersection(actual_keywords)
        
        # Jaccard 유사도 계산
        union = expected_keywords.union(actual_keywords)
        jaccard_similarity = len(intersection) / len(union) if union else 0
        
        # 포함도 계산 (예상 답변의 키워드가 실제 답변에 얼마나 포함되는지)
        inclusion_similarity = len(intersection) / len(expected_keywords)
        
        # 가중 평균 (Jaccard 70%, 포함도 30%)
        similarity = (jaccard_similarity * 0.7) + (inclusion_similarity * 0.3)
        
        return min(similarity, 1.0)
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정리 (불용어 제거, 특수문자 제거)"""
        import re
        
        # 특수문자 제거 (한글, 영문, 숫자만 유지)
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        
        # 불용어 제거
        stopwords = {
            '은', '는', '이', '가', '을', '를', '에', '의', '로', '으로', '와', '과', '도', '만', '부터', '까지',
            '에서', '에게', '한테', '께', '더', '또', '그리고', '하지만', '그런데', '그러나', '따라서',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'
        }
        
        words = text.lower().split()
        cleaned_words = [word for word in words if word not in stopwords and len(word) > 1]
        
        return ' '.join(cleaned_words)
    
    def evaluate_single_question(self, question_data: Dict[str, Any]) -> EvaluationResult:
        """단일 질문 평가"""
        question_id = question_data.get("question_id", 0)
        original_question_id = question_data.get("original_question_id", 0)
        question = question_data.get("question", "")
        expected_answer = question_data.get("answer", "")
        category = question_data.get("category", "기타")
        difficulty = question_data.get("difficulty", "low")
        points = question_data.get("points", 3)
        
        logger.info(f"📝 질문 {question_id} 평가 중: {question[:50]}...")
        
        # API로 질문 전송
        start_time = time.time()
        api_response = self.send_question(question)
        processing_time = time.time() - start_time
        
        # 결과 분석
        success = api_response.get("success", False)
        actual_answer = api_response.get("answer", "")
        api_processing_time = api_response.get("processing_time", 0)
        context_count = api_response.get("context_count", 0)
        
        # 유사도 계산
        similarity_score = self.calculate_similarity(expected_answer, actual_answer)
        
        # 결과 생성
        result = EvaluationResult(
            question_id=question_id,
            original_question_id=original_question_id,
            question=question,
            expected_answer=expected_answer,
            actual_answer=actual_answer,
            success=success,
            processing_time=processing_time,
            category=category,
            difficulty=difficulty,
            points=points,
            similarity_score=similarity_score,
            context_count=context_count,
            api_processing_time=api_processing_time,
            error_message=None if success else "API 호출 실패"
        )
        
        logger.info(f"✅ 질문 {question_id} 완료 - 성공: {success}, 유사도: {similarity_score:.3f}")
        
        return result
    
    def load_questions(self, json_file_path: str) -> List[Dict[str, Any]]:
        """JSON 질문 파일 로드 (기존 형식과 새로운 형식 모두 지원)"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            questions = []
            
            # 새로운 형식 (questions 배열이 직접 있는 경우)
            if "questions" in data:
                questions = data["questions"]
                logger.info(f"📚 새로운 형식으로 {len(questions)}개 질문 로드 완료")
            # 기존 형식 (sections 배열 안에 questions가 있는 경우)
            elif "sections" in data:
                for section in data.get("sections", []):
                    questions.extend(section.get("questions", []))
                logger.info(f"📚 기존 형식으로 {len(questions)}개 질문 로드 완료")
            else:
                logger.error("❌ 지원되지 않는 JSON 형식입니다.")
                return []
            
            return questions
            
        except Exception as e:
            logger.error(f"❌ 질문 파일 로드 실패: {e}")
            return []
    
    def run_evaluation(self, json_file_path: str, max_questions: Optional[int] = None, 
                      start_from: int = 0, delay_between_requests: float = 1.0) -> List[EvaluationResult]:
        """전체 평가 실행"""
        logger.info("🚀 자동 평가 시작")
        
        # API 연결 테스트
        if not self.test_api_connection():
            logger.error("❌ API 서버에 연결할 수 없습니다. 평가를 중단합니다.")
            return []
        
        # 질문 로드
        questions = self.load_questions(json_file_path)
        if not questions:
            logger.error("❌ 질문을 로드할 수 없습니다.")
            return []
        
        # 평가할 질문 선택
        if max_questions:
            questions = questions[start_from:start_from + max_questions]
        else:
            questions = questions[start_from:]
        
        logger.info(f"📊 {len(questions)}개 질문 평가 예정 (시작: {start_from})")
        
        # 질문별 평가 실행
        for i, question_data in enumerate(questions, 1):
            try:
                result = self.evaluate_single_question(question_data)
                self.results.append(result)
                
                # 진행률 표시
                progress = (i / len(questions)) * 100
                logger.info(f"📈 진행률: {progress:.1f}% ({i}/{len(questions)})")
                
                # 요청 간 지연
                if delay_between_requests > 0 and i < len(questions):
                    time.sleep(delay_between_requests)
                    
            except Exception as e:
                logger.error(f"❌ 질문 {i} 평가 실패: {e}")
                # 실패한 질문도 결과에 추가
                error_result = EvaluationResult(
                    question_id=question_data.get("question_id", i),
                    original_question_id=question_data.get("original_question_id", i),
                    question=question_data.get("question", ""),
                    expected_answer=question_data.get("answer", ""),
                    actual_answer="",
                    success=False,
                    processing_time=0,
                    category=question_data.get("category", "기타"),
                    difficulty=question_data.get("difficulty", "low"),
                    points=question_data.get("points", 3),
                    error_message=str(e)
                )
                self.results.append(error_result)
        
        logger.info("✅ 자동 평가 완료")
        return self.results
    
    def analyze_results(self) -> Dict[str, Any]:
        """평가 결과 분석"""
        if not self.results:
            return {}
        
        total_questions = len(self.results)
        successful_questions = sum(1 for r in self.results if r.success)
        failed_questions = total_questions - successful_questions
        
        # 유사도 통계
        similarities = [r.similarity_score for r in self.results if r.similarity_score is not None]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        
        # 카테고리별 통계
        category_stats = {}
        for result in self.results:
            category = result.category
            if category not in category_stats:
                category_stats[category] = {
                    "total": 0,
                    "successful": 0,
                    "avg_similarity": 0,
                    "total_points": 0,
                    "earned_points": 0
                }
            
            category_stats[category]["total"] += 1
            if result.success:
                category_stats[category]["successful"] += 1
            category_stats[category]["total_points"] += result.points
            if result.similarity_score and result.similarity_score > 0.5:  # 50% 이상 유사도
                category_stats[category]["earned_points"] += result.points
        
        # 난이도별 통계
        difficulty_stats = {}
        for result in self.results:
            difficulty = result.difficulty
            if difficulty not in difficulty_stats:
                difficulty_stats[difficulty] = {
                    "total": 0,
                    "successful": 0,
                    "avg_similarity": 0
                }
            
            difficulty_stats[difficulty]["total"] += 1
            if result.success:
                difficulty_stats[difficulty]["successful"] += 1
        
        # 처리 시간 통계
        processing_times = [r.processing_time for r in self.results if r.processing_time > 0]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # API 처리 시간 통계
        api_processing_times = [r.api_processing_time for r in self.results if r.api_processing_time > 0]
        avg_api_processing_time = sum(api_processing_times) / len(api_processing_times) if api_processing_times else 0
        
        # 컨텍스트 통계
        context_counts = [r.context_count for r in self.results if r.context_count > 0]
        avg_context_count = sum(context_counts) / len(context_counts) if context_counts else 0
        total_contexts = sum(context_counts)
        
        analysis = {
            "summary": {
                "total_questions": total_questions,
                "successful_questions": successful_questions,
                "failed_questions": failed_questions,
                "success_rate": (successful_questions / total_questions) * 100 if total_questions > 0 else 0,
                "average_similarity": avg_similarity,
                "average_processing_time": avg_processing_time,
                "average_api_processing_time": avg_api_processing_time,
                "average_context_count": avg_context_count,
                "total_contexts_retrieved": total_contexts
            },
            "category_stats": category_stats,
            "difficulty_stats": difficulty_stats
        }
        
        return analysis
    
    def save_results(self, output_file: str):
        """평가 결과를 JSON 파일로 저장"""
        try:
            # 결과 데이터 준비
            results_data = {
                "evaluation_info": {
                    "timestamp": datetime.now().isoformat(),
                    "api_base_url": self.api_base_url,
                    "total_questions": len(self.results)
                },
                "analysis": self.analyze_results(),
                "detailed_results": []
            }
            
            # 상세 결과 추가
            for result in self.results:
                result_dict = {
                    "question_id": result.question_id,
                    "original_question_id": result.original_question_id,
                    "question": result.question,
                    "expected_answer": result.expected_answer,
                    "actual_answer": result.actual_answer,
                    "success": result.success,
                    "processing_time": result.processing_time,
                    "category": result.category,
                    "difficulty": result.difficulty,
                    "points": result.points,
                    "similarity_score": result.similarity_score,
                    "context_count": result.context_count,
                    "api_processing_time": result.api_processing_time,
                    "error_message": result.error_message
                }
                results_data["detailed_results"].append(result_dict)
            
            # 파일 저장
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 평가 결과 저장 완료: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ 결과 저장 실패: {e}")
    
    def print_summary(self):
        """평가 결과 요약 출력"""
        analysis = self.analyze_results()
        
        if not analysis:
            print("❌ 분석할 결과가 없습니다.")
            return
        
        summary = analysis["summary"]
        
        print("\n" + "="*60)
        print("📊 평가 결과 요약")
        print("="*60)
        print(f"총 질문 수: {summary['total_questions']}")
        print(f"성공한 질문: {summary['successful_questions']}")
        print(f"실패한 질문: {summary['failed_questions']}")
        print(f"성공률: {summary['success_rate']:.1f}%")
        print(f"평균 유사도: {summary['average_similarity']:.3f}")
        print(f"평균 처리 시간: {summary['average_processing_time']:.2f}초")
        print(f"평균 API 처리 시간: {summary['average_api_processing_time']:.2f}초")
        print(f"평균 컨텍스트 수: {summary['average_context_count']:.1f}개")
        print(f"총 검색된 컨텍스트: {summary['total_contexts_retrieved']}개")
        
        # 카테고리별 통계
        print("\n📈 카테고리별 통계:")
        for category, stats in analysis["category_stats"].items():
            success_rate = (stats["successful"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            point_rate = (stats["earned_points"] / stats["total_points"]) * 100 if stats["total_points"] > 0 else 0
            print(f"  {category}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%) - 점수: {stats['earned_points']}/{stats['total_points']} ({point_rate:.1f}%)")
        
        # 난이도별 통계
        print("\n🎯 난이도별 통계:")
        for difficulty, stats in analysis["difficulty_stats"].items():
            success_rate = (stats["successful"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"  {difficulty}: {stats['successful']}/{stats['total']} ({success_rate:.1f}%)")
        
        print("="*60)

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="JSON 질문 파일을 사용한 자동 평가")
    parser.add_argument("--input", "-i", required=True, help="입력 JSON 질문 파일 경로")
    parser.add_argument("--output", "-o", help="출력 결과 파일 경로 (기본: evaluation_results.json)")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API 서버 URL (기본: http://localhost:8000)")
    parser.add_argument("--max-questions", "-m", type=int, help="평가할 최대 질문 수")
    parser.add_argument("--start-from", "-s", type=int, default=0, help="시작 질문 번호 (0부터)")
    parser.add_argument("--delay", "-d", type=float, default=1.0, help="요청 간 지연 시간 (초)")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="API 요청 타임아웃 (초)")
    
    args = parser.parse_args()
    
    # 출력 파일 경로 설정
    if not args.output:
        input_path = Path(args.input)
        args.output = input_path.parent / f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # 평가자 생성
    evaluator = AutoEvaluator(api_base_url=args.api_url, timeout=args.timeout)
    
    # 평가 실행
    results = evaluator.run_evaluation(
        json_file_path=args.input,
        max_questions=args.max_questions,
        start_from=args.start_from,
        delay_between_requests=args.delay
    )
    
    if results:
        # 결과 저장
        evaluator.save_results(str(args.output))
        
        # 요약 출력
        evaluator.print_summary()
        
        print(f"\n✅ 평가 완료! 결과가 저장되었습니다: {args.output}")
    else:
        print("❌ 평가를 실행할 수 없습니다.")

if __name__ == "__main__":
    main()
