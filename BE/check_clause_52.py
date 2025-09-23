#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
제52조가 데이터베이스에 존재하는지 확인하는 스크립트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# .env 파일 로드
load_dotenv()

# 환경변수가 없으면 기본값 사용
if not os.getenv('NEO4J_URI'):
    os.environ['NEO4J_URI'] = 'neo4j://127.0.0.1:7687'
    os.environ['NEO4J_USER'] = 'neo4j'
    os.environ['NEO4J_PASSWORD'] = 'password'
    os.environ['NEO4J_DATABASE'] = 'neo4j'

def check_clause_52():
    """제52조가 데이터베이스에 존재하는지 확인"""
    
    # Neo4j 연결 설정
    neo4j_uri = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
    neo4j_database = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    print(f"Neo4j 연결: {neo4j_uri}")
    print(f"데이터베이스: {neo4j_database}")
    
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        with driver.session(database=neo4j_database) as session:
            # 1. 제52조 검색
            print("\n=== 제52조 검색 결과 ===")
            result = session.run('MATCH (t:Text) WHERE t.text CONTAINS "제52조" RETURN t.text as text LIMIT 5')
            records = list(result)
            if records:
                for i, record in enumerate(records, 1):
                    print(f"{i}. {record['text'][:200]}...")
            else:
                print("제52조를 찾을 수 없습니다.")
            
            # 2. 52조 검색 (제 없이)
            print("\n=== 52조 검색 결과 ===")
            result = session.run('MATCH (t:Text) WHERE t.text CONTAINS "52조" RETURN t.text as text LIMIT 5')
            records = list(result)
            if records:
                for i, record in enumerate(records, 1):
                    print(f"{i}. {record['text'][:200]}...")
            else:
                print("52조를 찾을 수 없습니다.")
            
            # 3. 모든 조항 번호 확인
            print("\n=== 조항 번호들 ===")
            result = session.run('MATCH (t:Text) WHERE t.text CONTAINS "제" AND t.text CONTAINS "조" RETURN DISTINCT t.text as text LIMIT 50')
            records = list(result)
            
            import re
            all_clauses = set()
            for record in records:
                text = record['text']
                clauses = re.findall(r'제\d+조', text)
                all_clauses.update(clauses)
                if clauses:
                    print(f"텍스트에서 발견된 조항: {clauses} - {text[:100]}...")
            
            if all_clauses:
                sorted_clauses = sorted(all_clauses, key=lambda x: int(re.findall(r'\d+', x)[0]))
                print(f"발견된 조항들: {sorted_clauses}")
                
                # 52조가 있는지 확인
                if '제52조' in all_clauses:
                    print("✅ 제52조가 데이터베이스에 존재합니다!")
                else:
                    print("❌ 제52조가 데이터베이스에 존재하지 않습니다.")
            else:
                print("조항을 찾을 수 없습니다.")
            
            # 4. 전체 Text 노드 수 확인
            result = session.run('MATCH (t:Text) RETURN count(t) as count')
            count = result.single()['count']
            print(f"\n전체 Text 노드 수: {count}")
            
        driver.close()
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_clause_52()