#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
범용 질문-답변 파서
장/부 구분을 무시하고 질문과 정답만 추출
"""

import re
import json
import os
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

@dataclass
class QuestionData:
    question_id: int
    question: str
    answer: str
    category: str = "일반"
    difficulty: str = "중간"
    points: int = 1

class UniversalQuestionParser:
    def __init__(self):
        self.questions = []
        
    def parse_file(self, file_path: str) -> List[QuestionData]:
        """파일을 파싱하여 질문-답변 쌍을 추출"""
        print(f"📖 파일 파싱 시작: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 질문 패턴들 (다양한 형식 지원)
        question_patterns = [
            r'질문\s*(\d+)\s*[:：]\s*(.+?)(?=\n\s*정답|\n\s*답변|\n\s*질문|\Z)',
            r'Q\s*(\d+)\s*[:：]\s*(.+?)(?=\n\s*정답|\n\s*답변|\n\s*Q|\Z)',
            r'(\d+)\.\s*(.+?)(?=\n\s*정답|\n\s*답변|\n\s*\d+\.|\Z)',
        ]
        
        # 답변 패턴들
        answer_patterns = [
            r'정답\s*[:：]\s*(.+?)(?=\n\s*질문|\n\s*Q|\n\s*\d+\.|\Z)',
            r'답변\s*[:：]\s*(.+?)(?=\n\s*질문|\n\s*Q|\n\s*\d+\.|\Z)',
        ]
        
        questions = []
        question_id = 1
        
        # 각 질문 패턴으로 시도
        for pattern in question_patterns:
            matches = re.finditer(pattern, content, re.DOTALL | re.MULTILINE)
            
            for match in matches:
                q_id = match.group(1) if match.group(1) else str(question_id)
                question_text = match.group(2).strip()
                
                # 질문 텍스트 정리
                question_text = re.sub(r'\n\s*', ' ', question_text)
                question_text = re.sub(r'\s+', ' ', question_text).strip()
                
                if not question_text:
                    continue
                
                # 해당 질문 다음에 오는 답변 찾기
                answer_text = self._find_answer_after_question(content, match.end())
                
                if answer_text:
                    questions.append(QuestionData(
                        question_id=int(q_id),
                        question=question_text,
                        answer=answer_text,
                        category=self._extract_category(content, match.start()),
                        difficulty=self._extract_difficulty(question_text),
                        points=self._calculate_points(question_text)
                    ))
                    question_id += 1
        
        # 질문이 없으면 더 간단한 패턴으로 시도
        if not questions:
            questions = self._parse_simple_format(content)
        
        print(f"✅ {len(questions)}개 질문 추출 완료")
        return questions
    
    def _find_answer_after_question(self, content: str, start_pos: int) -> str:
        """질문 다음에 오는 답변을 찾기"""
        remaining_content = content[start_pos:]
        
        # 답변 패턴들로 시도
        answer_patterns = [
            r'정답\s*[:：]\s*(.+?)(?=\n\s*질문|\n\s*Q|\n\s*\d+\.|\Z)',
            r'답변\s*[:：]\s*(.+?)(?=\n\s*질문|\n\s*Q|\n\s*\d+\.|\Z)',
        ]
        
        for pattern in answer_patterns:
            match = re.search(pattern, remaining_content, re.DOTALL | re.MULTILINE)
            if match:
                answer_text = match.group(1).strip()
                # 답변 텍스트 정리
                answer_text = re.sub(r'\n\s*', ' ', answer_text)
                answer_text = re.sub(r'\s+', ' ', answer_text).strip()
                return answer_text
        
        return ""
    
    def _parse_simple_format(self, content: str) -> List[QuestionData]:
        """더 간단한 형식으로 파싱 시도"""
        questions = []
        lines = content.split('\n')
        
        current_question = ""
        current_answer = ""
        question_id = 1
        in_question = False
        in_answer = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 질문 시작 감지
            if re.match(r'질문\s*\d+[:：]', line) or re.match(r'Q\s*\d+[:：]', line) or re.match(r'\d+\.', line):
                if current_question and current_answer:
                    questions.append(QuestionData(
                        question_id=question_id,
                        question=current_question.strip(),
                        answer=current_answer.strip(),
                        category="일반",
                        difficulty="중간",
                        points=1
                    ))
                    question_id += 1
                
                current_question = line
                current_answer = ""
                in_question = True
                in_answer = False
                
            # 답변 시작 감지
            elif re.match(r'정답[:：]', line) or re.match(r'답변[:：]', line):
                current_answer = line
                in_question = False
                in_answer = True
                
            # 내용 추가
            elif in_question:
                current_question += " " + line
            elif in_answer:
                current_answer += " " + line
        
        # 마지막 질문-답변 쌍 추가
        if current_question and current_answer:
            questions.append(QuestionData(
                question_id=question_id,
                question=current_question.strip(),
                answer=current_answer.strip(),
                category="일반",
                difficulty="중간",
                points=1
            ))
        
        return questions
    
    def _extract_category(self, content: str, question_pos: int) -> str:
        """질문 위치를 기반으로 카테고리 추출"""
        # 질문 앞의 텍스트에서 카테고리 찾기
        before_question = content[:question_pos]
        
        # 부/장 패턴 찾기
        section_patterns = [
            r'제\d+부[:：]\s*([^(\n]+)',
            r'제\d+장[:：]\s*([^(\n]+)',
            r'(\w+)\s*분석',
            r'(\w+)\s*평가',
        ]
        
        for pattern in section_patterns:
            matches = re.findall(pattern, before_question)
            if matches:
                category = matches[-1].strip()
                return category[:20]  # 길이 제한
        
        return "일반"
    
    def _extract_difficulty(self, question_text: str) -> str:
        """질문 텍스트를 기반으로 난이도 추정"""
        difficulty_keywords = {
            '고난도': ['종합적', '심층', '구조적', '연계', '복합', '고급'],
            '중간': ['분석', '검토', '평가', '확인'],
            '쉬움': ['무엇', '언제', '얼마', '어떤', '누구']
        }
        
        question_lower = question_text.lower()
        
        for difficulty, keywords in difficulty_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return difficulty
        
        return "중간"
    
    def _calculate_points(self, question_text: str) -> int:
        """질문 텍스트를 기반으로 점수 계산"""
        if any(keyword in question_text for keyword in ['종합적', '심층', '구조적', '연계']):
            return 3
        elif any(keyword in question_text for keyword in ['분석', '검토', '평가']):
            return 2
        else:
            return 1
    
    def save_to_json(self, questions: List[QuestionData], output_file: str):
        """질문들을 JSON 파일로 저장"""
        data = {
            "metadata": {
                "total_questions": len(questions),
                "categories": list(set(q.category for q in questions)),
                "difficulties": list(set(q.difficulty for q in questions)),
                "total_points": sum(q.points for q in questions)
            },
            "questions": []
        }
        
        for q in questions:
            data["questions"].append({
                "question_id": q.question_id,
                "question": q.question,
                "answer": q.answer,
                "category": q.category,
                "difficulty": q.difficulty,
                "points": q.points
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 JSON 파일 저장 완료: {output_file}")

def main():
    """메인 함수"""
    parser = UniversalQuestionParser()
    
    # questionset 폴더의 모든 txt 파일 처리
    questionset_dir = "questionset"
    if not os.path.exists(questionset_dir):
        print(f"❌ {questionset_dir} 폴더를 찾을 수 없습니다.")
        return
    
    txt_files = [f for f in os.listdir(questionset_dir) if f.endswith('.txt')]
    
    if not txt_files:
        print(f"❌ {questionset_dir} 폴더에 txt 파일이 없습니다.")
        return
    
    print(f"📁 {len(txt_files)}개 파일 발견: {txt_files}")
    
    for txt_file in txt_files:
        input_path = os.path.join(questionset_dir, txt_file)
        output_file = txt_file.replace('.txt', '_questions.json')
        
        try:
            questions = parser.parse_file(input_path)
            if questions:
                parser.save_to_json(questions, output_file)
                print(f"✅ {txt_file} → {output_file} 변환 완료")
            else:
                print(f"⚠️ {txt_file}: 질문을 찾을 수 없습니다.")
        except Exception as e:
            print(f"❌ {txt_file} 처리 중 오류: {e}")

if __name__ == "__main__":
    main()




