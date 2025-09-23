#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Concept 활용 LKG 우선 검색 + HiPPO-RAG2 + LKG 여러 조항 검색 하이브리드 RAG 질문 실행 스크립트
Concept을 활용하여 검색 정확도를 향상시킵니다.

=============================================================================
서버 배포 시 수정 필요 사항:
=============================================================================
1. 상대 import → 절대 import 변경 (완료)
   - from ..atlas_rag... → from atlas_rag...

2. 실행 경로 설정
   - 현재: BE/experiment/ 디렉토리에서 실행
   - 서버: 프로젝트 루트에서 python -m BE.experiment.run_questions_v3_with_concept.py

3. 환경변수 설정 확인
   - .env 파일 경로 확인
   - Neo4j 연결 설정 확인
   - OpenRouter API 설정 확인
=============================================================================
"""

import os
import sys
import time
import json
import re
import warnings
import logging
from datetime import datetime
from pathlib import Path
from collections import Counter

# 서버 배포 시 Python 경로 설정
if __name__ == "__main__":
    # 현재 스크립트의 디렉토리에서 BE 디렉토리 찾기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    be_dir = os.path.join(current_dir, '..')
    if be_dir not in sys.path:
        sys.path.insert(0, be_dir)
import numpy as np
from dotenv import load_dotenv

# 불필요한 로그 억제
warnings.filterwarnings("ignore")
logging.getLogger("faiss.loader").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("nltk").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# .env 파일 로드 (서버 실행 시 경로 수정)
def load_env_file():
    """서버와 직접 실행 모두에서 .env 파일을 찾아서 로드"""
    # 현재 스크립트의 디렉토리에서 BE 디렉토리 찾기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    be_dir = os.path.join(current_dir, '..')
    
    # .env 파일 경로들 시도
    env_paths = [
        os.path.join(be_dir, '.env'),  # BE/.env
        '.env',                        # 현재 디렉토리
        '../.env'                      # 상위 디렉토리
    ]
    
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"✅ .env 파일 로드 성공: {env_path}")
            return True
    
    print("⚠️ .env 파일을 찾을 수 없습니다.")
    return False

# .env 파일 로드
load_env_file()

def load_enhanced_rag_system():
    """향상된 LKG 리트라이버 + HippoRAG2Retriever 하이브리드 RAG 시스템 로드"""
    print("🚀 load_enhanced_rag_system() 함수 시작")
    
    # 디버깅 정보 출력
    import os
    print(f"📁 현재 작업 디렉토리: {os.getcwd()}")
    print(f" __file__ 경로: {__file__}")
    print(f"📁 스크립트 디렉토리: {os.path.dirname(os.path.abspath(__file__))}")
    
    try:
        from atlas_rag.retriever import HippoRAG2Retriever
        from atlas_rag.retriever.lkg_retriever.enhanced_lkgr import EnhancedLargeKGRetriever
        from atlas_rag.llm_generator import LLMGenerator
        
        # OpenAI 클라이언트 설정
        print("🤖 OpenAI 클라이언트 설정 중...")
        from openai import OpenAI
        client = OpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        )
        print("✅ OpenAI 클라이언트 설정 완료")
        
        print("🧠 LLMGenerator 생성 중...")
        llm_generator = LLMGenerator(
            client=client, 
            model_name=os.getenv('DEFAULT_MODEL', "gpt-4.1-2025-04-14"),
        )
        print("✅ LLMGenerator 생성 완료")
        
        # Neo4j 연결 설정
        from neo4j import GraphDatabase
        neo4j_uri = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        neo4j_database = os.getenv('NEO4J_DATABASE', 'neo4j')
        keyword = os.getenv('KEYWORD', 'contract_v5')
        
        print(f"🔧 환경변수 확인:")
        print(f"   - NEO4J_URI: {neo4j_uri}")
        print(f"   - NEO4J_DATABASE: {neo4j_database}")
        print(f"   - KEYWORD: {keyword}")
        
        try:
            neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            print("✅ Neo4j 연결 성공")
        except Exception as e:
            print(f"⚠️ Neo4j 연결 실패: {e}")
            neo4j_driver = None
        
        # 저장된 RAG 데이터 로드
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        import_dir = os.getenv('IMPORT_DIRECTORY', 'import')
        precompute_dir = os.getenv('PRECOMPUTE_DIRECTORY', 'precompute')
        
        print(f"📁 경로 정보:")
        print(f"   - script_dir: {script_dir}")
        print(f"   - project_root: {project_root}")
        print(f"   - import_dir: {import_dir}")
        print(f"   - precompute_dir: {precompute_dir}")
        
        data_path = os.path.join(project_root, import_dir, keyword, precompute_dir, f"{keyword}_eventTrue_conceptTrue_all-MiniLM-L6-v2_node_faiss.index")
        print(f"   - data_path: {data_path}")
        print(f"   - data_path 존재: {os.path.exists(data_path)}")
        
        if not os.path.exists(data_path):
            print("❌ 저장된 RAG 데이터를 찾을 수 없습니다.")
            print("먼저 experiment_multihop_qa.py를 실행해서 임베딩을 생성하세요.")
            return None, None, None, None
        
        # RAG 시스템 생성
        from atlas_rag.vectorstore import create_embeddings_and_index
        from sentence_transformers import SentenceTransformer
        from atlas_rag.vectorstore.embedding_model import SentenceEmbedding
        
        # 임베딩 모델 로드
        sentence_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        sentence_encoder = SentenceEmbedding(sentence_model)
        
        # RAG 데이터 생성
        data = create_embeddings_and_index(
            sentence_encoder=sentence_encoder,
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            working_directory=os.path.join(project_root, "import", keyword),
            keyword=keyword,
            include_concept=True,
            include_events=True,
            normalize_embeddings=True,
            text_batch_size=32,
            node_and_edge_batch_size=64,
        )
        
        # 데이터 구조 확인
        print(f"📊 데이터 구조:")
        # print(f"   - data 키들: {list(data.keys())}")  # 이 줄을 주석 처리하거나 삭제
        
        # FAISS 인덱스 직접 로드 (기존 방식 사용)
        enhanced_lkg_retriever = None
        hippo_retriever = None
        
        if neo4j_driver is not None:
            try:
                # FAISS 인덱스 로드
                import faiss
                node_index_path = os.path.join(project_root, import_dir, keyword, precompute_dir, f"{keyword}_eventTrue_conceptTrue_all-MiniLM-L6-v2_node_faiss.index")
                passage_index_path = os.path.join(project_root, import_dir, keyword, precompute_dir, f"{keyword}_text_faiss.index")
                
                print(f" FAISS 인덱스 경로:")
                print(f"   - node_index_path: {node_index_path}")
                print(f"   - passage_index_path: {passage_index_path}")
                print(f"   - node_index_path 존재: {os.path.exists(node_index_path)}")
                print(f"   - passage_index_path 존재: {os.path.exists(passage_index_path)}")
                
                if os.path.exists(node_index_path) and os.path.exists(passage_index_path):
                    node_index = faiss.read_index(node_index_path)
                    passage_index = faiss.read_index(passage_index_path)
                    print("✅ FAISS 인덱스 로드 성공")
                    
                    # node_list 로드
                    import pickle
                    node_list_path = os.path.join(project_root, import_dir, keyword, precompute_dir, f"{keyword}_eventTrue_conceptTrue_node_list.pkl")
                    print(f"   - node_list_path: {node_list_path}")
                    print(f"   - node_list_path 존재: {os.path.exists(node_list_path)}")
                    
                    if os.path.exists(node_list_path):
                        with open(node_list_path, "rb") as f:
                            node_list = pickle.load(f)
                        print(f"✅ node_list 로드 성공: {len(node_list)}개 노드")
                        print(f"   - node_list 첫 3개: {node_list[:3] if len(node_list) >= 3 else node_list}")
                    else:
                        print("❌ node_list 파일을 찾을 수 없습니다!")
                        node_list = []
                    
                    # print 함수를 래핑한 간단한 로거 클래스 생성
                    class PrintLogger:
                        def info(self, message):
                            print(f"[INFO] {message}")
                        def debug(self, message):
                            print(f"[DEBUG] {message}")
                        def warning(self, message):
                            print(f"[WARNING] {message}")
                        def error(self, message):
                            print(f"[ERROR] {message}")
                    
                    print_logger = PrintLogger()
                    
                    # EnhancedLargeKGRetriever 생성
                    enhanced_lkg_retriever = EnhancedLargeKGRetriever(
                        keyword=keyword,
                        neo4j_driver=neo4j_driver,
                        llm_generator=llm_generator,
                        sentence_encoder=sentence_encoder,
                        node_index=node_index,
                        passage_index=passage_index,
                        topN=5,
                        number_of_source_nodes_per_ner=10,
                        sampling_area=250,
                        database=neo4j_database,
                        verbose=True,
                        logger=print_logger
                    )
                    
                    # node_list와 GraphML 그래프 추가 (원본과 동일하게)
                    enhanced_lkg_retriever.node_list = node_list
                    
                    # GraphML 그래프 로드 (노드 타입 정보용)
                    import networkx as nx
                    graphml_path = os.path.join(project_root, "import", keyword, "kg_graphml", f"{keyword}_graph_with_numeric_id.graphml")
                    print(f"   - graphml_path: {graphml_path}")
                    print(f"   - graphml_path 존재: {os.path.exists(graphml_path)}")
                    
                    if os.path.exists(graphml_path):
                        with open(graphml_path, "rb") as f:
                            enhanced_lkg_retriever.kg_graph = nx.read_graphml(f)
                        print(f"✅ GraphML 그래프 로드 성공: {len(enhanced_lkg_retriever.kg_graph.nodes)}개 노드")
                    else:
                        print("❌ GraphML 파일을 찾을 수 없습니다!")
                        enhanced_lkg_retriever.kg_graph = None
                    
                    print("✅ EnhancedLargeKGRetriever 생성 완료")
                    
                    # HippoRAG2Retriever 생성
                    hippo_retriever = HippoRAG2Retriever(
                        llm_generator=llm_generator,
                        sentence_encoder=sentence_encoder,
                        data=data,
                    )
                    print("✅ HippoRAG2Retriever 생성 완료")
                    
                else:
                    print("❌ FAISS 인덱스 파일을 찾을 수 없습니다!")
                    print(f"   node_index_path: {node_index_path}")
                    print(f"   passage_index_path: {passage_index_path}")
                    
            except Exception as e:
                print(f"❌ FAISS 인덱스 로드 실패: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️ Neo4j 연결이 없어서 리트라이버를 생성할 수 없습니다.")
        
        return enhanced_lkg_retriever, hippo_retriever, llm_generator, neo4j_driver
        
    except Exception as e:
        print(f"❌ RAG 시스템 로드 실패: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None

def extract_concepts_from_question(question, llm_generator):
    """
    질문에서 concept 키워드를 추출합니다.
    """
    if not question or not llm_generator:
        return []
    
    print("�� 질문에서 concept 키워드 추출 중...")
    
    try:
        # Concept 추출을 위한 프롬프트
        concept_extraction_prompt = f"""
다음 질문에서 계약서와 관련된 핵심 concept들을 추출해주세요.

질문: {question}

다음 형식으로 추출해주세요:
1. 계약 관련 concept (예: 계약당사자, 의무, 권리, 조건, 조항 등)
2. 법적 concept (예: 손해배상, 계약해지, 비밀유지, 지적재산권 등)
3. 비즈니스 concept (예: 매도인, 매수인, 가격, 조정, 운전자본 등)

각 concept을 쉼표로 구분하여 나열해주세요.
"""
        
        messages = [
            {"role": "system", "content": "당신은 계약서 분석 전문가입니다. 질문에서 핵심 concept들을 정확히 추출해주세요."}, 
            {"role": "user", "content": concept_extraction_prompt}
        ]
        
        response = llm_generator.generate_response(
            messages, 
            max_new_tokens=256, 
            temperature=0.3
        )
        
        # 응답에서 concept 추출
        concepts = []
        if response:
            # 쉼표로 분리하고 정리
            raw_concepts = [concept.strip() for concept in response.split(',') if concept.strip()]
            concepts = [concept for concept in raw_concepts if len(concept) > 1]
        
        print(f"✅ 추출된 concept: {concepts}")
        return concepts
        
    except Exception as e:
        print(f"⚠️ concept 추출 실패: {e}")
        return []

def search_by_concept_matching(question, concepts, enhanced_lkg_retriever, neo4j_driver, topN=20):
    """
    Concept 매칭을 통한 검색을 수행합니다.
    """
    if not concepts or not enhanced_lkg_retriever or not neo4j_driver:
        return [], []
    
    print("🔍 Concept 매칭 검색 시작...")
    
    try:
        # Neo4j에서 concept_list가 있는 노드들을 검색
        with neo4j_driver.session() as session:
            # Concept 매칭 쿼리
            concept_query = """
            MATCH (n:Node)
            WHERE n.concept_list IS NOT NULL
            RETURN n.id as node_id, n.name as node_name, n.concept_list as concept_list
            """
            
            result = session.run(concept_query)
            nodes_with_concepts = []
            
            for record in result:
                node_id = record["node_id"]
                node_name = record["node_name"]
                concept_list = record["concept_list"]
                
                if concept_list:
                    # concept_list가 JSON 문자열인 경우 파싱
                    if isinstance(concept_list, str):
                        try:
                            concept_list = json.loads(concept_list)
                        except:
                            concept_list = []
                    
                    # Concept 매칭 점수 계산
                    concept_score = 0
                    matched_concepts = []
                    
                    for concept in concepts:
                        for node_concept in concept_list:
                            if concept.lower() in node_concept.lower() or node_concept.lower() in concept.lower():
                                concept_score += 1
                                matched_concepts.append(node_concept)
                    
                    if concept_score > 0:
                        nodes_with_concepts.append({
                            'node_id': node_id,
                            'node_name': node_name,
                            'concept_list': concept_list,
                            'concept_score': concept_score,
                            'matched_concepts': matched_concepts
                        })
            
            # Concept 점수로 정렬
            nodes_with_concepts.sort(key=lambda x: x['concept_score'], reverse=True)
            
            print(f"✅ Concept 매칭 결과: {len(nodes_with_concepts)}개 노드")
            
            # 상위 결과 반환
            top_nodes = nodes_with_concepts[:topN]
            
            content = []
            context_ids = []
            
            for node in top_nodes:
                content.append(node['node_name'])
                context_ids.append(node['node_id'])
                print(f"   - {node['node_name'][:50]}... (점수: {node['concept_score']}, 매칭: {node['matched_concepts']})")
            
            return content, context_ids
            
    except Exception as e:
        print(f"⚠️ Concept 매칭 검색 실패: {e}")
        return [], []

def search_text_nodes_by_content(question, concepts, neo4j_driver, topN=15):
    """
    Text 노드의 실제 내용에서 검색합니다.
    """
    if not concepts or not neo4j_driver:
        return [], []
    
    print("🔍 Text 노드 내용 검색 시작...")
    
    try:
        with neo4j_driver.session() as session:
            all_matched_texts = []
            
            # 각 concept에 대해 Text 노드에서 검색
            for concept in concepts:
                # concept을 단어 단위로 분리
                words = concept.split()
                for word in words:
                    if len(word) > 1:  # 1글자 단어 제외
                        # 유사한 단어들도 검색
                        similar_words = get_similar_words(word)
                        
                        for search_word in similar_words:
                            # Text 노드에서 검색
                            text_query = """
                            MATCH (t:Text)
                            WHERE t.text CONTAINS $word
                            RETURN t.id as text_id, t.text as text_content
                            LIMIT 10
                            """
                            
                            result = session.run(text_query, word=search_word)
                            for record in result:
                                all_matched_texts.append({
                                    'text_id': record["text_id"],
                                    'text_content': record["text_content"],
                                    'search_word': search_word,
                                    'original_word': word
                                })
            
            # 중복 제거 및 점수 계산
            text_scores = {}
            for text in all_matched_texts:
                text_id = text['text_id']
                if text_id not in text_scores:
                    text_scores[text_id] = {
                        'text_id': text_id,
                        'text_content': text['text_content'],
                        'score': 0,
                        'matched_words': []
                    }
                
                # 매칭된 단어 수로 점수 계산
                matched_words = []
                for concept in concepts:
                    for word in concept.split():
                        if len(word) > 1 and word in text['text_content']:
                            matched_words.append(word)
                
                text_scores[text_id]['score'] += len(matched_words)
                text_scores[text_id]['matched_words'].extend(matched_words)
            
            # 점수순으로 정렬
            sorted_texts = sorted(text_scores.values(), key=lambda x: x['score'], reverse=True)
            
            # 상위 N개 선택
            selected_texts = sorted_texts[:topN]
            
            content = [text['text_content'] for text in selected_texts]
            context_ids = [text['text_id'] for text in selected_texts]
            
            print(f"✅ Text 노드 내용 검색 결과: {len(selected_texts)}개")
            for i, text in enumerate(selected_texts[:5]):  # 상위 5개만 출력
                print(f"   - {text['text_content'][:50]}... (점수: {text['score']}, 매칭: {text['matched_words'][:3]})")
            
            return content, context_ids
            
    except Exception as e:
        print(f"⚠️ Text 노드 내용 검색 실패: {e}")
        return [], []

def get_similar_words(word):
    """한국어 유사어 반환"""
    similar_dict = {
        '중대한': ['중요한', '주요한', '핵심적인'],
        '부정적': ['나쁜', '악화된', '불리한'],
        '변경': ['변동', '변화', '수정'],
        'MAE': ['중요한 부정적 변동', '중대한 부정적 변경'],
        '거래종결': ['거래 종결', '거래완료', '거래마감'],
        '계약': ['계약서', '협약', '약정']
    }
    
    # 정확한 매칭
    if word in similar_dict:
        return [word] + similar_dict[word]
    
    # 부분 매칭
    similar_words = [word]
    for key, values in similar_dict.items():
        if word in key or key in word:
            similar_words.extend(values)
    
    return list(set(similar_words))  # 중복 제거

def enhance_search_with_concept_expansion(question, concepts, enhanced_lkg_retriever, topN=10):
    """
    Concept을 활용하여 검색 쿼리를 확장합니다.
    """
    if not concepts or not enhanced_lkg_retriever:
        return [], []
    
    print("🔍 Concept 확장 검색 시작...")
    
    try:
        # 원본 질문 + concept들을 결합한 확장 쿼리 생성
        expanded_query = f"{question} {' '.join(concepts)}"
        
        # 조항 검색이 아닌 경우만 일반 검색 실행 (중복 방지)
        if not enhanced_lkg_retriever.is_clause_question(expanded_query):
            # EnhancedLargeKGRetriever로 검색
            result = enhanced_lkg_retriever.retrieve(expanded_query, topN=topN)
            
            # 결과가 2개인지 확인하고 안전하게 언패킹
            if result and len(result) == 2:
                content, context_ids = result
            else:
                # 결과가 2개가 아닌 경우 빈 리스트 반환
                print(f"⚠️ retrieve 결과가 올바르지 않음: {type(result)}, 길이: {len(result) if result else 'None'}")
                return [], []
        else:
            # 조항 질문인 경우 조항 검색만 실행
            clause_results = enhanced_lkg_retriever.search_clause_directly(expanded_query, topN=topN)
            if clause_results:
                content = [result['text'] for result in clause_results]
                context_ids = [result['textId'] for result in clause_results]
            else:
                content, context_ids = [], []
        
        if content and context_ids:
            print(f"✅ Concept 확장 검색: {len(content)}개 결과")
            return content, context_ids
        else:
            print("⚠️ Concept 확장 검색: 결과 없음")
            return [], []
            
    except Exception as e:
        print(f"⚠️ Concept 확장 검색 실패: {e}")
        return [], []

def rerank_results_by_concept_similarity(content, context_ids, concepts, neo4j_driver):
    """
    Concept 유사도를 기반으로 검색 결과를 재순위화합니다.
    """
    if not content or not context_ids or not concepts or not neo4j_driver:
        return content, context_ids
    
    print("�� Concept 유사도 기반 재순위화 시작...")
    
    try:
        # Neo4j에서 각 노드의 concept_list 가져오기
        with neo4j_driver.session() as session:
            node_concepts = {}
            
            for context_id in context_ids:
                query = """
                MATCH (n:Node {id: $node_id})
                WHERE n.concept_list IS NOT NULL
                RETURN n.concept_list as concept_list
                """
                
                result = session.run(query, node_id=context_id)
                record = result.single()
                
                if record and record["concept_list"]:
                    concept_list = record["concept_list"]
                    if isinstance(concept_list, str):
                        try:
                            concept_list = json.loads(concept_list)
                        except:
                            concept_list = []
                    node_concepts[context_id] = concept_list
            
            # Concept 유사도 점수 계산
            scored_results = []
            
            for i, (content_item, context_id) in enumerate(zip(content, context_ids)):
                if context_id in node_concepts:
                    concept_list = node_concepts[context_id]
                    
                    # Concept 매칭 점수 계산
                    concept_score = 0
                    for concept in concepts:
                        for node_concept in concept_list:
                            if concept.lower() in node_concept.lower() or node_concept.lower() in concept.lower():
                                concept_score += 1
                    
                    scored_results.append({
                        'content': content_item,
                        'context_id': context_id,
                        'concept_score': concept_score,
                        'original_rank': i
                    })
                else:
                    scored_results.append({
                        'content': content_item,
                        'context_id': context_id,
                        'concept_score': 0,
                        'original_rank': i
                    })
            
            # Concept 점수로 정렬 (높은 점수 우선)
            scored_results.sort(key=lambda x: x['concept_score'], reverse=True)
            
            # 재정렬된 결과 반환
            reranked_content = [item['content'] for item in scored_results]
            reranked_ids = [item['context_id'] for item in scored_results]
            
            print(f"✅ Concept 재순위화 완료: {len(reranked_content)}개 결과")
            
            # 상위 5개 결과의 점수 출력
            for i, item in enumerate(scored_results[:5]):
                print(f"   {i+1}. 점수: {item['concept_score']}, 원래 순위: {item['original_rank']+1}")
            
            return reranked_content, reranked_ids
            
    except Exception as e:
        print(f"⚠️ Concept 재순위화 실패: {e}")
        return content, context_ids

def is_clause_question(question):
    """
    질문이 조항 관련 질문인지 판단
    """
    import re
    clause_patterns = [
        r'제\d+조',
        r'\d+조',
        r'조항\s*\d+',
        r'제\d+조\s*\d+항',
        r'\d+조\s*\d+항',
        r'비밀유지',
        r'계약해지',
        r'손해배상',
        r'지적재산권',
        r'유지보수',
        r'대가',
        r'책임',
        r'효력',
        r'분쟁',
        r'거래종결',
        r'배당',
        r'차입',
        r'매도인',
        r'매수인',
        r'계약',
        r'가격',
        r'조정',
        r'운전자본',
        r'부채'
    ]
    
    for pattern in clause_patterns:
        if re.search(pattern, question):
            return True
    return False

def extract_key_terms_from_hippo_results(hippo_content, llm_generator):
    """
    HiPPO-RAG2 검색 결과에서 핵심 키워드와 조항 정보를 추출합니다.
    """
    if not hippo_content:
        return []
    
    print("🔍 HiPPO-RAG2 결과에서 핵심 키워드 추출 중...")
    
    try:
        # 검색 결과를 하나의 텍스트로 합치기
        combined_text = "\n".join(hippo_content[:10])  # 상위 10개 결과만 사용
        
        # 키워드 추출을 위한 프롬프트
        keyword_extraction_prompt = f"""
다음 텍스트에서 계약서 조항과 관련된 핵심 키워드들을 추출해주세요.

텍스트:
{combined_text}

다음 형식으로 추출해주세요:
1. 조항 번호 (예: 제6조, 제8조 3항, 제12조 2항 등)
2. 핵심 키워드 (예: 비밀유지, 손해배상, 계약해지, 지적재산권 등)
3. 관련 개념 (예: 계약당사자, 의무, 권리, 조건 등)

각 항목을 쉼표로 구분하여 나열해주세요.
"""
        
        messages = [
            {"role": "system", "content": "당신은 계약서 분석 전문가입니다. 텍스트에서 핵심 키워드와 조항 정보를 정확히 추출해주세요."}, 
            {"role": "user", "content": keyword_extraction_prompt}
        ]
        
        response = llm_generator.generate_response(
            messages, 
            max_new_tokens=512, 
            temperature=0.3
        )
        
        # 응답에서 키워드 추출
        keywords = []
        if response:
            # 쉼표로 분리하고 정리
            raw_keywords = [kw.strip() for kw in response.split(',') if kw.strip()]
            keywords = [kw for kw in raw_keywords if len(kw) > 1]
        
        print(f"✅ 추출된 키워드: {keywords}")
        return keywords
        
    except Exception as e:
        print(f"⚠️ 키워드 추출 실패: {e}")
        return []

def search_multiple_clauses(extracted_keywords, enhanced_lkg_retriever, topN=10):
    """
    추출된 키워드에서 여러 조항을 찾아서 각각 검색합니다.
    연결된 노드도 함께 포함하여 더 포괄적인 결과를 제공합니다.
    """
    if not extracted_keywords or not enhanced_lkg_retriever:
        return [], []
    
    print("🔍 여러 조항 검색 시작...")
    
    # 조항 번호 패턴 찾기
    import re
    clause_pattern = r'제?(\d+)조'
    found_clauses = set()
    
    for keyword in extracted_keywords:
        matches = re.findall(clause_pattern, keyword)
        for match in matches:
            found_clauses.add(int(match))
    
    print(f"🔍 발견된 조항들: {sorted(found_clauses)}")
    
    if not found_clauses:
        print("⚠️ 조항 번호를 찾을 수 없습니다.")
        return [], []
    
    all_content = []
    all_ids = []
    
    # 각 조항에 대해 개별적으로 검색
    for clause_num in sorted(found_clauses):
        try:
            print(f"🔍 제{clause_num}조 검색 중...")
            clause_query = f"제{clause_num}조"
            
            # EnhancedLargeKGRetriever의 조항 검색 사용 (연결된 노드 포함)
            clause_content, clause_ids = enhanced_lkg_retriever.retrieve(clause_query, topN=topN//len(found_clauses))
            
            if clause_content and clause_ids:
                all_content.extend(clause_content)
                all_ids.extend(clause_ids)
                print(f"✅ 제{clause_num}조: {len(clause_content)}개 결과 (연결된 노드 포함)")
                # 디버깅: 각 결과의 내용 일부 출력
                for i, (content_item, content_id) in enumerate(zip(clause_content, clause_ids)):
                    print(f"   결과 {i+1} (ID: {content_id}): {content_item[:100]}...")
            else:
                print(f"⚠️ 제{clause_num}조: 결과 없음")
                
        except Exception as e:
            print(f"⚠️ 제{clause_num}조 검색 실패: {e}")
            continue
    
    # 중복 제거
    unique_content = []
    unique_ids = []
    seen_ids = set()
    
    for content_item, context_id in zip(all_content, all_ids):
        if content_item and context_id and context_id not in seen_ids:
            seen_ids.add(context_id)
            unique_content.append(content_item)
            unique_ids.append(context_id)
    
    print(f"✅ 총 조항 검색 결과: {len(unique_content)}개 (중복 제거 후)")
    return unique_content, unique_ids

def concept_enhanced_hybrid_retrieve(question, enhanced_lkg_retriever, hippo_retriever, llm_generator, neo4j_driver, topN=50):
    """
    Concept을 활용한 향상된 하이브리드 검색 (수정 버전)
    0. 조항 검색 시도 (조항 질문인 경우)
    1. 질문에서 concept 추출
    2. Concept 매칭 검색
    3. Concept 확장 검색
    4. HiPPO-RAG2 검색
    5. 결과 재순위화
    """
    print(f"�� Concept 활용 하이브리드 검색 시작: {question} (최대 {topN}개)")
    
    content = []
    context_ids = []
    
    # 0단계: Neo4j 직접 검색 (모든 질문에 대해)
    print(f"🔍 0단계 - Neo4j 직접 검색 시도")
    try:
        # 키워드 추출
        keywords = enhanced_lkg_retriever._extract_keywords_from_query(question)
        print(f"🔍 추출된 키워드: {keywords}")
        
        if keywords:
            # 키워드로 Neo4j에서 직접 검색
            keyword_results = enhanced_lkg_retriever._search_by_keywords(keywords, topN=15)
            if keyword_results:
                keyword_content = [result['text'] for result in keyword_results]
                keyword_ids = [result['textId'] for result in keyword_results]
                content.extend(keyword_content)
                context_ids.extend(keyword_ids)
                print(f"✅ Neo4j 직접 검색: {len(keyword_content)}개 결과")
            else:
                print("⚠️ Neo4j 직접 검색: 결과 없음")
        else:
            print("⚠️ 키워드 추출 실패")
    except Exception as e:
        print(f"⚠️ Neo4j 직접 검색 실패: {e}")
    
    # 0.5단계: 조항 검색 시도 (조항 질문인 경우)
    if enhanced_lkg_retriever.is_clause_question(question):
        print(f"🔍 0.5단계 - 조항 검색 시도")
        try:
            # 조항 검색만 직접 실행 (중복 방지)
            clause_results = enhanced_lkg_retriever.search_clause_directly(question, topN=10)
            if clause_results:
                clause_content = [result['text'] for result in clause_results]
                clause_ids = [result['textId'] for result in clause_results]
                content.extend(clause_content)
                context_ids.extend(clause_ids)
                print(f"✅ 조항 검색: {len(clause_content)}개 결과")
            else:
                print("⚠️ 조항 검색: 결과 없음")
        except Exception as e:
            print(f"⚠️ 조항 검색 실패: {e}")
    
    # 1단계: 질문에서 concept 추출 (조항 질문이어도 실행)
    concepts = extract_concepts_from_question(question, llm_generator)
    
    # 2단계: Concept 매칭 검색 (전체의 30%)
    # 2.5단계: Text 노드 내용 검색 (전체의 20%)
    text_content_topN = max(1, int(topN * 0.2))
    print(f"🔍 1.5단계 - Text 노드 내용 검색: {text_content_topN}개")

    if concepts and neo4j_driver:
        try:
            text_content, text_ids = search_text_nodes_by_content(
                question, concepts, neo4j_driver, text_content_topN
            )
            
            if text_content and text_ids:
                content.extend(text_content)
                context_ids.extend(text_ids)
                print(f"✅ Text 노드 내용 검색: {len(text_content)}개 결과")
            else:
                print("⚠️ Text 노드 내용 검색: 결과 없음")
        except Exception as e:
            print(f"⚠️ Text 노드 내용 검색 실패: {e}")
        
    concept_matching_topN = max(1, int(topN * 0.3))
    print(f"�� 1단계 - Concept 매칭 검색: {concept_matching_topN}개")
    
    if concepts and neo4j_driver:
        try:
            concept_content, concept_ids = search_by_concept_matching(
                question, concepts, enhanced_lkg_retriever, neo4j_driver, concept_matching_topN
            )
            
            if concept_content and concept_ids:
                content.extend(concept_content)
                context_ids.extend(concept_ids)
                print(f"✅ Concept 매칭 검색: {len(concept_content)}개 결과")
            else:
                print("⚠️ Concept 매칭 검색: 결과 없음")
        except Exception as e:
            print(f"⚠️ Concept 매칭 검색 실패: {e}")
    
    # 3단계: Concept 확장 검색 (전체의 40%)
    concept_expansion_topN = max(1, int(topN * 0.3))
    print(f"�� 2단계 - Concept 확장 검색: {concept_expansion_topN}개")
    
    if concepts and enhanced_lkg_retriever:
        try:
            expansion_content, expansion_ids = enhance_search_with_concept_expansion(
                question, concepts, enhanced_lkg_retriever, concept_expansion_topN
            )
            
            if expansion_content and expansion_ids:
                content.extend(expansion_content)
                context_ids.extend(expansion_ids)
                print(f"✅ Concept 확장 검색: {len(expansion_content)}개 결과")
            else:
                print("⚠️ Concept 확장 검색: 결과 없음")
        except Exception as e:
            print(f"⚠️ Concept 확장 검색 실패: {e}")
    
    # 4단계: HiPPO-RAG2 검색 (전체의 50%)
    hippo_topN = max(1, int(topN * 0.5))
    print(f"�� 3단계 - HiPPO-RAG2 검색: {hippo_topN}개")
    
    if hippo_retriever:
        try:
            hippo_content, hippo_ids = hippo_retriever.retrieve(question, topN=hippo_topN)
            
            if hippo_content and hippo_ids:
                content.extend(hippo_content)
                context_ids.extend(hippo_ids)
                print(f"✅ HiPPO-RAG2 검색: {len(hippo_content)}개 결과")
            else:
                print("⚠️ HiPPO-RAG2 검색: 결과 없음")
        except Exception as e:
            print(f"⚠️ HiPPO-RAG2 검색 실패: {e}")
    
    # 5단계: 중복 제거
    unique_content = []
    unique_ids = []
    seen_ids = set()
    
    if content and context_ids and len(content) == len(context_ids):
        for content_item, context_id in zip(content, context_ids):
            if content_item and context_id and context_id not in seen_ids:
                seen_ids.add(context_id)
                unique_content.append(content_item)
                unique_ids.append(context_id)
    
    # 6단계: Concept 유사도 기반 재순위화
    if concepts and neo4j_driver and unique_content and unique_ids:
        try:
            unique_content, unique_ids = rerank_results_by_concept_similarity(
                unique_content, unique_ids, concepts, neo4j_driver
            )
        except Exception as e:
            print(f"⚠️ Concept 재순위화 실패: {e}")
    
    if not unique_content or not unique_ids:
        print("⚠️ 검색 결과가 없습니다.")
        return [], []
    
    print(f"✅ 최종 검색 결과: {len(unique_content)}개")
    return unique_content[:topN], unique_ids[:topN]

def save_qa_to_file(question, answer, qa_file_path):
    """질문과 답변을 JSON 파일에 저장"""
    try:
        # 기존 데이터 로드
        qa_data = []
        if os.path.exists(qa_file_path):
            with open(qa_file_path, 'r', encoding='utf-8') as f:
                qa_data = json.load(f)
        
        # 새로운 Q&A 추가
        qa_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer
        }
        qa_data.append(qa_entry)
        
        # 파일에 저장
        with open(qa_file_path, 'w', encoding='utf-8') as f:
            json.dump(qa_data, f, ensure_ascii=False, indent=2)
        
        print(f"�� 질문과 답변이 저장되었습니다: {qa_file_path}")
        
    except Exception as e:
        print(f"⚠️ 파일 저장 실패: {e}")

def load_qa_history(qa_file_path, max_entries=5):
    """이전 질문과 답변 기록을 로드하여 표시"""
    try:
        if not os.path.exists(qa_file_path):
            return
        
        with open(qa_file_path, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
        
        if not qa_data:
            return
        
        print(f"\n�� 최근 질문과 답변 기록 (최대 {max_entries}개):")
        print("=" * 60)
        
        # 최근 항목들을 역순으로 표시
        recent_entries = qa_data[-max_entries:]
        for i, entry in enumerate(reversed(recent_entries), 1):
            timestamp = entry.get('timestamp', '알 수 없음')
            question = entry.get('question', '')
            answer = entry.get('answer', '')
            
            print(f"\n[{i}] {timestamp}")
            print(f"질문: {question}")
            print(f"답변: {answer[:200]}{'...' if len(answer) > 200 else ''}")
            print("-" * 40)
        
    except Exception as e:
        print(f"⚠️ 기록 로드 실패: {e}")

def run_single_question(question, llm_generator, enhanced_lkg_retriever, hippo_retriever, neo4j_driver, qa_file_path=None):
    """단일 질문 실행 (Concept 활용 하이브리드 검색)"""
    print(f"\n 질문: {question}")
    print("-" * 50)
    
    try:
        # Concept 활용 하이브리드 검색 실행
        result = concept_enhanced_hybrid_retrieve(
            question, 
            enhanced_lkg_retriever, 
            hippo_retriever,
            llm_generator,
            neo4j_driver,
            topN=50
        )
        
        # 결과 검증 및 안전한 언패킹
        if result and len(result) == 2:
            content, context_ids = result
            print(f"🔍 검색 결과 확인 - content: {type(content)}, context_ids: {type(context_ids)}")
            print(f"🔍 content 길이: {len(content) if content else 'None'}, context_ids 길이: {len(context_ids) if context_ids else 'None'}")
            
            # 검색 결과 상세 출력
            if content:
                print(f"📋 검색된 컨텍스트 (처음 3개):")
                for i, ctx in enumerate(content[:3], 1):
                    print(f"   {i}. {ctx[:100]}...")
            else:
                print("❌ 검색된 컨텍스트가 없습니다!")
        else:
            print("⚠️ 하이브리드 검색 결과가 올바르지 않습니다.")
            print(f"🔍 result 타입: {type(result)}, 길이: {len(result) if result else 'None'}")
            content, context_ids = [], []
        
        if content and context_ids:
            print(f"✅ {len(content)}개의 관련 컨텍스트를 찾았습니다.")
            
            # 컨텍스트를 사용한 답변 생성
            print("🤖 LLM을 사용해서 답변을 생성 중...")
            sorted_context = "\n".join(content)
            
            try:
                # 한국어 답변을 위한 시스템 프롬프트 사용
                korean_system_instruction = (
                    "당신은 대한민국의 고급 계약서 분석 전문가입니다. 주어진 텍스트와 질문을 꼼꼼히 분석하고 답변해야 합니다. "
                    "정보가 충분하지 않다면 자신의 지식을 활용해서 답변할 수 있습니다. "
                    "답변은 'Thought: '로 시작하여 추론 과정을 단계별로 설명하고, "
                    "'Answer: '로 끝나며 간결하고 명확한 답변을 제공해야 합니다. "
                    "모든 답변은 한국어로 해주세요."
                )
                messages = [
                    {"role": "system", "content": korean_system_instruction},
                    {"role": "user", "content": f"{sorted_context}\n\n{question}\nThought:"},
                ]
                
                print(f" LLM 호출 시작 - 컨텍스트 길이: {len(sorted_context)}")
                answer = llm_generator.generate_response(
                    messages, 
                    max_new_tokens=2048, 
                    temperature=0.5,
                    validate_function=None
                )
                print(f" 답변: {answer}")
                
                # 질문과 답변을 파일에 저장
                if qa_file_path:
                    save_qa_to_file(question, answer, qa_file_path)
                
                # 빈 답변인 경우 다른 방법 시도
                if not answer or answer == "[]" or len(str(answer)) < 5:
                    print(" 빈 답변 감지, 다른 방법으로 시도...")
                    # 한국어 답변을 위한 KG 시스템 프롬프트 사용
                    korean_kg_system_instruction = (
                        "당신은 고급 독해 전문가입니다. 추출된 정보와 질문을 꼼꼼히 분석하고 답변해야 합니다. "
                        "지식 그래프 정보가 충분하지 않다면 자신의 지식을 활용해서 답변할 수 있습니다. "
                        "답변은 'Thought: '로 시작하여 추론 과정을 단계별로 설명하고, "
                        "'Answer: '로 끝나며 간결하고 명확한 답변을 제공해야 합니다. "
                        "모든 답변은 한국어로 해주세요."
                    )
                    kg_messages = [
                        {"role": "system", "content": korean_kg_system_instruction},
                        {"role": "user", "content": f"{sorted_context}\n\n{question}"},
                    ]
                    answer = llm_generator.generate_response(
                        kg_messages, 
                        max_new_tokens=2048, 
                        temperature=0.5,
                        validate_function=None
                    )
                    print(f" 백업 답변: {answer}")
                    
                    # 백업 답변도 파일에 저장
                    if qa_file_path:
                        save_qa_to_file(question, answer, qa_file_path)
                    
            except Exception as e:
                print(f"❌ LLM 호출 오류: {e}")
                import traceback
                print(f"❌ 상세 오류 정보:\n{traceback.format_exc()}")
                answer = "답변 생성 중 오류가 발생했습니다."
            
        else:
            print("❌ 관련 컨텍스트를 찾을 수 없습니다.")
            answer = "관련 컨텍스트를 찾을 수 없어 답변을 생성할 수 없습니다."
            
            # 오류 상황도 파일에 저장
            if qa_file_path:
                save_qa_to_file(question, answer, qa_file_path)
            
    except Exception as e:
        print(f"❌ 질문 처리 중 오류 발생: {e}")
        import traceback
        print(f"❌ 상세 오류 정보:\n{traceback.format_exc()}")
        answer = f"질문 처리 중 오류가 발생했습니다: {str(e)}"
        
        # 오류 상황도 파일에 저장
        if qa_file_path:
            save_qa_to_file(question, answer, qa_file_path)
    
    print("-" * 50)

def main():
    """메인 실행 함수"""
    print("🚀 Concept 활용 LKG + HiPPO-RAG2 하이브리드 RAG 질문 모드 시작!")
    print("="*80)
    print("�� 원하는 질문을 자유롭게 입력하세요!")
    print("💡 계약서 관련 질문 예시:")
    print("   - '제6조는 무엇에 관한 조항인가요?'")
    print("   - '제8조 3항의 내용을 알려주세요'")
    print("   - '비밀유지 조항에 대해 설명해주세요'")
    print("   - '계약 해지 조건은 무엇인가요?'")
    print("   - '손해배상에 대한 규정을 알려주세요'")
    print("💡 종료하려면 'quit', 'exit', '종료'를 입력하세요.")
    print("�� 'history' 또는 '기록'을 입력하면 이전 질문과 답변을 볼 수 있습니다.")
    print("="*80)
    
    # Q&A 저장 파일 경로 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    qa_file_path = os.path.join(script_dir, "qa_history_concept_enhanced.json")
    print(f"📁 질문과 답변은 다음 파일에 저장됩니다: {qa_file_path}")
    
    # 이전 기록이 있으면 보여주기
    load_qa_history(qa_file_path, max_entries=3)
    
    # RAG 시스템 로드
    enhanced_lkg_retriever, hippo_retriever, llm_generator, neo4j_driver = load_enhanced_rag_system()
    if llm_generator is None:
        return
    
    # retriever 확인
    if enhanced_lkg_retriever is None and hippo_retriever is None:
        print("❌ retriever가 모두 None입니다. RAG 시스템 로드를 확인하세요.")
        return
    
    # 대화형 질문 입력
    while True:
        try:
            # 사용자 입력 받기
            question = input("\n📝 질문을 입력하세요: ").strip()
            
            # 종료 조건 확인
            if question.lower() in ['quit', 'exit', '종료', 'q']:
                print("�� Concept 활용 하이브리드 질문 모드를 종료합니다.")
                break
            
            # 빈 입력 처리
            if not question:
                print("❌ 질문을 입력해주세요.")
                continue
            
            # 기록 보기 명령 처리
            if question.lower() in ['history', '기록', 'h']:
                load_qa_history(qa_file_path, max_entries=10)
                continue
            
            # 질문 실행 (Concept 활용 하이브리드 검색)
            run_single_question(question, llm_generator, enhanced_lkg_retriever, hippo_retriever, neo4j_driver, qa_file_path)
            
        except KeyboardInterrupt:
            print("\n�� Concept 활용 하이브리드 질문 모드를 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
    
    print("\n�� Concept 활용 하이브리드 질문 모드가 완료되었습니다!")

if __name__ == "__main__":
    main()
