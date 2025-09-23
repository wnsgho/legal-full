#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
모든 질문 파일을 일괄 변환하는 스크립트
"""

import os
import json
from universal_question_parser import UniversalQuestionParser

def batch_convert_all():
    """모든 질문 파일을 일괄 변환"""
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
    print("=" * 60)
    
    all_questions = []
    total_questions = 0
    
    for i, txt_file in enumerate(sorted(txt_files), 1):
        input_path = os.path.join(questionset_dir, txt_file)
        output_file = txt_file.replace('.txt', '_questions.json')
        
        print(f"\n[{i}/{len(txt_files)}] {txt_file} 처리 중...")
        
        try:
            questions = parser.parse_file(input_path)
            if questions:
                parser.save_to_json(questions, output_file)
                all_questions.extend(questions)
                total_questions += len(questions)
                print(f"✅ {txt_file} → {output_file} 변환 완료 ({len(questions)}개 질문)")
            else:
                print(f"⚠️ {txt_file}: 질문을 찾을 수 없습니다.")
        except Exception as e:
            print(f"❌ {txt_file} 처리 중 오류: {e}")
    
    # 전체 통합 파일 생성
    if all_questions:
        print(f"\n📊 전체 통합 파일 생성 중...")
        create_combined_file(all_questions, total_questions)
    
    print(f"\n🎉 변환 완료! 총 {total_questions}개 질문 처리됨")

def create_combined_file(all_questions, total_questions):
    """전체 질문을 하나의 통합 파일로 생성"""
    # 질문 ID 재정렬
    for i, q in enumerate(all_questions, 1):
        q.question_id = i
    
    # 카테고리별 통계
    categories = {}
    difficulties = {}
    total_points = 0
    
    for q in all_questions:
        categories[q.category] = categories.get(q.category, 0) + 1
        difficulties[q.difficulty] = difficulties.get(q.difficulty, 0) + 1
        total_points += q.points
    
    data = {
        "metadata": {
            "total_questions": total_questions,
            "total_files": len(set(q.question_id for q in all_questions if hasattr(q, 'source_file'))),
            "categories": list(categories.keys()),
            "difficulties": list(difficulties.keys()),
            "total_points": total_points,
            "category_stats": categories,
            "difficulty_stats": difficulties
        },
        "questions": []
    }
    
    for q in all_questions:
        data["questions"].append({
            "question_id": q.question_id,
            "question": q.question,
            "answer": q.answer,
            "category": q.category,
            "difficulty": q.difficulty,
            "points": q.points
        })
    
    output_file = "all_questions_combined.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 통합 파일 생성 완료: {output_file}")
    print(f"   총 질문 수: {total_questions}")
    print(f"   카테고리: {len(categories)}개")
    print(f"   난이도: {len(difficulties)}개")
    print(f"   총 점수: {total_points}")

if __name__ == "__main__":
    batch_convert_all()




