#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
node_list.pkl의 해시 ID를 사용하면서 concept을 속성으로 저장하는 Neo4j 임포트 스크립트
기존 fix_neo4j_with_hash_ids.py를 기반으로 concept 속성 추가
"""

import os
import sys
import pickle
import csv
import pandas as pd
import json
import argparse
from collections import defaultdict
from configparser import ConfigParser
from neo4j import GraphDatabase

def fix_neo4j_with_hash_ids_and_concept_attributes(keyword=None):
    """node_list.pkl의 해시 ID를 사용하면서 concept을 속성으로 저장하여 Neo4j 임포트"""
    try:
        print("[INFO] node_list.pkl의 해시 ID + concept 속성을 사용해서 Neo4j 임포트 시작...")
        
        # 설정 로드
        config = ConfigParser()
        config.read('config.ini', encoding='utf-8')
        
        neo4j_uri = os.getenv('NEO4J_URI', config.get('urls', 'NEO4J_URI', fallback='neo4j://127.0.0.1:7687'))
        neo4j_user = os.getenv('NEO4J_USER', config.get('urls', 'NEO4J_USER', fallback='neo4j'))
        neo4j_password = os.getenv('NEO4J_PASSWORD', config.get('urls', 'NEO4J_PASSWORD', fallback='qwer1234'))
        neo4j_database = os.getenv('NEO4J_DATABASE', config.get('urls', 'NEO4J_DATABASE', fallback='neo4j'))
        
        # keyword 우선순위: 함수 인수 > 환경변수 > 설정파일 > 기본값
        if keyword is None:
            keyword = os.getenv('KEYWORD', config.get('data', 'KEYWORD', fallback='contract_v5'))
        
        print(f"🔗 Neo4j 연결 정보: {neo4j_uri} (데이터베이스: {neo4j_database})")
        print(f"🔑 사용할 키워드: '{keyword}' (길이: {len(keyword)})")
        
        # Neo4j 연결
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        # node_list.pkl 로드
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = script_dir
        print(f"🔍 스크립트 디렉토리: {script_dir}")
        print(f"🔍 프로젝트 루트: {project_root}")
        
        # 여러 가능한 경로에서 node_list.pkl 찾기
        possible_paths = [
            os.path.join(project_root, 'import', keyword, 'precompute', f'{keyword}_eventTrue_conceptTrue_node_list.pkl'),
            os.path.join(project_root, 'import', keyword, 'precompute', f'{keyword}_node_list.pkl'),
            os.path.join(project_root, 'import', keyword, f'{keyword}_eventTrue_conceptTrue_node_list.pkl'),
            os.path.join(project_root, 'import', keyword, f'{keyword}_node_list.pkl')
        ]
        
        node_list_path = None
        for path in possible_paths:
            print(f"🔍 경로 확인: {path}")
            print(f"🔍 존재 여부: {os.path.exists(path)}")
            if os.path.exists(path):
                node_list_path = path
                print(f"✅ 파일 발견: {path}")
                break
        
        if not node_list_path:
            print(f"[ERROR] node_list.pkl 파일을 찾을 수 없습니다. 시도한 경로들:")
            for path in possible_paths:
                print(f"  - {path}")
            return False
        
        print(f"[INFO] node_list.pkl 파일 발견: {node_list_path}")
        
        with open(node_list_path, 'rb') as f:
            node_list = pickle.load(f)
        
        print(f"[INFO] node_list.pkl 로드 완료: {len(node_list)}개 노드")
        
        # CSV 파일 로드 - 여러 가능한 경로에서 찾기
        possible_csv_paths = [
            os.path.join(project_root, 'import', keyword, 'triples_csv', f'triple_nodes_{keyword}_from_json_with_emb.csv'),
            os.path.join(project_root, 'import', keyword, 'triples_csv', f'triple_nodes_{keyword}_from_json_without_emb.csv'),
            os.path.join(project_root, 'import', keyword, 'triples_csv', f'triple_nodes_{keyword}_from_json.csv'),
            os.path.join(project_root, 'import', keyword, f'triple_nodes_{keyword}_from_json_with_emb.csv'),
            os.path.join(project_root, 'import', keyword, f'triple_nodes_{keyword}_from_json.csv')
        ]
        
        csv_path = None
        for path in possible_csv_paths:
            if os.path.exists(path):
                csv_path = path
                break
        
        if not csv_path:
            print(f"[ERROR] CSV 파일을 찾을 수 없습니다. 시도한 경로들:")
            for path in possible_csv_paths:
                print(f"  - {path}")
            return False
        
        print(f"[INFO] CSV 파일 발견: {csv_path}")
        
        # CSV에서 노드 정보 읽기
        nodes_data = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i < len(node_list):  # node_list 범위 내에서만
                    nodes_data.append({
                        'hash_id': node_list[i],  # 해시 ID
                        'name': row['name:ID'],   # 한국어 텍스트
                        'type': row['type'],
                        'concepts': row['concepts'],
                        'synsets': row['synsets']
                    })
        
        print(f"📊 CSV에서 {len(nodes_data)}개 노드 정보 로드 완료")
        
        # Concept 정보 로드 - 여러 가능한 경로에서 찾기
        possible_concept_nodes_paths = [
            os.path.join(project_root, 'import', keyword, 'concept_csv', f'concept_nodes_{keyword}_from_json_with_concept.csv'),
            os.path.join(project_root, 'import', keyword, 'concept_csv', f'concept_nodes_{keyword}_from_json.csv'),
            os.path.join(project_root, 'import', keyword, f'concept_nodes_{keyword}_from_json_with_concept.csv'),
            os.path.join(project_root, 'import', keyword, f'concept_nodes_{keyword}_from_json.csv')
        ]
        
        possible_concept_edges_paths = [
            os.path.join(project_root, 'import', keyword, 'concept_csv', f'concept_edges_{keyword}_from_json_with_concept.csv'),
            os.path.join(project_root, 'import', keyword, 'concept_csv', f'concept_edges_{keyword}_from_json.csv'),
            os.path.join(project_root, 'import', keyword, f'concept_edges_{keyword}_from_json_with_concept.csv'),
            os.path.join(project_root, 'import', keyword, f'concept_edges_{keyword}_from_json.csv')
        ]
        
        concept_nodes_file = None
        for path in possible_concept_nodes_paths:
            if os.path.exists(path):
                concept_nodes_file = path
                break
        
        concept_edges_file = None
        for path in possible_concept_edges_paths:
            if os.path.exists(path):
                concept_edges_file = path
                break
        
        # Concept ID -> Concept Name 매핑 생성
        concept_id_to_name = {}
        if os.path.exists(concept_nodes_file):
            with open(concept_nodes_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    concept_id_to_name[row['concept_id:ID']] = row['name']
        
        # 각 노드에 연결된 concept들 수집
        node_to_concepts = defaultdict(list)
        if os.path.exists(concept_edges_file):
            with open(concept_edges_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    node_text = row[':START_ID']  # START_ID가 노드 텍스트
                    concept_id = row[':END_ID']  # END_ID가 concept
                    if concept_id in concept_id_to_name:
                        concept_name = concept_id_to_name[concept_id]
                        node_to_concepts[node_text].append(concept_name)
        
        print(f"📊 {len(node_to_concepts)}개 노드의 concept 매핑 완료")
        
        # Neo4j 임포트
        with driver.session(database=neo4j_database) as session:
            # 기존 데이터 삭제
            print("🗑️ 기존 데이터 삭제 중...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # Node 노드들 생성 (해시 ID + concept_list 속성)
            print("📊 Node 노드들 생성 중...")
            for i, node_data in enumerate(nodes_data):
                # 해당 노드의 concept들 수집
                concepts = node_to_concepts.get(node_data['name'], [])
                concept_list = json.dumps(concepts, ensure_ascii=False)
                
                session.run("""
                    CREATE (n:Node {
                        id: $hash_id,
                        name: $name,
                        type: $type,
                        concepts: $concepts,
                        synsets: $synsets,
                        concept_list: $concept_list,
                        numeric_id: $numeric_id
                    })
                """, 
                hash_id=node_data['hash_id'],
                name=node_data['name'],
                type=node_data['type'],
                concepts=node_data['concepts'],
                synsets=node_data['synsets'],
                concept_list=concept_list,
                numeric_id=i  # CSV 순서대로 numeric_id 할당
                )
            
            # Text 노드들 생성
            print("[INFO] Text 노드들 생성 중...")
            possible_text_paths = [
                os.path.join(project_root, 'import', keyword, 'triples_csv', f'text_nodes_{keyword}_from_json_with_numeric_id.csv'),
                os.path.join(project_root, 'import', keyword, 'triples_csv', f'text_nodes_{keyword}_from_json_with_emb.csv'),
                os.path.join(project_root, 'import', keyword, 'triples_csv', f'text_nodes_{keyword}_from_json.csv'),
                os.path.join(project_root, 'import', keyword, f'text_nodes_{keyword}_from_json_with_numeric_id.csv'),
                os.path.join(project_root, 'import', keyword, f'text_nodes_{keyword}_from_json.csv')
            ]
            
            text_csv_path = None
            for path in possible_text_paths:
                if os.path.exists(path):
                    text_csv_path = path
                    break
            
            if text_csv_path:
                text_df = pd.read_csv(text_csv_path, encoding='utf-8')
                for i, row in text_df.iterrows():
                    session.run("""
                        CREATE (t:Text {
                            id: $text_id,
                            text_id: $text_id,
                            text: $text,
                            numeric_id: $numeric_id
                        })
                    """, 
                    text_id=row['text_id:ID'],
                    text=row['original_text'],
                    numeric_id=row['numeric_id']
                    )
                print(f"[SUCCESS] 생성된 Text 노드 수: {len(text_df)}개")
            else:
                print(f"[ERROR] Text CSV 파일을 찾을 수 없습니다: {text_csv_path}")
            
            # Source 관계 생성 (Node -> Text)
            print("[INFO] Source 관계 생성 중...")
            source_count = 0
            possible_source_paths = [
                os.path.join(project_root, 'import', keyword, 'triples_csv', f'text_edges_{keyword}_from_json.csv'),
                os.path.join(project_root, 'import', keyword, f'text_edges_{keyword}_from_json.csv')
            ]
            
            source_csv_path = None
            for path in possible_source_paths:
                if os.path.exists(path):
                    source_csv_path = path
                    break
            
            if source_csv_path:
                with open(source_csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        node_name = row[':START_ID']
                        text_id = row[':END_ID']
                        
                        # Node와 Text 찾기
                        node_result = session.run("MATCH (n:Node) WHERE n.name = $name RETURN n.id as id", name=node_name)
                        text_result = session.run("MATCH (t:Text) WHERE t.text_id = $text_id RETURN t.id as id", text_id=text_id)
                        
                        node_record = node_result.single()
                        text_record = text_result.single()
                        
                        if node_record and text_record:
                            session.run("""
                                MATCH (n:Node {id: $node_id})
                                MATCH (t:Text {id: $text_id})
                                CREATE (n)-[:Source]->(t)
                            """, 
                            node_id=node_record['id'],
                            text_id=text_record['id']
                            )
                            source_count += 1
                
                print(f"[SUCCESS] 생성된 Source 관계 수: {source_count}개")
            else:
                print(f"[ERROR] Source CSV 파일을 찾을 수 없습니다: {source_csv_path}")
            
            # Relation 관계 생성
            print("[INFO] Relation 관계 생성 중...")
            relation_count = 0
            
            # triple_edges CSV 파일에서 관계 생성
            possible_edges_paths = [
                os.path.join(project_root, 'import', keyword, 'triples_csv', f'triple_edges_{keyword}_from_json_without_emb_with_numeric_id.csv'),
                os.path.join(project_root, 'import', keyword, 'triples_csv', f'triple_edges_{keyword}_from_json_with_concept_with_emb.csv'),
                os.path.join(project_root, 'import', keyword, 'triples_csv', f'triple_edges_{keyword}_from_json_with_concept.csv'),
                os.path.join(project_root, 'import', keyword, 'triples_csv', f'triple_edges_{keyword}_from_json_without_emb.csv'),
                os.path.join(project_root, 'import', keyword, 'triples_csv', f'triple_edges_{keyword}_from_json.csv'),
                os.path.join(project_root, 'import', keyword, f'triple_edges_{keyword}_from_json_without_emb_with_numeric_id.csv'),
                os.path.join(project_root, 'import', keyword, f'triple_edges_{keyword}_from_json.csv')
            ]
            
            edges_csv_path = None
            for path in possible_edges_paths:
                if os.path.exists(path):
                    edges_csv_path = path
                    break
            
            if edges_csv_path:
                with open(edges_csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        start_name = row[':START_ID']
                        end_name = row[':END_ID']
                        relation = row.get('relation', '')
                        concepts = row.get('concepts', '')
                        synsets = row.get('synsets', '')
                        
                        # 관계의 concept 정보도 수집
                        start_concepts = node_to_concepts.get(start_name, [])
                        end_concepts = node_to_concepts.get(end_name, [])
                        all_concepts = list(set(start_concepts + end_concepts))
                        concept_list = json.dumps(all_concepts, ensure_ascii=False)
                        
                        # 시작 노드와 끝 노드 찾기
                        start_result = session.run("MATCH (n:Node) WHERE n.name = $name RETURN n.id as id", name=start_name)
                        end_result = session.run("MATCH (n:Node) WHERE n.name = $name RETURN n.id as id", name=end_name)
                        
                        start_record = start_result.single()
                        end_record = end_result.single()
                        
                        if start_record and end_record:
                            session.run("""
                                MATCH (n1:Node {id: $start_id})
                                MATCH (n2:Node {id: $end_id})
                                CREATE (n1)-[:Relation {
                                    relation: $relation,
                                    concepts: $concepts,
                                    synsets: $synsets,
                                    concept_list: $concept_list,
                                    numeric_id: $numeric_id
                                }]->(n2)
                            """, 
                            start_id=start_record['id'],
                            end_id=end_record['id'],
                            relation=relation,
                            concepts=concepts,
                            synsets=synsets,
                            concept_list=concept_list,
                            numeric_id=row.get('numeric_id', 0)
                            )
                            relation_count += 1
                
                print(f"[SUCCESS] 생성된 Relation 관계 수: {relation_count}개")
            else:
                print(f"[ERROR] Relation CSV 파일을 찾을 수 없습니다: {edges_csv_path}")
            
            # 결과 확인
            print("📊 결과 확인 중...")
            result = session.run("MATCH (n:Node) RETURN count(n) as node_count")
            node_count = result.single()["node_count"]
            print(f"[SUCCESS] 생성된 Node 노드 수: {node_count}개")
            
            result = session.run("MATCH ()-[r:Relation]->() RETURN count(r) as rel_count")
            rel_count = result.single()["rel_count"]
            print(f"[SUCCESS] 생성된 Relation 관계 수: {rel_count}개")
            
            result = session.run("MATCH ()-[r:Source]->() RETURN count(r) as source_count")
            source_count = result.single()["source_count"]
            print(f"[SUCCESS] 생성된 Source 관계 수: {source_count}개")
            
            # concept_list가 있는 노드 수 확인
            result = session.run("""
                MATCH (n:Node) 
                WHERE n.concept_list IS NOT NULL AND n.concept_list <> '[]' AND n.concept_list <> 'null'
                RETURN count(n) as concept_nodes
            """)
            concept_nodes = result.single()["concept_nodes"]
            print(f"[SUCCESS] concept_list가 있는 노드 수: {concept_nodes}개")
            
            # 첫 번째 노드 확인
            result = session.run("MATCH (n:Node) RETURN n.id as id, n.name as name, n.concept_list as concept_list LIMIT 1")
            first_node = result.single()
            if first_node:
                print(f"🔍 첫 번째 노드: id={first_node['id'][:20]}..., name={first_node['name']}, concept_list={first_node['concept_list']}")
        
        driver.close()
        print("[SUCCESS] Neo4j 임포트 완료!")
        return True
        
    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("해시 ID + concept 속성을 사용한 Neo4j 임포트 도구")
    print("=" * 60)
    
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(description='Neo4j 임포트 도구')
    parser.add_argument('--keyword', '-k', type=str, help='사용할 키워드 (예: contract_ff8fad8c-e7d1-44b3-8dae-64d75e90deb6)')
    args = parser.parse_args()
    
    success = fix_neo4j_with_hash_ids_and_concept_attributes(keyword=args.keyword)
    
    if success:
        print("\n[SUCCESS] 작업 완료!")
        print("📋 concept이 노드 속성으로 저장되었습니다!")
    else:
        print("\n[ERROR] 작업 실패!")
        sys.exit(1)