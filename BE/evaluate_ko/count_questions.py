#!/usr/bin/env python3
import re

def count_questions(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # "질문 \d+:" 패턴으로 질문 찾기
    questions = re.findall(r'질문 \d+:', content)
    
    print(f"파일: {file_path}")
    print(f"정확한 질문 개수: {len(questions)}")
    
    if questions:
        # 질문 번호 추출
        question_numbers = [int(q.split()[1][:-1]) for q in questions]
        print(f"질문 번호 범위: {min(question_numbers)} - {max(question_numbers)}")
        
        # 누락된 번호가 있는지 확인
        expected = set(range(min(question_numbers), max(question_numbers) + 1))
        actual = set(question_numbers)
        missing = expected - actual
        
        if missing:
            print(f"누락된 질문 번호: {sorted(missing)}")
        else:
            print("모든 질문 번호가 연속적으로 존재합니다.")
    
    return len(questions)

if __name__ == "__main__":
    count_questions("questionset/question_C4.txt")
