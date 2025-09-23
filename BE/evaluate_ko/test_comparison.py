#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
성능 비교 테스트 스크립트
"""

import os
import sys
import json
import requests
from pathlib import Path

def test_server_health(api_url: str = "http://localhost:8000") -> bool:
    """
    서버 상태를 확인합니다.
    """
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 서버가 정상적으로 실행 중입니다.")
            return True
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        return False

def test_single_comparison(api_url: str = "http://localhost:8000") -> bool:
    """
    단일 질문 비교를 테스트합니다.
    """
    print("\n🧪 단일 질문 비교 테스트...")
    
    test_question = "이 계약서에서 독소조항이 있습니까?"
    test_document_id = "contract_01"  # 실제 업로드된 문서 ID로 변경
    
    try:
        response = requests.post(
            f"{api_url}/compare-answers",
            data={
                "question": test_question,
                "document_id": test_document_id
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 단일 질문 비교 성공")
            print(f"   질문: {result.get('question', '')[:50]}...")
            print(f"   유사도: {result.get('similarity', 0):.3f}")
            print(f"   AutoSchemaKG 성공: {result.get('atlas_result', {}).get('success', False)}")
            print(f"   OpenAI 성공: {result.get('openai_result', {}).get('success', False)}")
            return True
        else:
            print(f"❌ 단일 질문 비교 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 단일 질문 비교 오류: {e}")
        return False

def test_batch_comparison(api_url: str = "http://localhost:8000") -> bool:
    """
    배치 비교를 테스트합니다.
    """
    print("\n🧪 배치 비교 테스트...")
    
    questions_file = "question_C1_questions.json"
    test_document_id = "contract_01"  # 실제 업로드된 문서 ID로 변경
    
    if not Path(questions_file).exists():
        print(f"❌ 질문 파일을 찾을 수 없습니다: {questions_file}")
        return False
    
    try:
        response = requests.post(
            f"{api_url}/batch-compare",
            data={
                "questions_file": questions_file,
                "document_id": test_document_id,
                "max_questions": 3  # 테스트용으로 3개만
            },
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            summary = result.get("analysis", {}).get("summary", {})
            print("✅ 배치 비교 성공")
            print(f"   총 질문 수: {summary.get('total_questions', 0)}")
            print(f"   성공한 비교: {summary.get('successful_comparisons', 0)}")
            print(f"   성공률: {summary.get('success_rate', 0):.1f}%")
            print(f"   평균 유사도: {summary.get('average_similarity', 0):.3f}")
            return True
        else:
            print(f"❌ 배치 비교 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 배치 비교 오류: {e}")
        return False

def test_environment() -> bool:
    """
    환경 설정을 확인합니다.
    """
    print("🔍 환경 설정 확인...")
    
    # OpenAI API 키 확인
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        return False
    else:
        print("✅ OPENAI_API_KEY 설정됨")
    
    # 질문 파일 확인
    questions_file = "question_C1_questions.json"
    if not Path(questions_file).exists():
        print(f"❌ 질문 파일을 찾을 수 없습니다: {questions_file}")
        return False
    else:
        print(f"✅ 질문 파일 존재: {questions_file}")
    
    # 업로드 디렉토리 확인
    upload_dir = Path("../uploads")
    if not upload_dir.exists():
        print(f"❌ 업로드 디렉토리를 찾을 수 없습니다: {upload_dir}")
        return False
    else:
        print(f"✅ 업로드 디렉토리 존재: {upload_dir}")
        
        # 업로드된 파일 확인
        md_files = list(upload_dir.glob("*.md"))
        if not md_files:
            print("⚠️  업로드된 .md 파일이 없습니다.")
            print("   먼저 문서를 업로드하세요.")
        else:
            print(f"✅ 업로드된 파일 {len(md_files)}개 발견")
            for file in md_files[:3]:  # 처음 3개만 표시
                print(f"   - {file.name}")
    
    return True

def main():
    """
    메인 테스트 함수
    """
    print("🚀 AutoSchemaKG vs OpenAI 성능 비교 테스트 시작")
    print("="*60)
    
    api_url = "http://localhost:8000"
    
    # 환경 설정 확인
    if not test_environment():
        print("\n❌ 환경 설정 확인 실패")
        sys.exit(1)
    
    # 서버 상태 확인
    if not test_server_health(api_url):
        print("\n❌ 서버 상태 확인 실패")
        print("서버를 시작하세요: cd BE && python server.py")
        sys.exit(1)
    
    # 단일 질문 비교 테스트
    single_success = test_single_comparison(api_url)
    
    # 배치 비교 테스트
    batch_success = test_batch_comparison(api_url)
    
    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)
    print(f"환경 설정: ✅")
    print(f"서버 상태: ✅")
    print(f"단일 질문 비교: {'✅' if single_success else '❌'}")
    print(f"배치 비교: {'✅' if batch_success else '❌'}")
    
    if single_success and batch_success:
        print("\n🎉 모든 테스트가 성공했습니다!")
        print("이제 성능 비교를 실행할 수 있습니다.")
    else:
        print("\n⚠️  일부 테스트가 실패했습니다.")
        print("문제를 해결한 후 다시 시도하세요.")

if __name__ == "__main__":
    main()
