#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 위험 분석 결과에 위험 조항 필드 추가
"""

import json
import re
from pathlib import Path

def extract_risk_clauses_from_analysis(analysis_text: str, relevant_clauses: list) -> list:
    """분석 텍스트에서 위험 조항 추출"""
    risk_clauses = []
    
    # 분석 내용에서 조항 번호 패턴 찾기 (예: "제19조", "제39조" 등)
    clause_patterns = re.findall(r'제\d+조', analysis_text)
    
    # 관련 조항에서 해당 조항들 찾기
    for clause in relevant_clauses:
        for pattern in clause_patterns:
            if pattern in clause:
                if clause not in risk_clauses:
                    risk_clauses.append(clause)
    
    return risk_clauses

def add_risk_clauses_to_results():
    """기존 분석 결과에 위험 조항 추가"""
    data_file = Path("riskAnalysis/data/risk_analysis_results.json")
    
    if not data_file.exists():
        print("❌ 분석 결과 파일이 없습니다.")
        return
    
    # 기존 데이터 로드
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📁 로드된 분석 결과: {len(data)}개")
    
    # 각 분석 결과에 위험 조항 추가
    for analysis_id, result in data.items():
        print(f"🔍 처리 중: {analysis_id}")
        
        if 'analysis_result' in result and 'part_results' in result['analysis_result']:
            for part in result['analysis_result']['part_results']:
                # 위험 조항 추출
                risk_clauses = []
                
                if 'checklist_results' in part:
                    for checklist_item in part['checklist_results']:
                        # 위험도가 높은 항목들 (3점 이상)에서 관련 조항 추출
                        if checklist_item.get("risk_score", 0) >= 3:
                            analysis_text = checklist_item.get("analysis", "")
                            relevant_clauses = part.get("relevant_clauses", [])
                            
                            # relevant_clauses가 객체인 경우 clause 필드 추출
                            if relevant_clauses and isinstance(relevant_clauses[0], dict):
                                clause_texts = [clause.get("clause", "") for clause in relevant_clauses]
                            else:
                                clause_texts = relevant_clauses
                            
                            extracted_clauses = extract_risk_clauses_from_analysis(analysis_text, clause_texts)
                            risk_clauses.extend(extracted_clauses)
                
                # 중복 제거
                risk_clauses = list(set(risk_clauses))
                part['risk_clauses'] = risk_clauses
                
                print(f"  📋 Part {part.get('part_number', 'N/A')}: {len(risk_clauses)}개 위험 조항 추출")
    
    # 수정된 데이터 저장
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("✅ 위험 조항 추가 완료!")

if __name__ == "__main__":
    add_risk_clauses_to_results()
