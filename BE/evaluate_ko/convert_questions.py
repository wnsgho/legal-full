#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
간단한 질문 변환 실행 스크립트
사용법: python convert_questions.py [입력파일] [출력파일]
"""

import sys
from complete_txt_to_json_converter import CompleteQuestionConverter

def main():
    """메인 실행 함수"""
    # 명령행 인수 처리
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
    else:
        input_file = "question_validate_test.txt"
    
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = input_file.replace('.txt', '.json')
    
    print(f"입력 파일: {input_file}")
    print(f"출력 파일: {output_file}")
    print("-" * 50)
    
    # 변환 실행
    converter = CompleteQuestionConverter(input_file, output_file)
    converter.convert_from_file(input_file)
    
    print("-" * 50)
    print("변환 완료!")

if __name__ == "__main__":
    main()
