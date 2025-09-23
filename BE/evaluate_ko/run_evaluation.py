#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
평가 실행을 위한 간편한 스크립트
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
    """간편한 평가 실행"""
    print("🚀 자동 평가 시스템")
    print("="*50)
    
    # 기본 설정
    api_url = "http://localhost:8000"
    input_file = "complete_question_validate_test.json"
    output_file = f"evaluation_results_{os.path.basename(input_file).replace('.json', '')}.json"
    
    # 파일 존재 확인
    if not os.path.exists(input_file):
        print(f"❌ 입력 파일을 찾을 수 없습니다: {input_file}")
        print("먼저 complete_txt_to_json_converter.py를 실행하여 JSON 파일을 생성하세요.")
        return
    
    print(f"📁 입력 파일: {input_file}")
    print(f"📁 출력 파일: {output_file}")
    print(f"🌐 API URL: {api_url}")
    print()
    
    # 사용자 확인
    try:
        max_questions = input("평가할 질문 수 (전체: Enter, 일부: 숫자 입력): ").strip()
        max_questions = int(max_questions) if max_questions else None
        
        start_from = input("시작 질문 번호 (0부터, 기본값: 0): ").strip()
        start_from = int(start_from) if start_from else 0
        
        delay = input("요청 간 지연 시간(초, 기본값: 1.0): ").strip()
        delay = float(delay) if delay else 1.0
        
    except (ValueError, KeyboardInterrupt):
        print("❌ 잘못된 입력입니다. 기본값을 사용합니다.")
        max_questions = None
        start_from = 0
        delay = 1.0
    
    print(f"\n📊 설정:")
    print(f"  - 최대 질문 수: {max_questions or '전체'}")
    print(f"  - 시작 질문: {start_from}")
    print(f"  - 지연 시간: {delay}초")
    print()
    
    # 평가 실행
    evaluator = AutoEvaluator(api_base_url=api_url)
    
    try:
        results = evaluator.run_evaluation(
            json_file_path=input_file,
            max_questions=max_questions,
            start_from=start_from,
            delay_between_requests=delay
        )
        
        if results:
            evaluator.save_results(output_file)
            evaluator.print_summary()
            print(f"\n✅ 평가 완료! 결과: {output_file}")
        else:
            print("❌ 평가를 실행할 수 없습니다.")
            
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단되었습니다.")
        if evaluator.results:
            evaluator.save_results(output_file)
            print(f"💾 중간 결과가 저장되었습니다: {output_file}")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
