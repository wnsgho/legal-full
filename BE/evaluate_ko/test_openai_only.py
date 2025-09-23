#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI 전용 테스트 스크립트 검증
"""

import os
import sys
import json
from pathlib import Path

def test_environment():
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
        
        # 질문 파일 내용 확인
        try:
            with open(questions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            questions = data.get("questions", [])
            print(f"   - 질문 수: {len(questions)}")
            if questions:
                print(f"   - 첫 번째 질문: {questions[0].get('question', '')[:50]}...")
        except Exception as e:
            print(f"   - 질문 파일 읽기 오류: {e}")
            return False
    
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

def test_script_import():
    """
    스크립트 import를 테스트합니다.
    """
    print("\n🧪 스크립트 import 테스트...")
    
    try:
        # openai_only_test.py import 테스트
        sys.path.append('.')
        from openai_only_test import OpenAITester
        print("✅ OpenAITester 클래스 import 성공")
        
        # OpenAI 클라이언트 초기화 테스트
        tester = OpenAITester()
        print("✅ OpenAITester 인스턴스 생성 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ 스크립트 import 실패: {e}")
        return False

def test_simple_question():
    """
    간단한 질문으로 테스트합니다.
    """
    print("\n🧪 간단한 질문 테스트...")
    
    try:
        from openai_only_test import OpenAITester
        
        # 테스트용 간단한 문서와 질문
        test_document = """
        제1조 (목적)
        이 계약은 매수인과 매도인 간의 부동산 매매에 관한 사항을 규정한다.
        
        제2조 (매매대금)
        매매대금은 5억원으로 한다.
        """
        
        test_question = "매매대금은 얼마입니까?"
        
        tester = OpenAITester()
        result = tester.get_openai_answer(test_question, test_document)
        
        if result["success"]:
            print("✅ OpenAI API 호출 성공")
            print(f"   답변: {result['answer'][:100]}...")
            print(f"   처리시간: {result['processing_time']:.2f}초")
            print(f"   토큰 사용량: {result['tokens_used']:,}")
            return True
        else:
            print(f"❌ OpenAI API 호출 실패: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ 간단한 질문 테스트 실패: {e}")
        return False

def main():
    """
    메인 테스트 함수
    """
    print("🚀 OpenAI 전용 테스트 스크립트 검증")
    print("="*50)
    
    # 환경 설정 확인
    env_ok = test_environment()
    
    # 스크립트 import 테스트
    import_ok = test_script_import()
    
    # 간단한 질문 테스트
    api_ok = test_simple_question()
    
    # 결과 요약
    print("\n" + "="*50)
    print("테스트 결과 요약")
    print("="*50)
    print(f"환경 설정: {'✅' if env_ok else '❌'}")
    print(f"스크립트 import: {'✅' if import_ok else '❌'}")
    print(f"OpenAI API: {'✅' if api_ok else '❌'}")
    
    if env_ok and import_ok and api_ok:
        print("\n🎉 모든 테스트가 성공했습니다!")
        print("이제 OpenAI 전용 테스트를 실행할 수 있습니다.")
        print("\n사용 예시:")
        print("python openai_only_test.py --questions question_C1_questions.json --document ../uploads/contract_01.md --max-questions 3")
    else:
        print("\n⚠️  일부 테스트가 실패했습니다.")
        print("문제를 해결한 후 다시 시도하세요.")

if __name__ == "__main__":
    main()
