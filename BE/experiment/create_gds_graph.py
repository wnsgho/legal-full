#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GDS 그래프 프로젝션을 생성하는 스크립트
"""

import os
import sys
from configparser import ConfigParser
from neo4j import GraphDatabase
from graphdatascience import GraphDataScience

def create_gds_graph():
    """GDS 그래프 프로젝션 생성"""
    try:
        print("🔄 GDS 그래프 프로젝션 생성 시작...")
        
        # 설정 로드
        config = ConfigParser()
        config.read('../config.ini', encoding='utf-8')
        
        neo4j_uri = os.getenv('NEO4J_URI', config.get('urls', 'NEO4J_URI', fallback='neo4j://127.0.0.1:7687'))
        neo4j_user = os.getenv('NEO4J_USER', config.get('urls', 'NEO4J_USER', fallback='neo4j'))
        neo4j_password = os.getenv('NEO4J_PASSWORD', config.get('urls', 'NEO4J_PASSWORD', fallback='qwer1234'))
        neo4j_database = os.getenv('NEO4J_DATABASE', config.get('urls', 'NEO4J_DATABASE', fallback='neo4j'))
        
        print(f"🔗 Neo4j 연결 정보: {neo4j_uri} (데이터베이스: {neo4j_database})")
        
        # Neo4j 연결
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # GDS 초기화
        gds = GraphDataScience(driver, database=neo4j_database)
        
        # 기존 그래프 삭제 (있다면)
        try:
            gds.graph.drop('largekgrag_graph')
            print("🗑️ 기존 그래프 삭제 완료")
        except:
            print("ℹ️ 기존 그래프가 없습니다")
        
        # 노드 수 확인
        with driver.session(database=neo4j_database) as session:
            result = session.run("MATCH (n:Node) RETURN COUNT(n) as node_count")
            node_count = result.single()["node_count"]
            print(f"📊 Node 노드 수: {node_count}개")
            
            result = session.run("MATCH ()-[r:Relation]->() RETURN COUNT(r) as rel_count")
            rel_count = result.single()["rel_count"]
            print(f"📊 Relation 관계 수: {rel_count}개")
        
        if node_count == 0:
            print("❌ Node 노드가 없습니다. 먼저 Neo4j에 데이터를 임포트하세요.")
            return False
        
        # GDS 그래프 프로젝션 생성
        print("🔄 GDS 그래프 프로젝션 생성 중...")
        
        # 원래 개발자 방식: 라벨만 지정, 속성은 지정하지 않음
        graph, result = gds.graph.project(
            'largekgrag_graph',
            ['Node'],
            ['Relation']
        )
        
        print(f"✅ GDS 그래프 프로젝션 생성 완료!")
        print(f"   - 그래프 이름: {graph.name()}")
        print(f"   - 노드 수: {result['nodeCount']}")
        print(f"   - 관계 수: {result['relationshipCount']}")
        
        # 그래프 정보 확인
        print("📊 그래프 정보:")
        print(f"   - 노드 타입: {graph.node_labels()}")
        print(f"   - 관계 타입: {graph.relationship_types()}")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 GDS 그래프 프로젝션 생성 도구")
    print("=" * 60)
    
    success = create_gds_graph()
    
    if success:
        print("\n✅ GDS 그래프 프로젝션 생성 완료!")
        print("📋 이제 run_questions_v2.py를 실행할 수 있습니다.")
    else:
        print("\n❌ GDS 그래프 프로젝션 생성 실패!")
        sys.exit(1)
