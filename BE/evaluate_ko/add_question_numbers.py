#!/usr/bin/env python3
"""
질문 파일에 순차적으로 번호를 매기는 스크립트
질문 1:, 질문 2: 형태로 번호를 추가합니다.
"""

import os
import re
import argparse
from pathlib import Path

def add_question_numbers(input_file: str, output_file: str = None):
    """
    질문 파일에 순차적으로 번호를 추가합니다.
    다양한 형식을 지원합니다:
    - "질문:" → "질문 1:", "질문 2:"
    - "Q1:", "Q2:" → "질문 1:", "질문 2:"
    - "Q1:", "Q2:" (이미 번호가 있는 경우) → "질문 1:", "질문 2:"
    
    Args:
        input_file: 입력 파일 경로
        output_file: 출력 파일 경로 (None이면 원본 파일을 덮어씀)
    """
    if not os.path.exists(input_file):
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        return False
    
    # 출력 파일명 설정
    if output_file is None:
        output_file = input_file
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 질문 번호 카운터
        question_counter = 1
        
        # 1. "질문:" 패턴을 찾아서 "질문 1:", "질문 2:" 등으로 변경
        def replace_question(match):
            nonlocal question_counter
            result = f"질문 {question_counter}:"
            question_counter += 1
            return result
        
        # "질문:"을 "질문 {번호}:"로 변경
        pattern1 = r'^질문:\s*$'
        new_content = re.sub(pattern1, replace_question, content, flags=re.MULTILINE)
        
        # 2. "Q1:", "Q2:" 패턴을 찾아서 "질문 1:", "질문 2:" 등으로 변경
        def replace_q_question(match):
            nonlocal question_counter
            result = f"질문 {question_counter}:"
            question_counter += 1
            return result
        
        # "Q숫자:"를 "질문 {번호}:"로 변경 (앞에 공백이 있을 수 있음)
        pattern2 = r'^\s*Q\d+:\s*'
        new_content = re.sub(pattern2, replace_q_question, new_content, flags=re.MULTILINE)
        
        # 결과를 파일에 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 성공적으로 처리되었습니다!")
        print(f"📁 입력 파일: {input_file}")
        print(f"📁 출력 파일: {output_file}")
        print(f"🔢 총 질문 수: {question_counter - 1}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {e}")
        return False

def process_directory(directory: str, pattern: str = "question_*.txt"):
    """
    디렉토리 내의 모든 질문 파일을 처리합니다.
    
    Args:
        directory: 처리할 디렉토리 경로
        pattern: 파일 패턴 (기본값: question_*.txt)
    """
    directory_path = Path(directory)
    
    if not directory_path.exists():
        print(f"❌ 디렉토리를 찾을 수 없습니다: {directory}")
        return False
    
    # 패턴에 맞는 파일들 찾기
    files = list(directory_path.glob(pattern))
    
    if not files:
        print(f"❌ 패턴 '{pattern}'에 맞는 파일을 찾을 수 없습니다.")
        return False
    
    print(f"📁 처리할 파일 {len(files)}개를 찾았습니다:")
    for file in files:
        print(f"  - {file.name}")
    
    success_count = 0
    for file in files:
        print(f"\n🔄 처리 중: {file.name}")
        if add_question_numbers(str(file)):
            success_count += 1
    
    print(f"\n✅ 처리 완료: {success_count}/{len(files)}개 파일")
    return success_count == len(files)

def main():
    parser = argparse.ArgumentParser(
        description="질문 파일에 순차적으로 번호를 매기는 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
지원하는 형식:
  - "질문:" → "질문 1:", "질문 2:"
  - "Q1:", "Q2:" → "질문 1:", "질문 2:"
  - 앞에 공백이 있는 경우도 처리

사용 예시:
  # 단일 파일 처리
  python add_question_numbers.py question_C1.txt
  
  # 백업 파일 생성하며 처리
  python add_question_numbers.py question_C1.txt -o question_C1_numbered.txt
  
  # 디렉토리 내 모든 질문 파일 처리
  python add_question_numbers.py -d questionset/
  
  # 특정 패턴의 파일들 처리
  python add_question_numbers.py -d questionset/ -p "question_C*.txt"
        """
    )
    
    parser.add_argument('input_file', nargs='?', help='처리할 입력 파일')
    parser.add_argument('-o', '--output', help='출력 파일 경로 (지정하지 않으면 원본 파일을 덮어씀)')
    parser.add_argument('-d', '--directory', help='처리할 디렉토리 경로')
    parser.add_argument('-p', '--pattern', default='question_*.txt', help='파일 패턴 (기본값: question_*.txt)')
    
    args = parser.parse_args()
    
    if args.directory:
        # 디렉토리 처리 모드
        process_directory(args.directory, args.pattern)
    elif args.input_file:
        # 단일 파일 처리 모드
        add_question_numbers(args.input_file, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
