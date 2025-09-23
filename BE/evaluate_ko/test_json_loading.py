#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 파일 로딩 테스트
"""

import json
import sys
import os

# auto_evaluation.py의 load_questions 함수를 가져오기 위해 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_evaluation import AutoEvaluator

def test_json_loading():
    """JSON 파일 로딩 테스트"""
    evaluator = AutoEvaluator()
    
    # 새로운 형식 테스트
    print("📖 새로운 형식 JSON 파일 로딩 테스트:")
    questions = evaluator.load_questions("question_C1_questions.json")
    
    if questions:
        print(f"✅ 성공: {len(questions)}개 질문 로드됨")
        print(f"첫 번째 질문: {questions[0]['question'][:50]}...")
        print(f"첫 번째 답변: {questions[0]['answer'][:50]}...")
    else:
        print("❌ 실패: 질문을 로드할 수 없음")
    
    # 다른 파일들도 테스트
    test_files = [
        "question_C2_questions.json",
        "question_C3_questions.json", 
        "question_C4_questions.json",
        "question_C5_questions.json"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n📖 {test_file} 테스트:")
            questions = evaluator.load_questions(test_file)
            if questions:
                print(f"✅ 성공: {len(questions)}개 질문 로드됨")
            else:
                print("❌ 실패: 질문을 로드할 수 없음")

if __name__ == "__main__":
    test_json_loading()




