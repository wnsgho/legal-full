#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ATLAS 전체 파이프라인 테스트 스크립트
README의 예제를 기반으로 지식그래프 구축을 테스트합니다.

=============================================================================
서버 배포 시 수정 필요 사항:
=============================================================================
1. 상대 import → 절대 import 변경 (완료)
   - from .atlas_rag... → from atlas_rag...

2. subprocess.run cwd 설정 수정 (완료)
   - cwd="BE" → cwd="." (BE 디렉토리에서 실행할 때)
   - 서버에서는 프로젝트 루트에서 실행하므로 cwd="BE"로 되돌려야 함

3. 환경변수 설정 확인
   - .env 파일 경로: load_dotenv('.env') → load_dotenv('../.env')
   - DATA_DIRECTORY: "example_data" → "BE/example_data"

4. Neo4j 연결 설정
   - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE 확인

5. OpenRouter API 설정
   - OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_NAME 확인
=============================================================================
"""

import os
import subprocess
import sys
import glob
import logging
import io

# Windows에서 UTF-8 출력을 위한 설정
if sys.platform.startswith('win'):
    # stdout과 stderr을 UTF-8로 설정
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 서버 배포 시 Python 경로 설정 (모듈로 import될 때도 실행)
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from dotenv import load_dotenv

# UTF-8 로깅 설정 (atlas_rag import 전에 먼저 설정)
from atlas_rag.utils.utf8_logging import setup_utf8_logging
setup_utf8_logging()

# atlas_rag 모듈들을 나중에 import
from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
from atlas_rag.kg_construction.triple_config import ProcessingConfig
from atlas_rag.llm_generator import LLMGenerator
from openai import OpenAI
from transformers import pipeline

# OpenAI 클라이언트의 로깅 비활성화
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

def check_files_exist(file_patterns, directory):
    """지정된 디렉토리에서 파일 패턴들이 존재하는지 확인합니다."""
    print(f"🔍 파일 존재 확인: {directory}")
    if not os.path.exists(directory):
        print(f"❌ 디렉토리가 존재하지 않습니다: {directory}")
        return False
    
    for pattern in file_patterns:
        full_pattern = os.path.join(directory, pattern)
        matches = glob.glob(full_pattern)
        print(f"🔍 패턴 검색: {full_pattern} -> {matches}")
        if not matches:
            print(f"❌ 파일을 찾을 수 없습니다: {full_pattern}")
            return False
    print(f"✅ 모든 파일이 존재합니다: {file_patterns}")
    return True

def check_triple_extraction_is_empty(keyword, output_directory):
    """트리플 추출 결과가 비어있는지 확인합니다."""
    import json
    kg_extraction_dir = f"{output_directory}/kg_extraction"
    
    # 실제 파일 이름 패턴: {model_name}_{keyword}_output_{timestamp}_{shard}_in_{total}.json
    # 또는 {keyword}_kg_extraction*.json
    pattern1 = f"{keyword}_kg_extraction*.json"
    pattern2 = f"*_{keyword}_output_*.json"  # 모델 이름이 앞에 붙는 경우
    
    full_pattern1 = os.path.join(kg_extraction_dir, pattern1)
    full_pattern2 = os.path.join(kg_extraction_dir, pattern2)
    matches1 = glob.glob(full_pattern1)
    matches2 = glob.glob(full_pattern2)
    matches = matches1 + matches2
    
    if not matches:
        print(f"🔍 트리플 추출 결과 확인: 파일을 찾을 수 없습니다 (패턴1: {pattern1}, 패턴2: {pattern2})")
        return True  # 파일이 없으면 빈 것으로 간주
    
    # 가장 최근 파일 확인 (여러 파일이 있을 수 있음)
    if matches:
        # 파일 수정 시간으로 정렬하여 가장 최근 파일 확인
        matches_with_time = [(f, os.path.getmtime(f)) for f in matches]
        matches_with_time.sort(key=lambda x: x[1], reverse=True)
        latest_file = matches_with_time[0][0]
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                total_triples = 0
                line_count = 0
                for line in f:
                    line_count += 1
                    if line.strip():
                        try:
                            data = json.loads(line)
                            entity_relations = data.get("entity_relation_dict", [])
                            event_entities = data.get("event_entity_relation_dict", [])
                            event_relations = data.get("event_relation_dict", [])
                            total_triples += len(entity_relations) + len(event_entities) + len(event_relations)
                        except json.JSONDecodeError:
                            continue
                
                print(f"🔍 트리플 추출 결과 확인: {line_count}줄, {total_triples}개 트리플 (파일: {os.path.basename(latest_file)})")
                return total_triples == 0
        except Exception as e:
            print(f"⚠️ 트리플 추출 결과 확인 실패: {e}")
            return True  # 확인 실패 시 빈 것으로 간주하여 재추출
    
    return True

def convert_md_to_json(keyword):
    """마크다운 파일을 JSON으로 변환합니다."""
    print("📝 마크다운을 JSON으로 변환 중...")
    
    data_directory = os.getenv('DATA_DIRECTORY', 'BE/example_data')
    target_json = f"{data_directory}/{keyword}.json"
    if os.path.exists(target_json):
        print(f"✅ {keyword}.json 파일이 이미 존재합니다. 변환을 건너뜁니다.")
        return True
    
    try:
        # markdown_to_json 스크립트 실행 (md_data 디렉토리 전체 변환)
        # 현재 폴더에서 실행하므로 상대 경로 사용
        relative_data_dir = data_directory
        cmd = [
            sys.executable, "-m", 
            "atlas_rag.kg_construction.utils.md_processing.markdown_to_json",
            "--input", f"{relative_data_dir}/md_data",
            "--output", relative_data_dir
        ]
        
        # 현재 폴더에서 실행하도록 작업 디렉토리 설정
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=".")
        print("✅ 마크다운을 JSON으로 변환 완료!")
        print(f"출력: {result.stdout}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 마크다운 변환 실패: {e}")
        print(f"오류 출력: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def test_atlas_pipeline(start_step=1, keyword=None):
    """ATLAS 전체 파이프라인을 테스트합니다."""
    
    print(f"🚀 ATLAS 파이프라인 시작! (단계 {start_step}부터)")
    print(f"📝 전달받은 keyword: {keyword}")
    print(f"📂 현재 작업 디렉토리: {os.getcwd()}")
    
    # kg_extractor 초기화
    kg_extractor = None
    
    # .env 파일 로드 (BE 폴더의 .env 파일 우선)
    # API 서버에서 실행될 때를 고려하여 경로 설정
    env_path = 'BE/.env'  # 프로젝트 루트에서 실행될 때
    if not os.path.exists(env_path):
        env_path = '.env'  # BE 디렉토리에서 직접 실행될 때
    
    print(f"🔍 .env 파일 경로 확인: {env_path}")
    print(f"📄 .env 파일 존재 여부: {os.path.exists(env_path)}")
    
    try:
        load_dotenv(env_path)
        print(f"✅ .env 파일 로드 성공")
    except Exception as e:
        print(f"❌ .env 파일 로드 실패: {e}")
        return False
    
    # keyword가 제공되지 않은 경우 환경변수에서 읽기
    if keyword is None:
        keyword = os.getenv('KEYWORD')
    
    print(f"🔑 사용할 keyword: {keyword}")
    
    import_dir = os.getenv('IMPORT_DIRECTORY', 'import')
    output_directory = f'{import_dir}/{keyword}'
    
    print(f"📁 import_directory: {import_dir}")
    print(f"📁 output_directory: {output_directory}")
    
    # 주요 환경변수 확인
    print(f"🔐 OPENAI_API_KEY 존재: {'있음' if os.getenv('OPENAI_API_KEY') else '없음'}")
    print(f"🌐 OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL', '기본값')}")
    print(f"🤖 DEFAULT_MODEL: {os.getenv('DEFAULT_MODEL', '기본값')}")
    print(f"🗄️ NEO4J_URI: {os.getenv('NEO4J_URI', '기본값')}")
    print(f"📊 DATA_DIRECTORY: {os.getenv('DATA_DIRECTORY', '기본값')}")
    
    if start_step <= 1:
        # 1. 모델 설정
        print("\n📋 1단계: 모델 설정")
        
        try:
            client = OpenAI(
                api_key=os.getenv('OPENAI_API_KEY'),
                base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
            )
            model_name = os.getenv('DEFAULT_MODEL', 'gpt-4.1-2025-04-14')
            triple_generator = LLMGenerator(client=client, model_name=model_name, verbose=False)
            print(f"✅ OpenAI API 클라이언트 설정 완료: {model_name}")
            
        except Exception as e:
            print(f"❌ OpenAI API 설정 실패: {e}")
            return False
    
    if start_step <= 2:
        # 2. 설정 구성
        print("\n📋 2단계: 처리 설정 구성")
        print(f"🔑 사용할 계약서: {keyword}")
    
    if start_step <= 0:
        # 0. 마크다운을 JSON으로 변환 (keyword 사용)
        print("\n📋 0단계: 마크다운을 JSON으로 변환")
        if not convert_md_to_json(keyword):
            print("❌ 마크다운 변환 실패로 파이프라인을 중단합니다.")
            return False
    
    if start_step <= 3:
        # model_name 가져오기 (start_step > 1인 경우)
        if start_step > 1:
            model_name = os.getenv('DEFAULT_MODEL', 'gpt-4.1-2025-04-14')
        
        kg_extraction_config = ProcessingConfig(
            model_path=model_name,
            data_directory=os.getenv('DATA_DIRECTORY', "BE/example_data"),
            filename_pattern=keyword,
            remove_doc_spaces=True,
            output_directory=output_directory,
        )
        
        print(f"✅ 처리 설정 완료: {output_directory}")
        
        # 3. 지식그래프 추출기 생성
        print("\n📋 3단계: 지식그래프 추출기 생성")
        kg_extractor = KnowledgeGraphExtractor(model=triple_generator, config=kg_extraction_config)
        print("✅ 지식그래프 추출기 생성 완료")
    
    if start_step <= 4:
        # 4. 트리플 추출 실행
        print("\n🚀 4단계: 트리플 추출 실행")
        triple_files = [
            f"{keyword}_kg_extraction.json",
            f"{keyword}_kg_extraction_processed.json"
        ]
        
        files_exist = check_files_exist(triple_files, f"{output_directory}/kg_extraction")
        is_empty = check_triple_extraction_is_empty(keyword, output_directory)
        
        if files_exist and not is_empty:
            print("✅ 트리플 추출 파일들이 이미 존재하고 트리플이 있습니다. 추출을 건너뜁니다.")
        else:
            if files_exist and is_empty:
                print("⚠️ 트리플 추출 파일이 존재하지만 빈 트리플입니다. 다시 추출합니다.")
            else:
                print("🔄 트리플 추출 파일이 없습니다. 추출을 시작합니다.")
            
            try:
                print(f"🔄 kg_extractor.run_extraction() 실행 중...")
                if kg_extractor is None:
                    print("❌ kg_extractor가 None입니다. 2-3단계를 먼저 실행하세요.")
                    return False
                kg_extractor.run_extraction()
                print("✅ 트리플 추출 완료!")
                
                # 추출 후 다시 확인
                is_still_empty = check_triple_extraction_is_empty(keyword, output_directory)
                if is_still_empty:
                    print("⚠️ 경고: 트리플 추출이 완료되었지만 여전히 빈 트리플입니다.")
                    print("⚠️ LLM 응답을 확인하거나 모델 설정을 점검하세요.")
            except Exception as e:
                import traceback
                print(f"❌ 트리플 추출 실패: {e}")
                print(f"❌ 상세 오류:\n{traceback.format_exc()}")
                return False
    
    # kg_extractor가 필요한 경우 생성
    if kg_extractor is None:
        print("🔄 kg_extractor 생성 중...")
        # 간단한 설정으로 kg_extractor 생성
        kg_extraction_config = ProcessingConfig(
            model_path="",  # 빈 문자열로 설정 (LLM 사용 시)
            data_directory=os.getenv('DATA_DIRECTORY', "BE/example_data"),
            filename_pattern=keyword,
            remove_doc_spaces=True,
            output_directory=output_directory,
        )
        kg_extractor = KnowledgeGraphExtractor(model=None, config=kg_extraction_config)
        print("✅ kg_extractor 생성 완료")
    
    # 5. JSON을 CSV로 변환
    print("\n🔄 5단계: JSON을 CSV로 변환")
    
    # CSV 파일들이 이미 존재하는지 확인
    csv_files = [
        f"{keyword}_triples.csv",
        f"{keyword}_entities.csv",
        f"{keyword}_relations.csv"
    ]
    if check_files_exist(csv_files, output_directory):
        print("✅ CSV 파일들이 이미 존재합니다. 변환을 건너뜁니다.")
    else:
        try:
            if kg_extractor is None:
                print("❌ kg_extractor가 정의되지 않았습니다. 5단계부터 시작하려면 이전 단계를 먼저 실행하세요.")
                return False
            kg_extractor.convert_json_to_csv()
            print("✅ CSV 변환 완료!")
        except Exception as e:
            print(f"❌ CSV 변환 실패: {e}")
            return False

    # 6. 개념 생성
    print("\n🧠 6단계: 개념 생성")
    concept_files = [f"concept_shard_0.csv"]
    if check_files_exist(concept_files, f"{output_directory}/concepts"):
        print("✅ 개념 생성 파일이 이미 존재합니다. 생성을 건너뜁니다.")
    else:
        try:
            if kg_extractor is None:
                print("❌ kg_extractor가 정의되지 않았습니다. 6단계부터 시작하려면 이전 단계를 먼저 실행하세요.")
                return False
            kg_extractor.generate_concept_csv_temp()
            print("✅ 개념 생성 완료!")
        except Exception as e:
            print(f"❌ 개념 생성 실패: {e}")
            return False

    # 7. 개념 CSV 생성
    print("\n📊 7단계: 개념 CSV 생성")
    
    # 개념 CSV 파일이 이미 존재하는지 확인
    concept_csv_files = [
        f"concept_nodes_{keyword}_from_json_with_concept.csv",
        f"concept_edges_{keyword}_from_json_with_concept.csv"
    ]
    if check_files_exist(concept_csv_files, f"{output_directory}/concept_csv"):
        print("✅ 개념 CSV 파일이 이미 존재합니다. 생성을 건너뜁니다.")
    else:
        try:
            if kg_extractor is None:
                print("❌ kg_extractor가 정의되지 않았습니다. 7단계부터 시작하려면 이전 단계를 먼저 실행하세요.")
                return False
            kg_extractor.create_concept_csv()
            print("✅ 개념 CSV 생성 완료!")
        except Exception as e:
            print(f"❌ 개념 CSV 생성 실패: {e}")
            return False

    # 8. GraphML 생성
    print("\n🕸️ 8단계: GraphML 생성")
    
    # GraphML 파일이 이미 존재하는지 확인
    graphml_files = [f"{keyword}_graph.graphml"]
    graphml_exists = check_files_exist(graphml_files, f"{output_directory}/kg_graphml")
    
    # GraphML 파일에 엣지가 있는지 확인
    need_regenerate = False
    if graphml_exists:
        try:
            import networkx as nx
            graphml_path = f"{output_directory}/kg_graphml/{keyword}_graph.graphml"
            with open(graphml_path, "rb") as f:
                KG = nx.read_graphml(f)
            edge_count = len(KG.edges)
            node_count = len(KG.nodes)
            print(f"🔍 기존 GraphML 확인: {node_count}개 노드, {edge_count}개 엣지")
            if edge_count == 0:
                print("⚠️ GraphML에 엣지가 없습니다. 트리플이 새로 추출되었으므로 GraphML을 다시 생성합니다.")
                need_regenerate = True
        except Exception as e:
            print(f"⚠️ GraphML 확인 실패: {e}. GraphML을 다시 생성합니다.")
            need_regenerate = True
    
    if not graphml_exists or need_regenerate:
        try:
            if kg_extractor is None:
                print("❌ kg_extractor가 정의되지 않았습니다. 8단계부터 시작하려면 이전 단계를 먼저 실행하세요.")
                return False
            if need_regenerate:
                # 기존 파일 삭제
                graphml_path = f"{output_directory}/kg_graphml/{keyword}_graph.graphml"
                if os.path.exists(graphml_path):
                    os.remove(graphml_path)
                    print(f"🗑️ 기존 GraphML 파일 삭제: {graphml_path}")
            kg_extractor.convert_to_graphml()
            print("✅ GraphML 생성 완료!")
            
            # 생성 후 엣지 수 확인
            try:
                import networkx as nx
                graphml_path = f"{output_directory}/kg_graphml/{keyword}_graph.graphml"
                with open(graphml_path, "rb") as f:
                    KG = nx.read_graphml(f)
                edge_count = len(KG.edges)
                node_count = len(KG.nodes)
                print(f"✅ GraphML 생성 확인: {node_count}개 노드, {edge_count}개 엣지")
            except Exception as e:
                print(f"⚠️ GraphML 확인 실패: {e}")
        except Exception as e:
            print(f"❌ GraphML 생성 실패: {e}")
            return False
    else:
        print("✅ GraphML 파일이 이미 존재하고 엣지가 있습니다. 생성을 건너뜁니다.")

    # 9. 숫자 ID 추가
    print("\n🔢 9단계: 숫자 ID 추가")
    
    # 원본 GraphML과 숫자 ID가 추가된 GraphML 비교
    need_regenerate_numeric_id = False
    original_graphml = f"{output_directory}/kg_graphml/{keyword}_graph.graphml"
    numeric_id_graphml = f"{output_directory}/kg_graphml/{keyword}_graph_with_numeric_id.graphml"
    
    if os.path.exists(original_graphml) and os.path.exists(numeric_id_graphml):
        try:
            import networkx as nx
            # 원본 GraphML 확인
            with open(original_graphml, "rb") as f:
                KG_original = nx.read_graphml(f)
            original_edges = len(KG_original.edges)
            original_nodes = len(KG_original.nodes)
            
            # 숫자 ID GraphML 확인
            with open(numeric_id_graphml, "rb") as f:
                KG_numeric = nx.read_graphml(f)
            numeric_edges = len(KG_numeric.edges)
            numeric_nodes = len(KG_numeric.nodes)
            
            print(f"🔍 GraphML 비교: 원본({original_nodes}노드, {original_edges}엣지) vs 숫자ID({numeric_nodes}노드, {numeric_edges}엣지)")
            
            # 엣지 수가 다르면 숫자 ID를 다시 생성해야 함
            if original_edges != numeric_edges or original_nodes != numeric_nodes:
                print("⚠️ GraphML이 업데이트되었습니다. 숫자 ID를 다시 추가합니다.")
                need_regenerate_numeric_id = True
        except Exception as e:
            print(f"⚠️ GraphML 비교 실패: {e}. 숫자 ID를 다시 추가합니다.")
            need_regenerate_numeric_id = True
    elif os.path.exists(original_graphml) and not os.path.exists(numeric_id_graphml):
        print("⚠️ 숫자 ID GraphML 파일이 없습니다. 생성합니다.")
        need_regenerate_numeric_id = True
    
    # 숫자 ID 파일이 이미 존재하는지 확인
    numeric_id_files = [
        f"triple_nodes_{keyword}_from_json_without_emb_with_numeric_id.csv",
        f"triple_edges_{keyword}_from_json_without_emb_with_numeric_id.csv",
        f"text_nodes_{keyword}_from_json_with_numeric_id.csv"
    ]
    files_exist = check_files_exist(numeric_id_files, f"{output_directory}/triples_csv")
    
    if files_exist and not need_regenerate_numeric_id:
        print("✅ 숫자 ID 파일이 이미 존재하고 GraphML과 일치합니다. 생성을 건너뜁니다.")
    else:
        if need_regenerate_numeric_id:
            # 숫자 ID GraphML 파일 삭제
            if os.path.exists(numeric_id_graphml):
                os.remove(numeric_id_graphml)
                print(f"🗑️ 기존 숫자 ID GraphML 파일 삭제: {numeric_id_graphml}")
        try:
            if kg_extractor is None:
                print("❌ kg_extractor가 정의되지 않았습니다. 9단계부터 시작하려면 이전 단계를 먼저 실행하세요.")
                return False
            kg_extractor.add_numeric_id()
            print("✅ 숫자 ID 추가 완료!")
        except Exception as e:
            print(f"❌ 숫자 ID 추가 실패: {e}")
            return False

    # GraphML 파일 복사 (임베딩 생성용)
    import shutil
    source_graphml = f"{output_directory}/kg_graphml/{keyword}_graph.graphml"
    target_graphml = f"{output_directory}/kg_graphml/{keyword}_graph_with_numeric_id.graphml"
    
    # 원본 GraphML과 숫자 ID GraphML 비교
    if os.path.exists(source_graphml):
        try:
            import networkx as nx
            with open(source_graphml, "rb") as f:
                KG_source = nx.read_graphml(f)
            source_edges = len(KG_source.edges)
            source_nodes = len(KG_source.nodes)
            
            if os.path.exists(target_graphml):
                with open(target_graphml, "rb") as f:
                    KG_target = nx.read_graphml(f)
                target_edges = len(KG_target.edges)
                target_nodes = len(KG_target.nodes)
                
                # 엣지 수가 다르면 숫자 ID GraphML이 업데이트되지 않음
                if source_edges != target_edges or source_nodes != target_nodes:
                    print(f"⚠️ GraphML 불일치 감지: 원본({source_nodes}노드, {source_edges}엣지) vs 숫자ID({target_nodes}노드, {target_edges}엣지)")
                    print("⚠️ 숫자 ID GraphML을 업데이트합니다.")
                    shutil.copy2(source_graphml, target_graphml)
                    print("✅ GraphML 파일 업데이트 완료!")
                else:
                    print("✅ GraphML 파일이 일치합니다.")
            else:
                shutil.copy2(source_graphml, target_graphml)
                print("✅ GraphML 파일 복사 완료!")
        except Exception as e:
            print(f"⚠️ GraphML 비교 실패: {e}")
            if not os.path.exists(target_graphml):
                shutil.copy2(source_graphml, target_graphml)
                print("✅ GraphML 파일 복사 완료!")

    # 10. 임베딩 생성
    print("\n🧮 10단계: 임베딩 생성")
    
    # GraphML 파일 확인
    graphml_path = f"{output_directory}/kg_graphml/{keyword}_graph_with_numeric_id.graphml"
    if not os.path.exists(graphml_path):
        print(f"❌ GraphML 파일이 없습니다: {graphml_path}")
        print("⚠️ GraphML 파일이 없어도 계속 진행합니다. (임베딩은 생성되지 않을 수 있음)")
    else:
        # GraphML 파일에서 노드/엣지 수 확인
        try:
            import networkx as nx
            with open(graphml_path, "rb") as f:
                KG = nx.read_graphml(f)
            print(f"📊 GraphML 파일 확인: {len(KG.nodes)}개 노드, {len(KG.edges)}개 엣지")
            
            # 노드 타입 확인
            node_types = {}
            for node in KG.nodes:
                node_type = KG.nodes[node].get("type", "unknown")
                node_types[node_type] = node_types.get(node_type, 0) + 1
            print(f"📊 노드 타입 분포: {node_types}")
            
            if len(KG.nodes) == 0:
                print("⚠️ 경고: GraphML 파일에 노드가 없습니다!")
            if len(KG.edges) == 0:
                print("⚠️ 경고: GraphML 파일에 엣지가 없습니다!")
        except Exception as e:
            print(f"⚠️ GraphML 파일 확인 실패: {e}")
    
    # 임베딩 파일이 이미 존재하는지 확인
    embedding_files = [
        f"{keyword}_eventTrue_conceptTrue_all-MiniLM-L6-v2_node_faiss.index",
        f"{keyword}_eventTrue_conceptTrue_node_list.pkl",
        f"{keyword}_text_faiss.index"
    ]
    
    # 엣지 임베딩 파일도 확인
    encoder_model_name = os.getenv('DEFAULT_EMBEDDING_MODEL', "sentence-transformers/all-MiniLM-L6-v2")
    encoder_model_short = encoder_model_name.split('/')[-1]
    edge_embedding_file = f"{keyword}_eventTrue_conceptTrue_{encoder_model_short}_edge_faiss.index"
    
    # GraphML에 엣지가 있는지 확인
    has_edges = False
    if os.path.exists(graphml_path):
        try:
            import networkx as nx
            with open(graphml_path, "rb") as f:
                KG_check = nx.read_graphml(f)
            has_edges = len(KG_check.edges) > 0
        except:
            pass
    
    # 엣지 임베딩 파일 존재 확인
    edge_embedding_exists = os.path.exists(f"{output_directory}/precompute/{edge_embedding_file}")
    
    # 기본 임베딩 파일 존재 확인
    basic_files_exist = check_files_exist(embedding_files, f"{output_directory}/precompute")
    
    # GraphML에 엣지가 있는데 엣지 임베딩이 없으면 다시 생성
    need_regenerate = False
    if has_edges and not edge_embedding_exists:
        print(f"⚠️ GraphML에 엣지가 있지만 엣지 임베딩 파일이 없습니다. ({edge_embedding_file})")
        print("⚠️ 임베딩을 다시 생성합니다.")
        need_regenerate = True
    elif not basic_files_exist:
        need_regenerate = True
    
    if basic_files_exist and not need_regenerate:
        print("✅ 임베딩 파일이 이미 존재합니다. 생성을 건너뜁니다.")
    else:
        if need_regenerate:
            # 기존 임베딩 파일 삭제 (선택적)
            import glob
            precompute_dir = f"{output_directory}/precompute"
            if os.path.exists(precompute_dir):
                for pattern in [f"{keyword}_*_faiss.index", f"{keyword}_*.pkl"]:
                    for file in glob.glob(os.path.join(precompute_dir, pattern)):
                        try:
                            os.remove(file)
                            print(f"🗑️ 기존 임베딩 파일 삭제: {os.path.basename(file)}")
                        except:
                            pass
        try:
            from sentence_transformers import SentenceTransformer
            from atlas_rag.vectorstore.embedding_model import SentenceEmbedding
            from atlas_rag.vectorstore.create_graph_index import create_embeddings_and_index
            
            # Sentence Transformer 모델 로드
            encoder_model_name = os.getenv('DEFAULT_EMBEDDING_MODEL', "sentence-transformers/all-MiniLM-L6-v2")
            print(f"🔄 {encoder_model_name} 모델을 로딩 중...")
            
            sentence_model = SentenceTransformer(
                encoder_model_name, 
                trust_remote_code=True, 
                model_kwargs={'device_map': "auto"}
            )
            sentence_encoder = SentenceEmbedding(sentence_model)
            
            # create_embeddings_and_index 사용
            print("🔄 create_embeddings_and_index 실행 중...")
            create_embeddings_and_index(
                sentence_encoder=sentence_encoder,
                model_name=encoder_model_name,
                working_directory=output_directory,
                keyword=keyword,
                include_events=True,
                include_concept=True,
                normalize_embeddings=True,
                text_batch_size=40,
                node_and_edge_batch_size=256
            )
            print("✅ 임베딩 생성 완료!")
        except Exception as e:
            import traceback
            print(f"❌ 임베딩 생성 실패: {e}")
            print(f"❌ 상세 오류:\n{traceback.format_exc()}")
            # 임베딩 생성 실패해도 파이프라인은 계속 진행 (경고만)
            print("⚠️ 임베딩 생성 실패했지만 파이프라인은 계속 진행합니다.")

    
    # 11. 임베딩이 포함된 CSV 파일 생성
    print("\n🔍 11단계: 임베딩이 포함된 CSV 파일 생성")
    emb_csv_files = [
        f"triples_csv/triple_nodes_{keyword}_from_json_with_emb.csv",
        f"triples_csv/text_nodes_{keyword}_from_json_with_emb.csv",
        f"triples_csv/triple_edges_{keyword}_from_json_with_concept_with_emb.csv"
    ]
    if check_files_exist(emb_csv_files, output_directory):
        print("✅ 임베딩이 포함된 CSV 파일들이 이미 존재합니다. 생성을 건너뜁니다.")
    else:
        try:
            from sentence_transformers import SentenceTransformer
            from atlas_rag.vectorstore.embedding_model import SentenceEmbedding
            
            # Sentence Transformer 모델 로드
            encoder_model_name = os.getenv('DEFAULT_EMBEDDING_MODEL', "sentence-transformers/all-MiniLM-L6-v2")
            print(f"🔄 {encoder_model_name} 모델을 로딩 중...")
            
            sentence_model = SentenceTransformer(
                encoder_model_name, 
                trust_remote_code=True, 
                model_kwargs={'device_map': "auto"}
            )
            sentence_encoder = SentenceEmbedding(sentence_model)
            
            # CSV 파일 경로 설정
            node_csv_without_emb = f"{output_directory}/triples_csv/triple_nodes_{keyword}_from_json_without_emb.csv"
            node_csv_file = f"{output_directory}/triples_csv/triple_nodes_{keyword}_from_json_with_emb.csv"
            edge_csv_without_emb = f"{output_directory}/concept_csv/triple_edges_{keyword}_from_json_with_concept.csv"
            edge_csv_file = f"{output_directory}/triples_csv/triple_edges_{keyword}_from_json_with_concept_with_emb.csv"
            text_node_csv_without_emb = f"{output_directory}/triples_csv/text_nodes_{keyword}_from_json.csv"
            text_node_csv = f"{output_directory}/triples_csv/text_nodes_{keyword}_from_json_with_emb.csv"
            
            # 임베딩을 CSV 파일에 추가
            sentence_encoder.compute_kg_embedding(
                node_csv_without_emb=node_csv_without_emb,
                node_csv_file=node_csv_file,
                edge_csv_without_emb=edge_csv_without_emb,
                edge_csv_file=edge_csv_file,
                text_node_csv_without_emb=text_node_csv_without_emb,
                text_node_csv=text_node_csv,
                batch_size=2048
            )
            print("✅ 임베딩이 포함된 CSV 파일 생성 완료!")
        except Exception as e:
            print(f"❌ 임베딩 CSV 파일 생성 실패: {e}")
            return False
    
    # 12. FAISS 인덱스 생성
    print("\n🔍 12단계: FAISS 인덱스 생성")
    # precompute 폴더에서 FAISS 인덱스 파일 확인
    precompute_dir = f"{output_directory}/precompute"
    
    # GraphML에 엣지가 있는지 확인
    has_edges = False
    edge_count = 0
    graphml_path = f"{output_directory}/kg_graphml/{keyword}_graph_with_numeric_id.graphml"
    if os.path.exists(graphml_path):
        try:
            import networkx as nx
            with open(graphml_path, "rb") as f:
                KG_check = nx.read_graphml(f)
            edge_count = len(KG_check.edges)
            has_edges = edge_count > 0
            print(f"📊 GraphML 확인: {len(KG_check.nodes)}개 노드, {edge_count}개 엣지")
        except Exception as e:
            print(f"⚠️ GraphML 확인 실패: {e}")
    
    # 필수 FAISS 파일 목록
    required_faiss_files = [
        f"{keyword}_eventTrue_conceptTrue_all-MiniLM-L6-v2_node_faiss.index",
        f"{keyword}_text_faiss.index"
    ]
    
    # 엣지가 있으면 엣지 인덱스도 필수
    edge_faiss_file = f"{keyword}_eventTrue_conceptTrue_all-MiniLM-L6-v2_edge_faiss.index"
    if has_edges:
        required_faiss_files.append(edge_faiss_file)
        print(f"📊 GraphML에 {edge_count}개 엣지가 있으므로 엣지 FAISS 인덱스가 필요합니다.")
    else:
        print(f"⚠️ GraphML에 엣지가 없습니다. 엣지 FAISS 인덱스는 생성되지 않습니다.")
    
    # precompute 폴더의 파일들 확인
    existing_files = []
    missing_files = []
    for file in required_faiss_files:
        file_path = f"{precompute_dir}/{file}"
        if os.path.exists(file_path):
            existing_files.append(file)
        else:
            missing_files.append(file)
    
    print(f"📊 FAISS 인덱스 파일 상태: {len(existing_files)}/{len(required_faiss_files)} 존재")
    if missing_files:
        print(f"❌ 누락된 FAISS 인덱스 파일:")
        for file in missing_files:
            print(f"   - {file}")
    
    # 엣지가 있는데 엣지 인덱스가 없으면 에러
    if has_edges and edge_faiss_file in missing_files:
        print(f"❌ 오류: GraphML에 {edge_count}개 엣지가 있지만 엣지 FAISS 인덱스 파일이 없습니다!")
        print(f"❌ 이는 임베딩 생성 단계에서 엣지 필터링 문제가 발생했을 가능성이 있습니다.")
        print(f"❌ 디버깅을 위해 10단계(임베딩 생성)를 다시 실행하거나 엣지 필터링 로직을 확인하세요.")
        return False
    
    if len(existing_files) == len(required_faiss_files):
        print(f"✅ 모든 필수 FAISS 인덱스 파일이 존재합니다. 인덱스 생성을 건너뜁니다.")
    else:
        print(f"⚠️ 일부 FAISS 인덱스 파일이 없습니다. 인덱스를 생성합니다.")
        try:
            from atlas_rag.vectorstore.create_neo4j_index import create_faiss_index
            
            create_faiss_index(
                output_directory=output_directory,
                filename_pattern=keyword,
                index_type="HNSW,Flat",
                faiss_gpu=False
            )
            print("✅ FAISS 인덱스 생성 완료!")
        except Exception as e:
            print(f"❌ FAISS 인덱스 생성 실패: {e}")
            return False
    
    # 13. Neo4j 임포트 (해시 ID + concept을 속성으로 저장)
    print("\n🗄️ 13단계: Neo4j 임포트 (해시 ID + concept을 속성으로 저장)")
    
    try:
        import subprocess
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['LANG'] = 'ko_KR.UTF-8'
        env['LC_ALL'] = 'ko_KR.UTF-8'
        env['NEO4J_DATABASE'] = os.getenv('NEO4J_DATABASE', 'neo4j')
        env['KEYWORD'] = keyword
        
        # API 서버에서 실행될 때를 고려하여 경로 설정
        script_path = "neo4j_with_hash_ids_and_concept_attributes.py"
        if not os.path.exists(script_path):
            script_path = "BE/neo4j_with_hash_ids_and_concept_attributes.py"
        
        result = subprocess.run([
            sys.executable, script_path, "--keyword", keyword
        ], capture_output=True, text=True, encoding='utf-8', errors='ignore', env=env, check=True, cwd=".")
        print("✅ Neo4j 임포트 완료!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Neo4j 임포트 실패: {e}")
        print(f"오류 출력: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Neo4j 임포트 실패: {e}")
        return False
    
    # 14. GDS 그래프 프로젝션
    print("\n🕸️ 14단계: GDS 그래프 프로젝션")
    
    try:
        import subprocess
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['LANG'] = 'ko_KR.UTF-8'
        env['LC_ALL'] = 'ko_KR.UTF-8'
        env['NEO4J_DATABASE'] = os.getenv('NEO4J_DATABASE', 'neo4j')
        env['KEYWORD'] = keyword
        
        # API 서버에서 실행될 때를 고려하여 경로 설정
        script_path = "experiment/create_gds_graph.py"
        if not os.path.exists(script_path):
            script_path = "BE/experiment/create_gds_graph.py"
        
        result = subprocess.run([
            sys.executable, script_path
        ], capture_output=True, text=True, encoding='utf-8', errors='ignore', env=env, check=True, cwd=".")
        print("✅ GDS 그래프 프로젝션 완료!")
    except subprocess.CalledProcessError as e:
        print(f"❌ GDS 그래프 프로젝션 실패: {e}")
        print(f"오류 출력: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ GDS 그래프 프로젝션 실패: {e}")
        return False
    
    print("\n🎉 ATLAS 전체 파이프라인 완료!")
    print(f"📁 결과물 위치: {output_directory}")
    print("💡 이제 concept이 노드 속성으로 저장되었습니다!")
    print("💡 'python experiment/run_questions_v2.py'를 실행해서 하이브리드 RAG를 사용할 수 있습니다!")
    
    return True

if __name__ == "__main__":
    import sys
    
    # 명령행 인수로 시작 단계와 키워드 받기
    start_step = 0
    keyword = None
    
    if len(sys.argv) > 1:
        try:
            start_step = int(sys.argv[1])
            print(f"📋 시작 단계: {start_step}")
        except ValueError:
            # 숫자가 아니면 키워드로 간주
            keyword = sys.argv[1]
            print(f"📋 사용할 키워드: {keyword}")
    
    if len(sys.argv) > 2:
        keyword = sys.argv[2]
        print(f"📋 사용할 키워드: {keyword}")
    
    success = test_atlas_pipeline(start_step, keyword)
    if success:
        print("\n✅ 모든 단계가 성공적으로 완료되었습니다!")
    else:
        print("\n❌ 일부 단계에서 오류가 발생했습니다.")
