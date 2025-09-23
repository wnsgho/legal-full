#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 TXT 질문 파일을 JSON 형식으로 변환하는 완전한 스크립트
"""

import json
import re
from typing import Dict, List, Any
from pathlib import Path

class CompleteQuestionConverter:
    def __init__(self, input_file: str = None, output_file: str = None):
        self.input_file = input_file
        self.output_file = output_file or "complete_question_validate_test.json"
        self.questions_data = {
            "test_info": {
                "title": "계약서 분석 평가",
                "description": "M&A 계약서 분석을 위한 종합 평가 질문셋",
                "total_questions": 0,
                "sections": 0
            },
            "sections": []
        }
    
    def parse_from_file(self, file_path: str) -> Dict[str, Any]:
        """파일에서 텍스트를 읽어와서 파싱"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return self.parse_from_text(content)
    
    def parse_from_text(self, text_content: str) -> Dict[str, Any]:
        """텍스트 내용을 직접 파싱하여 구조화된 데이터로 변환"""
        # 섹션별로 분리
        sections = self._split_sections(text_content)
        
        current_question_id = 0
        
        for section in sections:
            section_data = self._parse_section(section, current_question_id)
            if section_data:
                self.questions_data["sections"].append(section_data)
                current_question_id += len(section_data["questions"])
        
        # 전체 정보 업데이트
        self.questions_data["test_info"]["total_questions"] = current_question_id
        self.questions_data["test_info"]["sections"] = len(self.questions_data["sections"])
        
        return self.questions_data
    
    def _split_sections(self, content: str) -> List[str]:
        """내용을 섹션별로 분리"""
        lines = content.split('\n')
        sections = []
        current_section = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('제') and '부:' in line:
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            elif current_section:
                current_section.append(line)
        
        if current_section:
            sections.append('\n'.join(current_section))
        
        print(f"발견된 섹션 수: {len(sections)}")
        return sections
    
    def _parse_section(self, section_content: str, start_question_id: int) -> Dict[str, Any]:
        """개별 섹션을 파싱"""
        lines = section_content.strip().split('\n')
        
        # 섹션 제목과 설명 추출
        section_title = ""
        section_description = ""
        section_id = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('제') and '부:' in line:
                section_title = line
                section_id = int(re.search(r'제(\d+)부', line).group(1))
                # 다음 줄이 설명인지 확인
                if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('질문'):
                    section_description = lines[i + 1].strip()
                break
        
        # 질문들 추출
        questions = self._extract_questions(section_content, start_question_id)
        
        if not questions:
            return None
            
        return {
            "section_id": section_id,
            "title": section_title,
            "description": section_description,
            "questions": questions
        }
    
    def _extract_questions(self, content: str, start_question_id: int) -> List[Dict[str, Any]]:
        """섹션에서 질문들을 추출"""
        questions = []
        
        # 질문 패턴 찾기 - 들여쓰기된 질문들
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 질문 시작 패턴 찾기
            if line.startswith('질문') and ':' in line:
                question_match = re.match(r'질문\s+(\d+):\s*(.*)', line)
                if question_match:
                    question_num = int(question_match.group(1))
                    question_text = question_match.group(2).strip()
                    
                    # 정답 찾기
                    answer_text = ""
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if next_line.startswith('정답:'):
                            answer_text = next_line[3:].strip()  # '정답:' 제거
                            i += 1
                            # 정답이 여러 줄에 걸쳐 있을 수 있음
                            while i < len(lines):
                                next_line = lines[i].strip()
                                if next_line and not next_line.startswith('질문'):
                                    answer_text += " " + next_line
                                    i += 1
                                else:
                                    break
                            break
                        elif next_line.startswith('질문'):
                            # 다음 질문을 만나면 이전 질문의 정답이 없는 것
                            i -= 1  # 다음 질문을 다시 처리하기 위해
                            break
                        i += 1
                    
                    if question_text and answer_text:
                        questions.append({
                            "question_id": start_question_id + len(questions) + 1,
                            "original_question_id": question_num,
                            "question": question_text,
                            "answer": answer_text,
                            "category": self._determine_category(question_text),
                            "difficulty": self._determine_difficulty(question_text),
                            "points": self._calculate_points(question_text)
                        })
            i += 1
        
        return questions
    
    def _determine_category(self, question_text: str) -> str:
        """질문 내용을 기반으로 카테고리 결정"""
        if any(keyword in question_text for keyword in ['독소조항', '구조적 결함', '하자담보책임']):
            return "독소조항"
        elif any(keyword in question_text for keyword in ['거래종결', '매매대금', '계약 이행', '영업일', '거래종결일']):
            return "거래종결"
        elif any(keyword in question_text for keyword in ['진술', '보증', '보장', '진술보증']):
            return "진술보증"
        elif any(keyword in question_text for keyword in ['손해배상', '분쟁', '해결', '배상', '손해']):
            return "손해배상"
        elif any(keyword in question_text for keyword in ['통지', '계약서', '일반', '계약', '조항']):
            return "일반조항"
        else:
            return "기타"
    
    def _determine_difficulty(self, question_text: str) -> str:
        """질문 내용을 기반으로 난이도 결정"""
        if any(keyword in question_text for keyword in ['종합적으로', '연계되어', '구조적', '복합적', '패턴 분석', '심층 추론']):
            return "high"
        elif any(keyword in question_text for keyword in ['정확히', '언제', '어떤', '누구', '상세 분석', '정확성']):
            return "medium"
        else:
            return "low"
    
    def _calculate_points(self, question_text: str) -> int:
        """질문 내용을 기반으로 점수 계산"""
        difficulty = self._determine_difficulty(question_text)
        if difficulty == "high":
            return 10
        elif difficulty == "medium":
            return 5
        else:
            return 3
    
    def save_json(self) -> str:
        """JSON 파일로 저장"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.questions_data, f, ensure_ascii=False, indent=2)
        
        return self.output_file
    
    def convert_from_file(self, file_path: str) -> str:
        """파일에서 변환"""
        print(f"파일 변환 시작: {file_path}")
        
        # 파일 파싱
        self.parse_from_file(file_path)
        
        # JSON 저장
        output_file = self.save_json()
        
        print(f"변환 완료: {output_file}")
        print(f"총 섹션 수: {self.questions_data['test_info']['sections']}")
        print(f"총 질문 수: {self.questions_data['test_info']['total_questions']}")
        
        return output_file
    
    def convert_from_text(self, text_content: str) -> str:
        """텍스트 내용을 직접 변환"""
        print("텍스트 내용 변환 시작")
        
        # 텍스트 파싱
        self.parse_from_text(text_content)
        
        # JSON 저장
        output_file = self.save_json()
        
        print(f"변환 완료: {output_file}")
        print(f"총 섹션 수: {self.questions_data['test_info']['sections']}")
        print(f"총 질문 수: {self.questions_data['test_info']['total_questions']}")
        
        return output_file

def main():
    """메인 실행 함수"""
    input_file = "BE/question_validate_test.txt"
    output_file = "BE/complete_question_validate_test.json"
    
    if not Path(input_file).exists():
        print(f"오류: 입력 파일을 찾을 수 없습니다: {input_file}")
        return
    
    converter = CompleteQuestionConverter(input_file, output_file)
    converter.convert_from_file(input_file)

if __name__ == "__main__":
    main()
