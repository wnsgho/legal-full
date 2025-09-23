#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
변환된 JSON 파일들 확인
"""

import json
import os

def check_converted_files():
    """변환된 파일들을 확인"""
    json_files = [f for f in os.listdir('.') if f.endswith('_questions.json')]
    
    print(f"📁 변환된 파일 수: {len(json_files)}")
    
    for json_file in sorted(json_files):
        print(f"\n📖 {json_file} 확인:")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data['metadata']
            print(f"  총 질문 수: {metadata['total_questions']}")
            print(f"  카테고리: {metadata['categories']}")
            print(f"  난이도: {metadata['difficulties']}")
            print(f"  총 점수: {metadata['total_points']}")
            
            # 첫 번째 질문 샘플
            if data['questions']:
                first_q = data['questions'][0]
                print(f"  첫 번째 질문 ID: {first_q['question_id']}")
                print(f"  질문: {first_q['question'][:100]}...")
                print(f"  답변: {first_q['answer'][:100]}...")
                print(f"  카테고리: {first_q['category']}")
                print(f"  난이도: {first_q['difficulty']}")
                print(f"  점수: {first_q['points']}")
            
        except Exception as e:
            print(f"  ❌ 오류: {e}")

if __name__ == "__main__":
    check_converted_files()




