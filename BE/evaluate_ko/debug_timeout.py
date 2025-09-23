#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
타임아웃 문제 디버깅 스크립트
"""

import requests
import time
import logging
import sys
import io

# UTF-8 로깅 설정
from atlas_rag.utils.utf8_logging import setup_utf8_logging

# UTF-8 로깅 초기화
setup_utf8_logging(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_timeout(question, timeout=30):
    """타임아웃 테스트"""
    url = "http://localhost:8000/chat"
    
    payload = {
        "question": question,
        "max_tokens": 2048,
        "temperature": 0.5
    }
    
    print(f"🔍 질문: {question}")
    print(f"⏱️ 타임아웃: {timeout}초")
    print("⏳ API 요청 시작...")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ 응답 성공 (소요시간: {duration:.2f}초)")
        print(f"📊 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 API 처리 시간: {data.get('processing_time', 0):.2f}초")
            print(f"🔍 컨텍스트 수: {data.get('context_count', 0)}개")
            print(f"📝 답변 길이: {len(data.get('answer', ''))}자")
            return True
        else:
            print(f"❌ API 오류: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ 타임아웃 발생! (실제 소요시간: {duration:.2f}초, 설정 타임아웃: {timeout}초)")
        return False
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ 오류 발생: {e} (소요시간: {duration:.2f}초)")
        return False

def main():
    """메인 테스트 함수"""
    print("🧪 타임아웃 디버깅 테스트")
    print("="*50)
    
    # API 서버 연결 확인
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ API 서버가 실행되지 않았습니다.")
            return
    except Exception as e:
        print(f"❌ API 서버 연결 실패: {e}")
        return
    
    print("✅ API 서버 연결 확인")
    print()
    
    # 테스트 질문
    test_question = "제5조는 무엇에 관한 조항인가요?"
    
    # 다양한 타임아웃으로 테스트
    timeouts = [10, 30, 60, 120]
    
    for timeout in timeouts:
        print(f"\n🔍 타임아웃 {timeout}초 테스트")
        print("-" * 30)
        
        success = test_timeout(test_question, timeout)
        
        if success:
            print(f"✅ 타임아웃 {timeout}초로 성공!")
            break
        else:
            print(f"❌ 타임아웃 {timeout}초로 실패")
        
        time.sleep(2)  # 요청 간 지연
    
    print("\n🎉 테스트 완료!")

if __name__ == "__main__":
    main()
