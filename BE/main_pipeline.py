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
from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
from atlas_rag.kg_construction.triple_config import ProcessingConfig
from atlas_rag.llm_generator import LLMGenerator
from openai import OpenAI
from transformers import pipeline

# UTF-8 로깅 설정
from atlas_rag.utils.utf8_logging import setup_utf8_logging

# UTF-8 로깅 초기화
setup_utf8_logging()

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
        keyword = os.getenv('KEYWORD', 'contract_v5')
    
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
            model_name = os.getenv('DEFAULT_MODEL', 'gpt-4.1-mini')
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
            model_name = os.getenv('DEFAULT_MODEL', 'gpt-4.1-mini')
        
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
        
        if check_files_exist(triple_files, f"{output_directory}/kg_extraction"):
            print("✅ 트리플 추출 파일들이 이미 존재합니다. 추출을 건너뜁니다.")
        else:
            try:
                kg_extractor.run_extraction()
                print("✅ 트리플 추출 완료!")
            except Exception as e:
                print(f"❌ 트리플 추출 실패: {e}")
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
    if check_files_exist(graphml_files, f"{output_directory}/kg_graphml"):
        print("✅ GraphML 파일이 이미 존재합니다. 생성을 건너뜁니다.")
    else:
        try:
            if kg_extractor is None:
                print("❌ kg_extractor가 정의되지 않았습니다. 8단계부터 시작하려면 이전 단계를 먼저 실행하세요.")
                return False
            kg_extractor.convert_to_graphml()
            print("✅ GraphML 생성 완료!")
        except Exception as e:
            print(f"❌ GraphML 생성 실패: {e}")
            return False

    # 9. 숫자 ID 추가
    print("\n🔢 9단계: 숫자 ID 추가")
    
    # 숫자 ID 파일이 이미 존재하는지 확인
    numeric_id_files = [
        f"triple_nodes_{keyword}_from_json_without_emb_with_numeric_id.csv",
        f"triple_edges_{keyword}_from_json_without_emb_with_numeric_id.csv",
        f"text_nodes_{keyword}_from_json_with_numeric_id.csv"
    ]
    if check_files_exist(numeric_id_files, f"{output_directory}/triples_csv"):
        print("✅ 숫자 ID 파일이 이미 존재합니다. 생성을 건너뜁니다.")
    else:
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
    if os.path.exists(source_graphml) and not os.path.exists(target_graphml):
        shutil.copy2(source_graphml, target_graphml)
        print("✅ GraphML 파일 복사 완료!")

    # 10. 임베딩 생성
    print("\n🧮 10단계: 임베딩 생성")
    
    # 임베딩 파일이 이미 존재하는지 확인
    embedding_files = [
        f"{keyword}_eventTrue_conceptTrue_all-MiniLM-L6-v2_node_faiss.index",
        f"{keyword}_eventTrue_conceptTrue_node_list.pkl",
        f"{keyword}_text_faiss.index"
    ]
    if check_files_exist(embedding_files, f"{output_directory}/precompute"):
        print("✅ 임베딩 파일이 이미 존재합니다. 생성을 건너뜁니다.")
    else:
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
            print(f"❌ 임베딩 생성 실패: {e}")
            return False

    
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
    faiss_files = [
        f"{keyword}_eventTrue_conceptTrue_all-MiniLM-L6-v2_node_faiss.index",
        f"{keyword}_eventTrue_conceptTrue_all-MiniLM-L6-v2_edge_faiss.index",
        f"{keyword}_text_faiss.index"
    ]
    
    # precompute 폴더의 파일들 확인
    existing_files = []
    for file in faiss_files:
        if os.path.exists(f"{precompute_dir}/{file}"):
            existing_files.append(file)
    
    if len(existing_files) == len(faiss_files):
        print("✅ FAISS 인덱스 파일이 이미 존재합니다. 인덱스 생성을 건너뜁니다.")
    else:
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
