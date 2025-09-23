#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
빠른 테스트를 위한 스크립트 (5개 질문만 평가)
"""

import os
import sys
import io
from pathlib import Path

# Windows에서 UTF-8 출력을 위한 설정
if sys.platform.startswith('win'):
    # stdout과 stderr을 UTF-8로 설정
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from auto_evaluation import AutoEvaluator

def main():
    """빠른 테스트 실행"""
    print("🧪 빠른 테스트 (5개 질문)")
    print("="*40)
    
    # 설정
    api_url = "http://localhost:8000"
    input_file = "complete_question_validate_test.json"
    output_file = "quick_test_results.json"
    
    # 파일 존재 확인
    if not os.path.exists(input_file):
        print(f"❌ 입력 파일을 찾을 수 없습니다: {input_file}")
        print("먼저 complete_txt_to_json_converter.py를 실행하여 JSON 파일을 생성하세요.")
        return
    
    print(f"📁 입력 파일: {input_file}")
    print(f"📁 출력 파일: {output_file}")
    print(f"🌐 API URL: {api_url}")
    print(f"📊 테스트 질문 수: 5개")
    print()
    
    # API 연결 테스트
    evaluator = AutoEvaluator(api_base_url=api_url)
    if not evaluator.test_api_connection():
        print("❌ API 서버에 연결할 수 없습니다.")
        print("먼저 'python server.py'로 API 서버를 실행하세요.")
        return
    
    # 평가 실행
    try:
        results = evaluator.run_evaluation(
            json_file_path=input_file,
            max_questions=5,  # 5개만 테스트
            start_from=0,
            delay_between_requests=0.5  # 빠른 테스트를 위해 지연 시간 단축
        )
        
        if results:
            evaluator.save_results(output_file)
            evaluator.print_summary()
            print(f"\n✅ 테스트 완료! 결과: {output_file}")
        else:
            print("❌ 테스트를 실행할 수 없습니다.")
            
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
