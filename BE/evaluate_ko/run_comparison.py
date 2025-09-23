#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성능 비교 실행 스크립트
AutoSchemaKG와 OpenAI의 답변을 비교하는 다양한 방법을 제공합니다.
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from typing import Dict, Any

def run_single_comparison(question: str, document_id: str, api_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    단일 질문에 대한 비교를 실행합니다.
    
    Args:
        question: 질문
        document_id: 문서 ID
        api_url: API 서버 URL
        
    Returns:
        비교 결과
    """
    try:
        response = requests.post(
            f"{api_url}/compare-answers",
            data={
                "question": question,
                "document_id": document_id
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 비교 실행 실패: {e}")
        return None

def run_batch_comparison(questions_file: str, document_id: str, 
                        max_questions: int = None, api_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    배치 비교를 실행합니다.
    
    Args:
        questions_file: 질문 파일 경로
        document_id: 문서 ID
        max_questions: 최대 질문 수
        api_url: API 서버 URL
        
    Returns:
        비교 결과
    """
    try:
        data = {
            "questions_file": questions_file,
            "document_id": document_id
        }
        
        if max_questions:
            data["max_questions"] = max_questions
        
        response = requests.post(
            f"{api_url}/batch-compare",
            data=data,
            timeout=300  # 5분 타임아웃
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 배치 비교 실행 실패: {e}")
        return None

def print_comparison_result(result: Dict[str, Any]):
    """
    비교 결과를 출력합니다.
    """
    if not result:
        print("❌ 결과가 없습니다.")
        return
    
    print("\n" + "="*80)
    print("비교 결과")
    print("="*80)
    
    # 질문 정보
    if "question" in result:
        print(f"질문: {result['question']}")
        print(f"문서 ID: {result['document_id']}")
        print(f"타임스탬프: {result['timestamp']}")
        print("-" * 80)
        
        # AutoSchemaKG 결과
        atlas = result.get("atlas_result", {})
        print("🤖 AutoSchemaKG 답변:")
        print(f"   성공: {'✅' if atlas.get('success') else '❌'}")
        print(f"   처리 시간: {atlas.get('processing_time', 0):.2f}초")
        print(f"   컨텍스트 수: {atlas.get('context_count', 0)}")
        print(f"   답변: {atlas.get('answer', '')[:200]}...")
        print()
        
        # OpenAI 결과
        openai = result.get("openai_result", {})
        print("🧠 OpenAI 답변:")
        print(f"   성공: {'✅' if openai.get('success') else '❌'}")
        print(f"   처리 시간: {openai.get('processing_time', 0):.2f}초")
        print(f"   모델: {openai.get('model', 'N/A')}")
        print(f"   토큰 사용량: {openai.get('tokens_used', 0)}")
        print(f"   답변: {openai.get('answer', '')[:200]}...")
        print()
        
        # 유사도
        similarity = result.get("similarity", 0)
        print(f"📊 유사도: {similarity:.3f}")
        
    else:
        # 배치 결과
        metadata = result.get("metadata", {})
        analysis = result.get("analysis", {})
        summary = analysis.get("summary", {})
        
        print(f"질문 파일: {metadata.get('questions_file', 'N/A')}")
        print(f"문서 ID: {metadata.get('document_id', 'N/A')}")
        print(f"총 질문 수: {summary.get('total_questions', 0)}")
        print(f"성공한 비교: {summary.get('successful_comparisons', 0)}")
        print(f"성공률: {summary.get('success_rate', 0):.1f}%")
        print(f"평균 유사도: {summary.get('average_similarity', 0):.3f}")
        print(f"평균 AutoSchemaKG 시간: {summary.get('average_atlas_time', 0):.2f}초")
        print(f"평균 OpenAI 시간: {summary.get('average_openai_time', 0):.2f}초")
        print(f"처리 시간 차이: {summary.get('time_difference', 0):.2f}초")
    
    print("="*80)

def save_results(result: Dict[str, Any], output_file: str):
    """
    결과를 파일로 저장합니다.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 결과 저장 완료: {output_file}")
    except Exception as e:
        print(f"❌ 결과 저장 실패: {e}")

def main():
    """
    메인 실행 함수
    """
    parser = argparse.ArgumentParser(description="AutoSchemaKG와 OpenAI 성능 비교")
    parser.add_argument("--mode", choices=["single", "batch"], required=True, 
                       help="실행 모드: single (단일 질문) 또는 batch (배치 비교)")
    
    # 공통 옵션
    parser.add_argument("--document-id", required=True, help="문서 ID")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API 서버 URL")
    parser.add_argument("--output", help="결과 저장 파일 경로")
    
    # 단일 질문 모드 옵션
    parser.add_argument("--question", help="질문 (단일 모드에서 사용)")
    
    # 배치 모드 옵션
    parser.add_argument("--questions-file", help="질문 파일 경로 (배치 모드에서 사용)")
    parser.add_argument("--max-questions", type=int, help="최대 질문 수")
    
    args = parser.parse_args()
    
    # 서버 상태 확인
    try:
        response = requests.get(f"{args.api_url}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ 서버가 응답하지 않습니다: {args.api_url}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        sys.exit(1)
    
    print(f"🚀 {args.mode} 모드로 비교 시작...")
    
    if args.mode == "single":
        if not args.question:
            print("❌ 단일 모드에서는 --question 옵션이 필요합니다.")
            sys.exit(1)
        
        result = run_single_comparison(
            question=args.question,
            document_id=args.document_id,
            api_url=args.api_url
        )
        
    elif args.mode == "batch":
        if not args.questions_file:
            print("❌ 배치 모드에서는 --questions-file 옵션이 필요합니다.")
            sys.exit(1)
        
        if not Path(args.questions_file).exists():
            print(f"❌ 질문 파일을 찾을 수 없습니다: {args.questions_file}")
            sys.exit(1)
        
        result = run_batch_comparison(
            questions_file=args.questions_file,
            document_id=args.document_id,
            max_questions=args.max_questions,
            api_url=args.api_url
        )
    
    if result:
        print_comparison_result(result)
        
        if args.output:
            save_results(result, args.output)
    else:
        print("❌ 비교 실행에 실패했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()
