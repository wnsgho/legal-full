#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 연결 및 단일 질문 테스트 스크립트
"""

import requests
import json
import time
import sys
import io

# Windows에서 UTF-8 출력을 위한 설정
if sys.platform.startswith('win'):
    # stdout과 stderr을 UTF-8로 설정
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def test_api_connection(api_url="http://localhost:8000"):
    """API 연결 테스트"""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API 서버 연결 성공")
            return True
        else:
            print(f"❌ API 서버 응답 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 서버 연결 실패: {e}")
        return False

def test_single_question(question, api_url="http://localhost:8000"):
    """단일 질문 테스트"""
    url = f"{api_url}/chat"
    
    payload = {
        "question": question,
        "max_tokens": 2048,
        "temperature": 0.5
    }
    
    print(f"📝 질문: {question}")
    print("⏳ API 요청 중...")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 응답 성공 (소요시간: {processing_time:.2f}초)")
            print(f"📊 API 처리 시간: {data.get('processing_time', 0):.2f}초")
            print(f"🔍 컨텍스트 수: {data.get('context_count', 0)}개")
            print(f"📝 답변 길이: {len(data.get('answer', ''))}자")
            print(f"💬 답변 미리보기: {data.get('answer', '')[:200]}...")
            return data
        else:
            print(f"❌ API 요청 실패: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ API 요청 타임아웃: 30초")
        return None
    except Exception as e:
        print(f"❌ API 요청 오류: {e}")
        return None

def main():
    """메인 테스트 함수"""
    print("🧪 API 연결 및 질문 테스트")
    print("="*50)
    
    api_url = "http://localhost:8000"
    
    # 1. API 연결 테스트
    if not test_api_connection(api_url):
        print("❌ API 서버에 연결할 수 없습니다.")
        print("먼저 'python server.py'로 API 서버를 실행하세요.")
        return
    
    print()
    
    # 2. 테스트 질문들
    test_questions = [
        "제5조는 무엇에 관한 조항인가요?",
        "매매대금은 얼마인가요?",
        "이 계약서의 주요 위험요소는 무엇인가요?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n🔍 테스트 {i}/{len(test_questions)}")
        print("-" * 30)
        result = test_single_question(question, api_url)
        
        if result:
            print("✅ 테스트 성공")
        else:
            print("❌ 테스트 실패")
        
        # 요청 간 지연
        if i < len(test_questions):
            time.sleep(1)
    
    print("\n🎉 테스트 완료!")

if __name__ == "__main__":
    main()
