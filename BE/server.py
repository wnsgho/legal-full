#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import sys
import json
import logging
import shutil
import uuid
import time
import requests
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 위험 분석 모듈 import
from riskAnalysis.risk_analysis_api import router as risk_analysis_router

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# UTF-8 로깅 설정
from atlas_rag.utils.utf8_logging import setup_utf8_logging

# UTF-8 로깅 초기화
setup_utf8_logging()
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

# 환경변수 확인
print(f"🔍 NEO4J_DATABASE: {os.getenv('NEO4J_DATABASE')}")
print(f"🔍 NEO4J_URI: {os.getenv('NEO4J_URI')}")
print(f"🔍 NEO4J_USER: {os.getenv('NEO4J_USER')}")

# 전역 변수
rag_system = None
neo4j_driver = None
pipeline_status = {}  # 파이프라인 실행 상태 관리
uploaded_files = {}   # 업로드된 파일 관리

# 업로드 디렉토리 설정 (프로젝트 루트의 uploads 폴더)
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Pydantic 모델들
class PipelineRequest(BaseModel):
    start_step: int = 0
    keyword: Optional[str] = None

class PipelineResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    question: str
    max_tokens: int = 8192
    temperature: float = 0.5
    chat_mode: str = "rag"  # "rag" 또는 "openai"
    file_id: str = None  # 파일 ID (선택사항)

class ChatResponse(BaseModel):
    success: bool
    answer: str
    context_count: int
    processing_time: float

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

class FileUploadResponse(BaseModel):
    success: bool
    file_id: str
    filename: str
    message: str

class PipelineStatusResponse(BaseModel):
    success: bool
    status: str
    progress: int
    message: str
    data: Optional[Dict[str, Any]] = None

def restore_uploaded_files():
    """서버 시작 시 업로드 디렉토리의 파일들을 스캔하여 uploaded_files 복구"""
    global uploaded_files
    
    if not UPLOAD_DIR.exists():
        return
    
    # 파일들을 수정 시간순으로 정렬하여 가장 최근 파일만 복구
    files_with_time = []
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            files_with_time.append((file_path, file_path.stat().st_mtime))
    
    # 수정 시간순으로 정렬 (최신순)
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    # 가장 최근 파일만 복구
    if files_with_time:
        file_path, _ = files_with_time[0]
        filename = file_path.name
        if '_' in filename:
            file_id = filename.split('_')[0]
            original_filename = '_'.join(filename.split('_')[1:])
            
            # 파일 정보 복구
            uploaded_files[file_id] = {
                "filename": original_filename,
                "file_path": str(file_path),
                "upload_time": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                "file_size": file_path.stat().st_size
            }
            
            logger.info(f"✅ 가장 최근 업로드 파일 복구: {original_filename} (ID: {file_id})")

def load_risk_checklist():
    """위험조항 체크리스트 로드"""
    try:
        # BE 폴더 기준으로 위험조항.txt 파일 찾기
        risk_file = Path(__file__).parent / "위험조항.txt"
        
        if risk_file.exists():
            with open(risk_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    risk_items = [item.strip() for item in content.split('\n') if item.strip()]
                    return '\n'.join([f"{i+1}. {item}" for i, item in enumerate(risk_items)])
        else:
            logger.warning(f"⚠️ 위험조항.txt 파일을 찾을 수 없습니다: {risk_file.absolute()}")
            return "위험조항 체크리스트를 로드할 수 없습니다."
    except Exception as e:
        logger.error(f"❌ 위험조항 체크리스트 로드 실패: {e}")
        return "위험조항 체크리스트를 로드할 수 없습니다."

def find_existing_keyword():
    """기존 임베딩 데이터가 있는 키워드 찾기 (.env 키워드 우선, 그 다음 최근 업로드 파일)"""
    import_dir = Path(os.getenv('IMPORT_DIRECTORY', 'BE/import'))
    logger.info(f"🔍 임베딩 데이터 탐색 중... import_dir: {import_dir.absolute()}")
    
    if not import_dir.exists():
        logger.warning(f"❌ import 디렉토리가 존재하지 않습니다: {import_dir.absolute()}")
        return None
    
    # 1. .env에 설정된 키워드 우선 확인
    env_keyword = os.getenv('KEYWORD')
    if env_keyword:
        keyword_dir = import_dir / env_keyword
        if keyword_dir.exists():
            precompute_dir = keyword_dir / os.getenv('PRECOMPUTE_DIRECTORY', 'precompute')
            if precompute_dir.exists():
                faiss_files = list(precompute_dir.glob("*_faiss.index"))
                if faiss_files:
                    logger.info(f"✅ .env에 설정된 키워드의 임베딩 데이터 발견: {env_keyword}")
                    return env_keyword
                else:
                    logger.info(f"⚠️ .env 키워드 {env_keyword}의 precompute 디렉토리는 있지만 FAISS 파일이 없습니다")
            else:
                logger.info(f"⚠️ .env 키워드 {env_keyword}의 precompute 디렉토리가 없습니다")
        else:
            logger.info(f"⚠️ .env 키워드 {env_keyword}의 디렉토리가 없습니다")
    else:
        logger.info("ℹ️ .env에 KEYWORD가 설정되지 않았습니다")
    
    # 2. 가장 최근 업로드 파일의 키워드 확인
    if uploaded_files:
        # 업로드된 파일 중 가장 최근 파일의 키워드 확인
        latest_file_id = max(uploaded_files.keys(), key=lambda k: uploaded_files[k]['upload_time'])
        latest_file_keyword = f"contract_{latest_file_id}"
        
        # 해당 키워드의 임베딩 데이터가 있는지 확인
        keyword_dir = import_dir / latest_file_keyword
        if keyword_dir.exists():
            precompute_dir = keyword_dir / os.getenv('PRECOMPUTE_DIRECTORY', 'precompute')
            if precompute_dir.exists():
                faiss_files = list(precompute_dir.glob("*_faiss.index"))
                if faiss_files:
                    logger.info(f"✅ 가장 최근 업로드 파일의 임베딩 데이터 발견: {latest_file_keyword}")
                    return latest_file_keyword
                else:
                    logger.info(f"⚠️ 최근 파일 {latest_file_keyword}의 precompute 디렉토리는 있지만 FAISS 파일이 없습니다")
            else:
                logger.info(f"⚠️ 최근 파일 {latest_file_keyword}의 precompute 디렉토리가 없습니다")
    
    # 3. 기존 방식으로 찾기 (수정 시간순)
    logger.info(" 최근 파일에 임베딩이 없어서 기존 방식으로 탐색...")
    
    # import 폴더에서 키워드 찾기 (수정 시간순으로 정렬)
    keyword_dirs = []
    for keyword_dir in import_dir.iterdir():
        if keyword_dir.is_dir():
            logger.info(f"📁 키워드 디렉토리 발견: {keyword_dir.name}")
            precompute_dir = keyword_dir / os.getenv('PRECOMPUTE_DIRECTORY', 'precompute')
            if precompute_dir.exists():
                # FAISS 인덱스 파일이 있는지 확인
                faiss_files = list(precompute_dir.glob("*_faiss.index"))
                if faiss_files:
                    # 수정 시간을 기준으로 정렬
                    mtime = keyword_dir.stat().st_mtime
                    keyword_dirs.append((mtime, keyword_dir.name))
    
    if keyword_dirs:
        # 수정 시간순으로 정렬 (최신순)
        keyword_dirs.sort(key=lambda x: x[0], reverse=True)
        latest_keyword = keyword_dirs[0][1]
        logger.info(f"✅ 기존 임베딩 데이터 발견 (최신순): {latest_keyword}")
        return latest_keyword
    
    logger.warning("❌ 임베딩 데이터를 찾을 수 없습니다.")
    return None

def check_and_load_existing_data():
    """서버 시작 시 기존 Neo4j 데이터 확인 및 로드"""
    global rag_system, neo4j_driver
    
    try:
        logger.info("🔍 기존 Neo4j 데이터 확인 중...")
        
        # 먼저 Neo4j 연결 테스트
        try:
            from neo4j import GraphDatabase
            neo4j_uri = os.getenv('NEO4J_URI', 'neo4j://127.0.0.1:7687')
            neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
            neo4j_password = os.getenv('NEO4J_PASSWORD', '')
            neo4j_database = os.getenv('NEO4J_DATABASE')
            
            print(f"🔍 Neo4j 연결 정보:")
            print(f"   - URI: {neo4j_uri}")
            print(f"   - USER: {neo4j_user}")
            print(f"   - DATABASE: {neo4j_database}")
            
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            
            # Neo4j에서 노드 수 확인
            with driver.session(database=neo4j_database) as session:
                result = session.run("MATCH (n) RETURN count(n) as node_count")
                node_count = result.single()["node_count"]
                
                if node_count > 0:
                    logger.info(f"✅ 기존 Neo4j 데이터 발견: {node_count}개 노드")
                    
                    # 기존 임베딩 데이터가 있는 키워드 찾기
                    existing_keyword = find_existing_keyword()
                    if existing_keyword:
                        # 환경변수에 키워드 설정
                        os.environ['KEYWORD'] = existing_keyword
                        logger.info(f"🔑 키워드 설정: {existing_keyword}")
                        
                        # RAG 시스템 로드 시도
                        try:
                            # 환경변수 재확인
                            print(f"🔍 RAG 시스템 로드 전 환경변수 확인:", flush=True)
                            print(f"🔍 NEO4J_DATABASE: {os.getenv('NEO4J_DATABASE')}", flush=True)
                            print(f"🔍 NEO4J_URI: {os.getenv('NEO4J_URI')}", flush=True)
                            
                            from experiment.run_questions_v3_with_concept import load_enhanced_rag_system
                            enhanced_lkg_retriever, hippo_retriever, llm_generator, neo4j_driver = load_enhanced_rag_system()
                            
                            # RAG 시스템 설정
                            rag_system = {
                                "enhanced_lkg_retriever": enhanced_lkg_retriever,
                                "hippo_retriever": hippo_retriever,
                                "llm_generator": llm_generator
                            }
                            
                            logger.info("✅ 기존 RAG 시스템 로드 완료")
                            return True
                            
                        except Exception as rag_error:
                            logger.warning(f"⚠️ RAG 시스템 로드 실패: {rag_error}")
                            return False
                    else:
                        logger.info("ℹ️ 임베딩 데이터를 찾을 수 없습니다. 파이프라인을 실행하세요.")
                        return False
                        
                else:
                    logger.info("ℹ️ Neo4j에 데이터가 없습니다. 새로 파이프라인을 실행하세요.")
                    return False
                    
        except Exception as neo4j_error:
            logger.warning(f"⚠️ Neo4j 연결 실패: {neo4j_error}")
            return False
            
    except Exception as e:
        logger.warning(f"⚠️ 기존 데이터 로드 실패: {e}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 함수"""
    # 시작 시
    logger.info("🚀 AutoSchemaKG 백엔드 서버 시작 중...")
    restore_uploaded_files()
    
    # 기존 Neo4j 데이터 확인 및 로드
    data_loaded = check_and_load_existing_data()
    if not data_loaded:
        logger.info("ℹ️ 기존 데이터가 없습니다. 파일을 업로드하고 파이프라인을 실행하세요.")
    
    yield
    # 종료 시
    logger.info("🛑 AutoSchemaKG 백엔드 서버 종료 중...")
    
    # Neo4j 연결 정리
    if neo4j_driver:
        neo4j_driver.close()
        logger.info("✅ Neo4j 연결 정리 완료")

# FastAPI 앱 생성
app = FastAPI(
    title="AutoSchemaKG Backend API",
    description="지식그래프 기반 RAG 시스템 백엔드 API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 위험 분석 라우터 추가
app.include_router(risk_analysis_router)

def load_rag_system():
    """RAG 시스템 로드"""
    global rag_system, neo4j_driver
    
    try:
        from experiment.run_questions_v3_with_concept import load_enhanced_rag_system
        
        enhanced_lkg_retriever, hippo_retriever, llm_generator, neo4j_driver = load_enhanced_rag_system()
        
        rag_system = {
            "enhanced_lkg_retriever": enhanced_lkg_retriever,
            "hippo_retriever": hippo_retriever,
            "llm_generator": llm_generator
        }
        
        logger.info("✅ RAG 시스템 로드 완료")
        return True
        
    except Exception as e:
        logger.error(f"❌ RAG 시스템 로드 실패: {e}")
        return False

# API 엔드포인트들
@app.get("/", response_model=HealthResponse)
async def root():
    """루트 엔드포인트 - 서버 상태 확인"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="2.0.0"
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """챗봇 질문 처리 - 두 가지 방식 지원 (RAG vs OpenAI 기본)"""
    start_time = datetime.now()

    try:
        # 쿼리 파라미터나 헤더에서 채팅 방식을 결정 (기본값: rag)
        chat_mode = "rag"  # 기본값은 RAG 시스템

        # 요청 본문에 chat_mode가 있으면 사용
        if hasattr(request, 'chat_mode'):
            chat_mode = request.chat_mode

        if chat_mode == "rag":
            # RAG 시스템 방식
            return await chat_rag(request, start_time)
        elif chat_mode == "openai":
            # OpenAI 기본 방식
            return await chat_openai_basic(request, start_time)
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 채팅 모드입니다.")

    except Exception as e:
        logger.error(f"챗봇 처리 실패: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()

        return ChatResponse(
            success=False,
            answer=f"오류가 발생했습니다: {str(e)}",
            context_count=0,
            processing_time=processing_time
        )

async def chat_rag(request: ChatRequest, start_time: datetime) -> ChatResponse:
    """RAG 시스템을 사용한 채팅"""
    try:
        # RAG 시스템이 로드되지 않은 경우 로드 시도
        if rag_system is None:
            if not load_rag_system():
                raise HTTPException(status_code=500, detail="RAG 시스템을 로드할 수 없습니다.")

        # 질문 처리
        from experiment.run_questions_v3_with_concept import concept_enhanced_hybrid_retrieve

        # Concept 활용 하이브리드 검색 실행
        search_result = concept_enhanced_hybrid_retrieve(
            request.question,
            rag_system["enhanced_lkg_retriever"],
            rag_system["hippo_retriever"],
            rag_system["llm_generator"],
            neo4j_driver
        )

        # 검색 결과 처리
        if search_result and len(search_result) == 2:
            sorted_context, context_ids = search_result
            context_count = len(context_ids) if context_ids else 0
        else:
            sorted_context = search_result if search_result else None
            context_count = 0

        if sorted_context:
            # 위험조항 체크리스트 로드
            risk_checklist = load_risk_checklist()

            # 시스템 프롬프트 설정
            system_instruction = (
                "당신은 대한민국의 고급 계약서 분석 전문가입니다. 추출된 정보와 질문을 꼼꼼히 분석하고 답변해야 합니다. "
                "지식 그래프 정보가 충분하지 않다면 자신의 지식을 활용해서 답변할 수 있습니다. "
                "답변은 'Thought: '로 시작하여 추론 과정을 단계별로 설명하고, "
                "'Answer: '로 끝나며 간결하고 명확한 답변을 제공해야 합니다. "
                "모든 답변은 한국어로 해주세요.\n\n"
                f"=== 계약서 위험조항 체크리스트 ===\n{risk_checklist}\n"
                "위 체크리스트를 참고하여 계약서의 잠재적 위험요소를 종합적으로 분석하세요."
            )

            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"{sorted_context}\n\n{request.question}"},
            ]

            result = rag_system["llm_generator"].generate_response(
                messages,
                max_new_tokens=request.max_tokens,
                temperature=request.temperature,
                validate_function=None
            )
        else:
            result = "관련 컨텍스트를 찾을 수 없어 답변을 생성할 수 없습니다."

        processing_time = (datetime.now() - start_time).total_seconds()

        return ChatResponse(
            success=True,
            answer=result if result else "답변을 생성할 수 없습니다.",
            context_count=context_count,
            processing_time=processing_time
        )

    except Exception as e:
        logger.error(f"RAG 채팅 처리 실패: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()

        return ChatResponse(
            success=False,
            answer=f"RAG 채팅 오류: {str(e)}",
            context_count=0,
            processing_time=processing_time
        )

async def chat_openai_basic(request: ChatRequest, start_time: datetime) -> ChatResponse:
    """간단한 OpenAI 기본 채팅"""
    try:
        # 간단한 OpenAI 채팅 스크립트 실행
        from experiment.simple_openai_chat import SimpleOpenAIChat

        # 기본적으로 최근 파일 사용 (file_id가 지정되지 않은 경우)
        file_id = getattr(request, 'file_id', None)

        # OpenAI 채팅 실행
        chat_instance = SimpleOpenAIChat()
        result = chat_instance.chat(request.question, file_id)

        processing_time = (datetime.now() - start_time).total_seconds()

        if result.get("success", False):
            return ChatResponse(
                success=True,
                answer=result["answer"],
                context_count=0,  # OpenAI 기본은 컨텍스트 카운트 없음
                processing_time=processing_time
            )
        else:
            return ChatResponse(
                success=False,
                answer=f"OpenAI 채팅 오류: {result.get('error', '알 수 없는 오류')}",
                context_count=0,
                processing_time=processing_time
            )

    except Exception as e:
        logger.error(f"OpenAI 기본 채팅 처리 실패: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()

        return ChatResponse(
            success=False,
            answer=f"OpenAI 기본 채팅 오류: {str(e)}",
            context_count=0,
            processing_time=processing_time
        )

@app.post("/analyze-risks", response_model=ChatResponse)
async def analyze_contract_risks(request: ChatRequest):
    """계약서 위험조항 전용 분석"""
    start_time = datetime.now()
    
    try:
        # RAG 시스템이 로드되지 않은 경우 로드 시도
        if rag_system is None:
            if not load_rag_system():
                raise HTTPException(status_code=500, detail="RAG 시스템을 로드할 수 없습니다.")
        
        # Concept 활용 하이브리드 검색 실행
        from experiment.run_questions_v3_with_concept import concept_enhanced_hybrid_retrieve
        
        sorted_context = concept_enhanced_hybrid_retrieve(
            request.question, 
            rag_system["enhanced_lkg_retriever"], 
            rag_system["hippo_retriever"],
            rag_system["llm_generator"],
            neo4j_driver,
            topN=50
        )
        
        if sorted_context:
            # 위험조항 체크리스트 로드
            risk_checklist = load_risk_checklist()
            
            # 위험조항 분석 전용 시스템 프롬프트
            system_instruction = (
                "당신은 대한민국의 계약서 위험조항 분석 전문가입니다. "
                "제공된 위험조항 체크리스트를 기반으로 계약서를 철저히 분석하세요.\n\n"
                "분석 시 다음 구조로 답변하세요:\n"
                "1. **발견된 위험요소**: 체크리스트 기준으로 발견된 위험조항들\n"
                "2. **위험도 평가**: 각 위험요소의 위험도 (매우 높음/높음/중간/낮음)\n"
                "3. **영향 당사자**: 매수인/매도인/양 당사자\n"
                "4. **개선 권고사항**: 구체적인 계약서 수정 제안\n"
                "5. **종합 평가**: 전체적인 위험 수준과 주요 우려사항\n\n"
                f"=== 계약서 위험조항 체크리스트 ===\n{risk_checklist}\n"
                "위 체크리스트의 각 항목을 계약서 내용과 대조하여 분석하세요."
            )
            
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"계약서 내용:\n{sorted_context}\n\n분석 요청: {request.question}"},
            ]
            
            result = rag_system["llm_generator"].generate_response(
                messages, 
                max_new_tokens=request.max_tokens, 
                temperature=request.temperature
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 위험조항 분석 완료 (소요시간: {processing_time:.2f}초)")
            
            return ChatResponse(
                success=True,
                answer=result,
                context_count=len(sorted_context) if isinstance(sorted_context, list) else 0,
                processing_time=processing_time
            )
        else:
            logger.warning("⚠️ 검색 결과가 없습니다.")
            return ChatResponse(
                success=False,
                answer="계약서 내용을 찾을 수 없습니다. 파이프라인을 먼저 실행해주세요.",
                context_count=0,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
    except Exception as e:
        logger.error(f"❌ 위험조항 분석 실패: {e}")
        return ChatResponse(
            success=False,
            answer=f"위험조항 분석 중 오류가 발생했습니다: {str(e)}",
            context_count=0,
            processing_time=(datetime.now() - start_time).total_seconds()
        )

@app.post("/pipeline/run", response_model=PipelineResponse)
async def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    """ATLAS 파이프라인 실행"""
    try:
        # 백그라운드에서 파이프라인 실행
        background_tasks.add_task(execute_pipeline, request.start_step, request.keyword)
        
        return PipelineResponse(
            success=True,
            message="파이프라인이 백그라운드에서 실행 중입니다.",
            data={"start_step": request.start_step, "keyword": request.keyword}
        )
        
    except Exception as e:
        logger.error(f"파이프라인 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def execute_pipeline(start_step: int, keyword: Optional[str], pipeline_id: str = None):
    """파이프라인 실행 함수 (subprocess 방식)"""
    global pipeline_status
    
    print(f"🚀 subprocess로 파이프라인 실행 시작 - keyword: {keyword}, start_step: {start_step}")
    logger.info(f"🚀 subprocess로 파이프라인 실행 시작 - keyword: {keyword}, start_step: {start_step}")
    
    if pipeline_id:
        pipeline_status[pipeline_id] = {
            "status": "running",
            "progress": 0,
            "message": "🚀 파이프라인 실행을 시작했습니다. 계약서를 분석하고 있습니다...",
            "start_time": datetime.now().isoformat(),
            "success": None,
            "rag_system_ready": False
        }
        print(f"📊 파이프라인 상태 초기화 완료 - ID: {pipeline_id}")
        logger.info(f"📊 파이프라인 상태 초기화 완료 - ID: {pipeline_id}")
    
    try:
        import subprocess
        import sys
        
        # BE 디렉토리에서 실행
        be_dir = Path(__file__).parent
        cmd = [sys.executable, "main_pipeline.py", str(start_step), keyword]
        
        print(f"📋 subprocess 명령어: {' '.join(cmd)}")
        print(f"📂 실행 디렉토리: {be_dir}")
        logger.info(f"📋 subprocess 명령어: {' '.join(cmd)}")
        logger.info(f"📂 실행 디렉토리: {be_dir}")
        
        # 환경변수 설정
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['LANG'] = 'ko_KR.UTF-8'
        env['LC_ALL'] = 'ko_KR.UTF-8'
        # env['KEYWORD'] = os.getenv('KEYWORD')
        env['KEYWORD'] = keyword  # keyword 환경변수 설정
        
        if pipeline_id:
            pipeline_status[pipeline_id]["progress"] = 25
            pipeline_status[pipeline_id]["message"] = "📋 파이프라인 프로세스를 시작하고 있습니다..."
            print("📊 파이프라인 진행률 업데이트: 25%")
            logger.info("📊 파이프라인 진행률 업데이트: 25%")
        
        # subprocess로 파이프라인 실행
        result = subprocess.run(
            cmd,
            cwd=be_dir,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            env=env,
            timeout=3600  # 1시간 타임아웃
        )
        
        print(f"📋 subprocess 결과 코드: {result.returncode}")
        print(f"📝 stdout: {result.stdout}")
        print(f"📝 stderr: {result.stderr}")
        logger.info(f"📋 subprocess 결과 코드: {result.returncode}")
        logger.info(f"📝 stdout: {result.stdout}")
        logger.info(f"📝 stderr: {result.stderr}")
        
        success = result.returncode == 0
        
        if success:
            print("✅ subprocess 파이프라인 실행 완료")
            logger.info("✅ subprocess 파이프라인 실행 완료")
            
            # 파이프라인 완료 후 RAG 시스템 자동 로드
            print("🔄 RAG 시스템 자동 로드 중...")
            logger.info("🔄 RAG 시스템 자동 로드 중...")
            if check_and_load_existing_data():
                print("✅ 파이프라인 완료 후 RAG 시스템 로드 성공")
                logger.info("✅ 파이프라인 완료 후 RAG 시스템 로드 성공")
            else:
                print("⚠️ 파이프라인 완료 후 RAG 시스템 로드 실패")
                logger.warning("⚠️ 파이프라인 완료 후 RAG 시스템 로드 실패")
            
            if pipeline_id:
                pipeline_status[pipeline_id] = {
                    "status": "completed",
                    "progress": 100,
                    "message": "✅ 파이프라인 실행이 성공적으로 완료되었습니다. RAG 시스템이 준비되었습니다.",
                    "end_time": datetime.now().isoformat(),
                    "success": True,
                    "rag_system_ready": True,
                    "completion_time": datetime.now().isoformat()
                }
                print(f"📊 파이프라인 상태 업데이트: 완료 - ID: {pipeline_id}")
                print(f"📊 파이프라인 상태 내용: {pipeline_status[pipeline_id]}")
                logger.info(f"📊 파이프라인 상태 업데이트: 완료 - ID: {pipeline_id}")
                logger.info(f"📊 파이프라인 상태 내용: {pipeline_status[pipeline_id]}")
        else:
            print("❌ subprocess 파이프라인 실행 실패")
            logger.error("❌ subprocess 파이프라인 실행 실패")
            if pipeline_id:
                pipeline_status[pipeline_id] = {
                    "status": "failed",
                    "progress": 0,
                    "message": "❌ 파이프라인 실행이 실패했습니다. 로그를 확인하고 다시 시도해주세요.",
                    "end_time": datetime.now().isoformat(),
                    "success": False,
                    "rag_system_ready": False
                }
                print(f"📊 파이프라인 상태 업데이트: 실패 - ID: {pipeline_id}")
                logger.error(f"📊 파이프라인 상태 업데이트: 실패 - ID: {pipeline_id}")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("⏰ subprocess 파이프라인 실행 타임아웃")
        logger.error("⏰ subprocess 파이프라인 실행 타임아웃")
        
        if pipeline_id:
            pipeline_status[pipeline_id] = {
                "status": "failed",
                "progress": 0,
                "message": "⏰ 파이프라인 실행이 타임아웃되었습니다. 파일이 너무 크거나 복잡할 수 있습니다.",
                "end_time": datetime.now().isoformat(),
                "success": False,
                "rag_system_ready": False
            }
            print(f"📊 파이프라인 상태 업데이트: 타임아웃 - ID: {pipeline_id}")
            logger.error(f"📊 파이프라인 상태 업데이트: 타임아웃 - ID: {pipeline_id}")
        
        return False
        
    except Exception as e:
        print(f"❌ subprocess 파이프라인 실행 중 오류: {e}")
        print(f"❌ 오류 타입: {type(e).__name__}")
        import traceback
        print(f"❌ 상세 오류 정보:\n{traceback.format_exc()}")
        logger.error(f"subprocess 파이프라인 실행 중 오류: {e}")
        logger.error(f"오류 타입: {type(e).__name__}")
        logger.error(f"상세 오류 정보:\n{traceback.format_exc()}")
        
        if pipeline_id:
            pipeline_status[pipeline_id] = {
                "status": "failed",
                "progress": 0,
                "message": f"❌ 파이프라인 실행 중 오류가 발생했습니다: {str(e)}",
                "end_time": datetime.now().isoformat(),
                "success": False,
                "rag_system_ready": False
            }
            print(f"📊 파이프라인 상태 업데이트: 오류 - ID: {pipeline_id}")
            logger.error(f"📊 파이프라인 상태 업데이트: 오류 - ID: {pipeline_id}")
        
        return False

@app.post("/upload/contract", response_model=FileUploadResponse)
async def upload_contract(file: UploadFile = File(...)):
    """계약서 파일 업로드"""
    try:
        # 파일 ID 생성
        file_id = str(uuid.uuid4())
        
        # 파일 저장
        file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 업로드된 파일 정보 저장
        uploaded_files[file_id] = {
            "filename": file.filename,
            "file_path": str(file_path),
            "upload_time": datetime.now().isoformat(),
            "file_size": len(content)
        }
        
        logger.info(f"파일 업로드 완료: {file.filename} (ID: {file_id})")
        
        return FileUploadResponse(
            success=True,
            file_id=file_id,
            filename=file.filename,
            message="파일이 성공적으로 업로드되었습니다."
        )
        
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pipeline/run-with-file", response_model=PipelineResponse)
async def run_pipeline_with_file(
    file_id: str = Form(...),
    start_step: int = Form(1),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """업로드된 파일로 파이프라인 실행"""
    try:
        logger.info(f"파이프라인 실행 요청 - file_id: {file_id}")
        logger.info(f"현재 uploaded_files 키들: {list(uploaded_files.keys())}")
        
        if file_id not in uploaded_files:
            logger.error(f"파일을 찾을 수 없습니다. 요청된 file_id: {file_id}")
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        file_info = uploaded_files[file_id]
        file_path = file_info["file_path"]
        
        # 파일을 example_data 디렉토리로 복사 (환경변수 기반)
        example_data_dir = Path(os.getenv('DATA_DIRECTORY', 'BE/example_data'))
        example_data_dir.mkdir(exist_ok=True)
        
        # 파일 확장자에 따라 처리
        file_ext = Path(file_path).suffix.lower()
        if file_ext == '.json':
            # JSON 파일인 경우 내용 확인 후 ATLAS 형식으로 변환
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # ATLAS가 기대하는 형식으로 변환
            if isinstance(json_data, list) and len(json_data) > 0 and 'text' in json_data[0]:
                # 이미 ATLAS 형식인 경우
                atlas_data = json_data
            elif isinstance(json_data, dict) and 'content' in json_data:
                # 업로드된 JSON에서 content 추출
                content = json_data['content']
                atlas_data = [
                    {
                        "id": "1",
                        "text": content,
                        "metadata": {
                            "lang": "ko",
                            "filename": file_info["filename"],
                            "upload_time": file_info["upload_time"]
                        }
                    }
                ]
            else:
                # 직접적인 JSON 내용인 경우
                content = json.dumps(json_data, ensure_ascii=False, indent=2)
                atlas_data = [
                    {
                        "id": "1",
                        "text": content,
                        "metadata": {
                            "lang": "ko",
                            "filename": file_info["filename"],
                            "upload_time": file_info["upload_time"]
                        }
                    }
                ]
            
            target_path = example_data_dir / f"contract_{file_id}.json"
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(atlas_data, f, ensure_ascii=False, indent=2)
            
            keyword = f"contract_{file_id}"
        elif file_ext in ['.txt', '.md']:
            # 텍스트/마크다운 파일인 경우 md_data 폴더에 저장 (파이프라인에서 변환)
            if file_ext == '.md':
                # 마크다운 파일은 md_data 폴더에 저장
                md_data_dir = example_data_dir / "md_data"
                md_data_dir.mkdir(exist_ok=True)
                target_path = md_data_dir / f"contract_{file_id}{file_ext}"
            else:
                # 텍스트 파일은 example_data에 직접 저장
                target_path = example_data_dir / f"contract_{file_id}{file_ext}"
            
            shutil.copy2(file_path, target_path)
            keyword = f"contract_{file_id}"
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")
        
        # 파이프라인 ID 생성
        pipeline_id = str(uuid.uuid4())
        
        # 백그라운드에서 파이프라인 실행 (마크다운 변환 포함)
        actual_start_step = 0 if start_step == 1 else start_step
        background_tasks.add_task(execute_pipeline, actual_start_step, keyword, pipeline_id)
        
        return PipelineResponse(
            success=True,
            message="파이프라인이 백그라운드에서 실행 중입니다.",
            data={
                "pipeline_id": pipeline_id,
                "keyword": keyword,
                "file_info": file_info
            }
        )
        
    except Exception as e:
        logger.error(f"파이프라인 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pipeline/status/{pipeline_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(pipeline_id: str):
    """파이프라인 실행 상태 조회"""
    try:
        print(f"🔍 파이프라인 상태 조회 요청 - ID: {pipeline_id}")
        print(f"🔍 현재 pipeline_status 키들: {list(pipeline_status.keys())}")
        
        if pipeline_id not in pipeline_status:
            print(f"❌ 파이프라인을 찾을 수 없음 - ID: {pipeline_id}")
            raise HTTPException(status_code=404, detail="파이프라인을 찾을 수 없습니다.")
        
        status_info = pipeline_status[pipeline_id]
        print(f"🔍 파이프라인 상태 정보: {status_info}")
        
        # 상태 정보에 추가 메타데이터 포함
        enhanced_status = {
            **status_info,
            "pipeline_id": pipeline_id,
            "timestamp": datetime.now().isoformat(),
            "rag_system_loaded": rag_system is not None
        }
        
        return PipelineStatusResponse(
            success=True,
            status=status_info["status"],
            progress=status_info["progress"],
            message=status_info["message"],
            data=enhanced_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파이프라인 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    """시스템 상태 조회"""
    try:
        # Neo4j 연결 실제 테스트
        neo4j_connected = False
        if neo4j_driver:
            try:
                with neo4j_driver.session() as session:
                    result = session.run("RETURN 1 as test")
                    neo4j_connected = True
            except Exception as e:
                logger.warning(f"Neo4j 연결 테스트 실패: {e}")
                neo4j_connected = False
        
        status = {
            "rag_system_loaded": rag_system is not None,
            "neo4j_connected": neo4j_connected,  # 실제 연결 테스트 결과
            "timestamp": datetime.now().isoformat(),
            "neo4j_database": os.getenv('NEO4J_DATABASE'),
            "neo4j_uri": os.getenv('NEO4J_URI')
        }
        
        return {"success": True, "status": status}
        
    except Exception as e:
        logger.error(f"상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/neo4j/stats")
async def get_neo4j_stats(request: dict):
    """Neo4j 데이터베이스 통계 정보 조회"""
    try:
        # 요청에서 연결 정보 추출
        server_url = request.get("serverUrl", "neo4j://127.0.0.1:7687")
        username = request.get("username", "neo4j")
        password = request.get("password", "")
        database = request.get("database", "contract3")
        
        if not password:
            raise HTTPException(status_code=400, detail="Neo4j 비밀번호가 필요합니다.")
        
        # Neo4j 드라이버 생성
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(server_url, auth=(username, password))
        
        try:
            with driver.session(database=database) as session:
                # 노드 수 조회
                node_result = session.run("MATCH (n) RETURN count(n) as nodeCount")
                node_count = node_result.single()["nodeCount"]
                
                # 관계 수 조회
                relationship_result = session.run("MATCH ()-[r]->() RETURN count(r) as relationshipCount")
                relationship_count = relationship_result.single()["relationshipCount"]
                
                logger.info(f"Neo4j 통계 - 노드: {node_count}, 관계: {relationship_count}")
                
                return {
                    "success": True,
                    "nodeCount": node_count,
                    "relationshipCount": relationship_count,
                    "database": database
                }
                
        finally:
            driver.close()
            
    except Exception as e:
        logger.error(f"Neo4j 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@app.post("/api/neo4j/graph-data")
async def get_neo4j_graph_data(request: dict):
    """Neo4j 그래프 데이터 조회 (노드와 관계)"""
    try:
        # 요청에서 연결 정보 추출
        server_url = request.get("serverUrl", "neo4j://127.0.0.1:7687")
        username = request.get("username", "neo4j")
        password = request.get("password", "")
        database = request.get("database", "contract3")
        
        if not password:
            raise HTTPException(status_code=400, detail="Neo4j 비밀번호가 필요합니다.")

        # 요청에서 limit 파라미터 추출 (기본값 1000, 최대 5000)
        request_limit = int(request.get("limit", 1000))
        request_limit = max(100, min(request_limit, 5000))  # 100-5000 범위로 제한

        # Neo4j 드라이버 생성
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(server_url, auth=(username, password))

        try:
            with driver.session(database=database) as session:
                # 노드 데이터 조회 (요청 limit만큼 가져옴)
                node_result = session.run("MATCH (n) RETURN n LIMIT $limit", limit=request_limit)
                nodes = []
                for record in node_result:
                    node = record["n"]
                    nodes.append({
                        "id": node.id,
                        "labels": list(node.labels),
                        "properties": dict(node)
                    })

                # 관계 데이터 조회 (더 적은 수로 제한)
                relationship_result = session.run("MATCH ()-[r]->() RETURN r LIMIT $limit", limit=request_limit)
                relationships = []
                for record in relationship_result:
                    rel = record["r"]
                    relationships.append({
                        "id": rel.id,
                        "type": rel.type,
                        "start_node": rel.start_node.id,
                        "end_node": rel.end_node.id,
                        "properties": dict(rel)
                    })
                
                logger.info(f"Neo4j 그래프 데이터 - 노드: {len(nodes)}, 관계: {len(relationships)}, 요청 limit: {request_limit}")

                return {
                    "success": True,
                    "nodes": nodes,
                    "relationships": relationships,
                    "database": database,
                    "limit_used": request_limit,
                    "node_count": len(nodes),
                    "relationship_count": len(relationships)
                }
                
        finally:
            driver.close()
            
    except Exception as e:
        logger.error(f"Neo4j 그래프 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"그래프 데이터 조회 실패: {str(e)}")

@app.get("/files")
async def list_uploaded_files():
    """업로드된 파일 목록 조회"""
    try:
        files = []
        logger.info(f"현재 uploaded_files에 등록된 파일 수: {len(uploaded_files)}")
        logger.info(f"uploaded_files 키들: {list(uploaded_files.keys())}")
        
        for file_id, file_info in uploaded_files.items():
            logger.info(f"파일 정보 - ID: {file_id}, 파일명: {file_info.get('filename', 'N/A')}")
            files.append({
                "file_id": file_id,
                "filename": file_info["filename"],
                "upload_time": file_info["upload_time"],
                "file_size": file_info["file_size"],
                "file_path": file_info.get("file_path", "")
            })
        
        return {"success": True, "data": files}
        
    except Exception as e:
        logger.error(f"파일 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/{file_id}")
async def delete_uploaded_file(file_id: str):
    """업로드된 파일 삭제"""
    try:
        if file_id not in uploaded_files:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        file_info = uploaded_files[file_id]
        file_path = Path(file_info["file_path"])
        
        # 파일 삭제
        if file_path.exists():
            file_path.unlink()
        
        # 메모리에서 제거
        del uploaded_files[file_id]
        
        logger.info(f"파일 삭제 완료: {file_info['filename']}")
        
        return {"success": True, "message": "파일이 삭제되었습니다."}
        
    except Exception as e:
        logger.error(f"파일 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/history")
async def get_chat_history(limit: int = 10):
    """챗봇 대화 기록 조회"""
    try:
        qa_file_path = "qa_history_api.json"
        
        if not os.path.exists(qa_file_path):
            return {"success": True, "history": []}
        
        with open(qa_file_path, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
        
        # 최근 기록만 반환
        recent_history = qa_data[-limit:] if len(qa_data) > limit else qa_data
        
        return {"success": True, "history": recent_history}
        
    except Exception as e:
        logger.error(f"대화 기록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/history")
async def clear_chat_history():
    """챗봇 대화 기록 삭제"""
    try:
        qa_file_path = "qa_history_api.json"
        
        if os.path.exists(qa_file_path):
            os.remove(qa_file_path)
        
        return {"success": True, "message": "대화 기록이 삭제되었습니다."}
        
    except Exception as e:
        logger.error(f"대화 기록 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-and-run", response_model=PipelineResponse)
async def upload_and_run_pipeline(
    file: UploadFile = File(...),
    start_step: int = Form(1),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """파일 업로드와 파이프라인 실행을 한 번에 처리"""
    try:
        # 1. 파일 업로드
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 업로드된 파일 정보 저장
        uploaded_files[file_id] = {
            "filename": file.filename,
            "file_path": str(file_path),
            "upload_time": datetime.now().isoformat(),
            "file_size": len(content)
        }
        
        logger.info(f"파일 업로드 완료: {file.filename} (ID: {file_id})")
        
        # 2. 파이프라인 실행
        file_info = uploaded_files[file_id]
        file_path = file_info["file_path"]
        
        # 파일을 example_data 디렉토리로 복사 (환경변수 기반)
        example_data_dir = Path(os.getenv('DATA_DIRECTORY', 'BE/example_data'))
        example_data_dir.mkdir(exist_ok=True)
        
        # 파일 확장자에 따라 처리
        file_ext = Path(file_path).suffix.lower()
        if file_ext == '.json':
            # JSON 파일인 경우 그대로 복사
            target_path = example_data_dir / f"contract_{file_id}.json"
            shutil.copy2(file_path, target_path)
            keyword = f"contract_{file_id}"
        elif file_ext in ['.txt', '.md']:
            # 텍스트/마크다운 파일인 경우 md_data 폴더에 저장 (파이프라인에서 변환)
            if file_ext == '.md':
                # 마크다운 파일은 md_data 폴더에 저장
                md_data_dir = example_data_dir / "md_data"
                md_data_dir.mkdir(exist_ok=True)
                target_path = md_data_dir / f"contract_{file_id}{file_ext}"
            else:
                # 텍스트 파일은 example_data에 직접 저장
                target_path = example_data_dir / f"contract_{file_id}{file_ext}"
            
            shutil.copy2(file_path, target_path)
            keyword = f"contract_{file_id}"
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다.")
        
        # 파이프라인 ID 생성
        pipeline_id = str(uuid.uuid4())
        
        # 파이프라인 상태 초기화
        pipeline_status[pipeline_id] = {
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "file_info": file_info,
            "keyword": keyword
        }
        
        # 백그라운드에서 파이프라인 실행 (마크다운 변환 포함)
        actual_start_step = 0 if start_step == 1 else start_step
        background_tasks.add_task(execute_pipeline, actual_start_step, keyword, pipeline_id)
        
        logger.info(f"파이프라인 실행 시작: {pipeline_id} (파일: {file.filename})")
        
        return PipelineResponse(
            success=True,
            message="파이프라인이 백그라운드에서 실행 중입니다.",
            data={
                "pipeline_id": pipeline_id,
                "keyword": keyword,
                "file_info": file_info
            }
        )
        
    except Exception as e:
        logger.error(f"파일 업로드 및 파이프라인 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/docs")
async def get_api_docs():
    """API 문서 정보 반환"""
    return {
        "title": "AutoSchemaKG Backend API",
        "version": "2.0.0",
        "description": "지식그래프 기반 RAG 시스템 백엔드 API",
        "endpoints": {
            "health": "GET /health - 서버 상태 확인",
            "chat": "POST /chat - 챗봇 질문 처리",
            "analyze_risks": "POST /analyze-risks - 계약서 위험조항 분석",
            "upload_contract": "POST /upload/contract - 계약서 파일 업로드",
            "run_pipeline": "POST /pipeline/run - ATLAS 파이프라인 실행",
            "run_with_file": "POST /pipeline/run-with-file - 업로드된 파일로 파이프라인 실행",
            "upload_and_run": "POST /upload-and-run - 파일 업로드와 파이프라인 실행을 한 번에 처리",
            "pipeline_status": "GET /pipeline/status/{pipeline_id} - 파이프라인 실행 상태 조회",
            "system_status": "GET /status - 시스템 상태 조회",
            "list_files": "GET /files - 업로드된 파일 목록 조회",
            "delete_file": "DELETE /files/{file_id} - 업로드된 파일 삭제",
            "chat_history": "GET /chat/history - 챗봇 대화 기록 조회",
            "clear_history": "DELETE /chat/history - 챗봇 대화 기록 삭제",
            "risk_analysis": "POST /risk-analysis/analyze-contract - 독립적인 계약서 위험 분석",
            "risk_analysis_file": "POST /risk-analysis/analyze-uploaded-file - 업로드된 파일의 하이브리드 위험 분석",
            "risk_analysis_gpt": "POST /risk-analysis/analyze-gpt-only - GPT 전용 위험 분석",
            "risk_analysis_results": "GET /risk-analysis/saved - 저장된 위험 분석 결과 조회"
        },
        "swagger_ui": "/docs",
        "redoc": "/redoc"
    }

@app.post("/test-pipeline")
async def test_pipeline_direct():
    """파이프라인 직접 실행 테스트"""
    try:
        print("🧪 파이프라인 직접 실행 테스트 시작")
        logger.info("🧪 파이프라인 직접 실행 테스트 시작")
        
        # 현재 작업 디렉토리 확인
        print(f"📂 현재 작업 디렉토리: {os.getcwd()}")
        logger.info(f"📂 현재 작업 디렉토리: {os.getcwd()}")
        
        # 환경변수 확인
        print(f"🔑 KEYWORD: {os.getenv('KEYWORD', '없음')}")
        print(f"📊 DATA_DIRECTORY: {os.getenv('DATA_DIRECTORY', '없음')}")
        print(f"📦 OPENAI_API_KEY: {'있음' if os.getenv('OPENAI_API_KEY') else '없음'}")
        
        # 단계별 import 테스트
        print("📦 1단계: dotenv import 중...")
        from dotenv import load_dotenv
        print("✅ dotenv import 완료")
        
        print("📦 2단계: atlas_rag 모듈들 import 중...")
        from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
        print("✅ KnowledgeGraphExtractor import 완료")
        
        from atlas_rag.kg_construction.triple_config import ProcessingConfig
        print("✅ ProcessingConfig import 완료")
        
        from atlas_rag.llm_generator import LLMGenerator
        print("✅ LLMGenerator import 완료")
        
        print("📦 3단계: main_pipeline 모듈 import 중...")
        from main_pipeline import test_atlas_pipeline
        print("✅ main_pipeline import 완료")
        
        print("📦 4단계: test_atlas_pipeline 함수 실행 중...")
        success = test_atlas_pipeline(0, "test_contract")
        print(f"✅ test_atlas_pipeline 실행 완료: {success}")
        
        return {
            "success": success,
            "message": "파이프라인 테스트 완료",
            "current_dir": os.getcwd(),
            "env_vars": {
                "KEYWORD": os.getenv('KEYWORD'),
                "DATA_DIRECTORY": os.getenv('DATA_DIRECTORY'),
                "OPENAI_API_KEY": "있음" if os.getenv('OPENAI_API_KEY') else "없음"
            }
        }
        
    except Exception as e:
        print(f"❌ 파이프라인 테스트 실패: {e}")
        import traceback
        print(f"❌ 상세 오류:\n{traceback.format_exc()}")
        logger.error(f"파이프라인 테스트 실패: {e}")
        logger.error(f"상세 오류:\n{traceback.format_exc()}")
        
        return {
            "success": False,
            "message": f"파이프라인 테스트 실패: {str(e)}",
            "error": str(e)
        }

@app.post("/compare-answers")
async def compare_answers(
    question: str = Form(...),
    document_id: str = Form(...)
):
    """
    AutoSchemaKG와 OpenAI의 답변을 비교합니다.
    """
    try:
        logger.info(f"답변 비교 시작 - 질문: {question[:50]}..., 문서: {document_id}")
        
        # AutoSchemaKG 답변 가져오기
        atlas_start_time = time.time()
        atlas_response = requests.post(
            f"http://localhost:8000/chat",
            json={
                "question": question,
                "document_id": document_id
            },
            timeout=60
        )
        atlas_time = time.time() - atlas_start_time
        
        atlas_result = {
            "success": False,
            "answer": "",
            "contexts": [],
            "processing_time": atlas_time
        }
        
        if atlas_response.status_code == 200:
            atlas_data = atlas_response.json()
            atlas_result = {
                "success": True,
                "answer": atlas_data.get("answer", ""),
                "contexts": atlas_data.get("contexts", []),
                "processing_time": atlas_time,
                "context_count": len(atlas_data.get("contexts", []))
            }
        
        # OpenAI 답변 가져오기
        openai_result = await get_openai_answer(question, document_id)
        
        # 유사도 계산
        similarity = 0.0
        if atlas_result["success"] and openai_result["success"]:
            similarity = calculate_text_similarity(
                atlas_result["answer"], 
                openai_result["answer"]
            )
        
        # 결과 반환
        comparison_result = {
            "question": question,
            "document_id": document_id,
            "atlas_result": atlas_result,
            "openai_result": openai_result,
            "similarity": similarity,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"답변 비교 완료 - 유사도: {similarity:.3f}")
        return comparison_result
        
    except Exception as e:
        logger.error(f"답변 비교 실패: {e}")
        raise HTTPException(status_code=500, detail=f"답변 비교 실패: {str(e)}")

async def get_openai_answer(question: str, document_id: str) -> Dict[str, Any]:
    """
    OpenAI API를 통해 답변을 가져옵니다.
    """
    try:
        import openai
        
        # 문서 내용 가져오기
        document_path = UPLOAD_DIR / f"{document_id}.md"
        if not document_path.exists():
            return {
                "success": False,
                "error": "문서를 찾을 수 없습니다.",
                "answer": "",
                "processing_time": 0
            }
        
        with open(document_path, 'r', encoding='utf-8') as f:
            document_content = f.read()
        
        start_time = time.time()
        
        # OpenAI API 호출
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""
다음 계약서 내용을 바탕으로 질문에 답변해주세요.

계약서 내용:
{document_content}

질문: {question}

"""
        
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[

                {"role": "user", "content": prompt}
            ],
            max_tokens=8192,
            temperature=1.0
        )
        
        processing_time = time.time() - start_time
        answer = response.choices[0].message.content.strip()
        
        return {
            "success": True,
            "answer": answer,
            "processing_time": processing_time,
            "model": "gpt-4.1-mini",
            "tokens_used": response.usage.total_tokens if response.usage else 0
        }
        
    except Exception as e:
        logger.error(f"OpenAI API 호출 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "answer": "",
            "processing_time": 0
        }

def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    두 텍스트 간의 유사도를 계산합니다.
    """
    try:
        # 간단한 단어 기반 Jaccard 유사도
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
            
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
        
    except Exception as e:
        logger.error(f"유사도 계산 실패: {e}")
        return 0.0

@app.post("/batch-compare")
async def batch_compare_answers(
    questions_file: str = Form(...),
    document_id: str = Form(...),
    max_questions: Optional[int] = Form(None)
):
    """
    여러 질문에 대해 AutoSchemaKG와 OpenAI의 답변을 일괄 비교합니다.
    """
    try:
        logger.info(f"배치 비교 시작 - 질문 파일: {questions_file}, 문서: {document_id}")
        
        # 질문 파일 로드
        questions_path = Path(questions_file)
        if not questions_path.exists():
            raise HTTPException(status_code=404, detail="질문 파일을 찾을 수 없습니다.")
        
        with open(questions_path, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        questions = questions_data.get("questions", [])
        if max_questions:
            questions = questions[:max_questions]
        
        # 문서 내용 로드
        document_path = UPLOAD_DIR / f"{document_id}.md"
        if not document_path.exists():
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
        
        with open(document_path, 'r', encoding='utf-8') as f:
            document_content = f.read()
        
        # 비교 결과 저장
        comparison_results = []
        successful_comparisons = 0
        total_atlas_time = 0
        total_openai_time = 0
        total_similarity = 0
        
        for i, question_data in enumerate(questions, 1):
            question_id = question_data.get("question_id", i)
            question = question_data.get("question", "")
            expected_answer = question_data.get("answer", "")
            
            logger.info(f"질문 {i}/{len(questions)} 처리 중: {question[:50]}...")
            
            # AutoSchemaKG 답변 가져오기
            atlas_start_time = time.time()
            atlas_response = requests.post(
                f"http://localhost:8000/chat",
                json={
                    "question": question,
                    "document_id": document_id
                },
                timeout=60
            )
            atlas_time = time.time() - atlas_start_time
            
            atlas_result = {
                "success": False,
                "answer": "",
                "contexts": [],
                "processing_time": atlas_time
            }
            
            if atlas_response.status_code == 200:
                atlas_data = atlas_response.json()
                atlas_result = {
                    "success": True,
                    "answer": atlas_data.get("answer", ""),
                    "contexts": atlas_data.get("contexts", []),
                    "processing_time": atlas_time,
                    "context_count": len(atlas_data.get("contexts", []))
                }
            
            # OpenAI 답변 가져오기
            openai_result = await get_openai_answer_with_content(question, document_content)
            
            # 유사도 계산
            similarity = 0.0
            if atlas_result["success"] and openai_result["success"]:
                similarity = calculate_text_similarity(
                    atlas_result["answer"], 
                    openai_result["answer"]
                )
            
            # 결과 저장
            comparison_result = {
                "question_id": question_id,
                "question": question,
                "expected_answer": expected_answer,
                "atlas_result": atlas_result,
                "openai_result": openai_result,
                "similarity": similarity,
                "processing_time": {
                    "atlas": atlas_result.get("processing_time", 0),
                    "openai": openai_result.get("processing_time", 0)
                }
            }
            
            comparison_results.append(comparison_result)
            
            # 통계 업데이트
            if atlas_result["success"] and openai_result["success"]:
                successful_comparisons += 1
                total_atlas_time += atlas_result.get("processing_time", 0)
                total_openai_time += openai_result.get("processing_time", 0)
                total_similarity += similarity
        
        # 최종 결과 구성
        final_result = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "questions_file": questions_file,
                "document_id": document_id,
                "total_questions": len(questions),
                "max_questions": max_questions
            },
            "comparison_results": comparison_results,
            "analysis": {
                "summary": {
                    "total_questions": len(questions),
                    "successful_comparisons": successful_comparisons,
                    "success_rate": (successful_comparisons / len(questions)) * 100 if questions else 0,
                    "average_similarity": total_similarity / successful_comparisons if successful_comparisons > 0 else 0,
                    "average_atlas_time": total_atlas_time / successful_comparisons if successful_comparisons > 0 else 0,
                    "average_openai_time": total_openai_time / successful_comparisons if successful_comparisons > 0 else 0,
                    "time_difference": (total_atlas_time - total_openai_time) / successful_comparisons if successful_comparisons > 0 else 0
                }
            }
        }
        
        logger.info(f"배치 비교 완료 - 성공률: {final_result['analysis']['summary']['success_rate']:.1f}%")
        return final_result
        
    except Exception as e:
        logger.error(f"배치 비교 실패: {e}")
        raise HTTPException(status_code=500, detail=f"배치 비교 실패: {str(e)}")

async def get_openai_answer_with_content(question: str, document_content: str) -> Dict[str, Any]:
    """
    문서 내용을 직접 받아서 OpenAI API를 통해 답변을 가져옵니다.
    """
    try:
        import openai
        
        start_time = time.time()
        
        # OpenAI API 호출
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""
다음 계약서 내용을 바탕으로 질문에 답변해주세요.

계약서 내용:
{document_content}

질문: {question}

답변 시 다음 사항을 고려해주세요:
1. 계약서의 구체적인 조항을 인용하여 답변
2. 법적 관점에서 정확하고 상세한 분석 제공
3. 독소조항이나 위험 요소가 있다면 명확히 지적
4. 답변 근거가 되는 조항 번호나 내용을 구체적으로 제시
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 계약서 분석 전문가입니다. 주어진 계약서를 바탕으로 정확하고 상세한 분석을 제공해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.1
        )
        
        processing_time = time.time() - start_time
        answer = response.choices[0].message.content.strip()
        
        return {
            "success": True,
            "answer": answer,
            "processing_time": processing_time,
            "model": "gpt-4o",
            "tokens_used": response.usage.total_tokens if response.usage else 0
        }
        
    except Exception as e:
        logger.error(f"OpenAI API 호출 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "answer": "",
            "processing_time": 0
        }



# 전역 변수 초기화
risk_analysis_results = {}  # 위험 분석 결과 저장용 (별도 API로 실행)

# 서버 시작 시 기존 파일들을 uploaded_files에 등록
async def initialize_uploaded_files():
    """서버 시작 시 uploads 폴더의 기존 파일들을 uploaded_files에 등록"""
    try:
        uploads_dir = Path("uploads")
        if uploads_dir.exists():
            logger.info(f"uploads 폴더 스캔 시작: {uploads_dir}")
            for file_path in uploads_dir.glob("*"):
                if file_path.is_file():
                    # 파일명에서 UUID 추출 시도
                    filename = file_path.name
                    if "_" in filename:
                        # 파일명이 "uuid_filename" 형태인 경우
                        parts = filename.split("_", 1)
                        if len(parts) == 2:
                            file_id = parts[0]
                            original_filename = parts[1]
                        else:
                            # UUID가 아닌 경우 파일명을 그대로 사용
                            file_id = str(uuid.uuid4())
                            original_filename = filename
                    else:
                        # UUID가 없는 경우 새로 생성
                        file_id = str(uuid.uuid4())
                        original_filename = filename
                    
                    # 파일 정보 등록
                    uploaded_files[file_id] = {
                        "filename": original_filename,
                        "file_path": str(file_path),
                        "upload_time": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "file_size": file_path.stat().st_size
                    }
                    logger.info(f"기존 파일 등록: {file_id} -> {original_filename}")
            
            logger.info(f"총 {len(uploaded_files)}개 파일이 uploaded_files에 등록됨")
        else:
            logger.info("uploads 폴더가 존재하지 않음")
    except Exception as e:
        logger.error(f"기존 파일 등록 실패: {e}")

# 서버 시작 시 기존 파일들 등록
@app.on_event("startup")
async def startup_event():
    await initialize_uploaded_files()

@app.get("/risk-analysis/rag-contracts")
async def get_rag_contracts():
    """RAG가 구축된 계약서 목록 조회"""
    try:
        # 업로드된 파일 중에서 RAG가 구축된 것들만 필터링
        rag_contracts = []
        
        for file_id, file_info in uploaded_files.items():
            # 파일이 존재하고 RAG 시스템이 로드되어 있는지 확인
            if os.path.exists(file_info["file_path"]) and rag_system:
                rag_contracts.append({
                    "file_id": file_id,
                    "filename": file_info["filename"],
                    "uploaded_at": file_info.get("upload_time", file_info.get("uploaded_at", "")),
                    "file_size": os.path.getsize(file_info["file_path"]),
                    "file_type": file_info.get("file_type", "unknown")
                })
        
        # 최신순으로 정렬
        rag_contracts.sort(key=lambda x: x["uploaded_at"], reverse=True)
        
        return {
            "success": True,
            "data": rag_contracts,
            "total_count": len(rag_contracts)
        }
        
    except Exception as e:
        logger.error(f"RAG 계약서 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_id}/content")
async def get_file_content(file_id: str):
    """업로드된 파일의 내용 조회"""
    try:
        # 먼저 업로드된 파일에서 찾기
        if file_id in uploaded_files:
            file_info = uploaded_files[file_id]
            file_path = file_info["file_path"]
            
            if os.path.exists(file_path):
                # 파일 내용 읽기
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # UTF-8로 읽기 실패 시 다른 인코딩 시도
                    try:
                        with open(file_path, 'r', encoding='cp949') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                
                return {
                    "success": True,
                    "data": {
                        "file_id": file_id,
                        "filename": file_info["filename"],
                        "content": content,
                        "file_size": len(content),
                        "upload_time": file_info.get("upload_time", "")
                    }
                }
        
        # 업로드된 파일이 없으면 처리된 파일에서 찾기
        keyword = f"contract_{file_id}"
        import_dir = Path(os.getenv('IMPORT_DIRECTORY', 'BE/import'))
        processed_file_path = import_dir / keyword / f"{keyword}.json"
        
        if processed_file_path.exists():
            try:
                with open(processed_file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # JSON 데이터에서 텍스트 추출
                if isinstance(json_data, list) and len(json_data) > 0:
                    # ATLAS 형식의 JSON에서 텍스트 추출
                    content = '\n\n'.join([item.get('text', '') for item in json_data if item.get('text')])
                elif isinstance(json_data, dict):
                    # 단일 객체인 경우
                    content = json_data.get('text', json.dumps(json_data, ensure_ascii=False, indent=2))
                else:
                    content = json.dumps(json_data, ensure_ascii=False, indent=2)
                
                return {
                    "success": True,
                    "data": {
                        "file_id": file_id,
                        "filename": f"{keyword}.json",
                        "content": content,
                        "file_size": len(content),
                        "upload_time": datetime.fromtimestamp(processed_file_path.stat().st_mtime).isoformat()
                    }
                }
            except Exception as e:
                logger.error(f"처리된 파일 읽기 실패: {e}")
        
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 내용 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/risk-analysis/saved")
async def get_saved_risk_analysis_results():
    """저장된 위험 분석 결과 조회"""
    try:
        import json
        import os
        
        # 직접 JSON 파일 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, "riskAnalysis", "data")
        results_file = os.path.join(data_dir, "risk_analysis_results.json")
        
        print(f"🔍 저장된 위험 분석 결과 조회 시작", flush=True)
        print(f"🔍 results_file 경로: {results_file}", flush=True)
        print(f"🔍 results_file 존재 여부: {os.path.exists(results_file)}", flush=True)
        
        if not os.path.exists(results_file):
            print(f"🔍 results_file이 존재하지 않음", flush=True)
            return {
                "success": True,
                "data": {
                    "results": [],
                    "total_count": 0
                }
            }
        
        # JSON 파일 직접 읽기
        with open(results_file, 'r', encoding='utf-8') as f:
            all_results = json.load(f)
        
        print(f"🔍 로드된 결과 개수: {len(all_results)}", flush=True)
        
        if not all_results:
            print(f"🔍 저장된 분석 결과가 없음", flush=True)
            return {
                "success": True,
                "data": {
                    "results": [],
                    "total_count": 0
                }
            }
        
        # 최신순으로 정렬
        results_list = list(all_results.values())
        results_list.sort(
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )
        
        print(f"🔍 정렬된 결과 개수: {len(results_list)}", flush=True)
        
        return {
            "success": True,
            "data": {
                "results": results_list,
                "total_count": len(results_list)
            }
        }
    except Exception as e:
        print(f"🔍 저장된 위험 분석 결과 조회 실패: {e}", flush=True)
        logger.error(f"저장된 위험 분석 결과 조회 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": {
                "results": [],
                "total_count": 0
            }
        }

@app.get("/risk-analysis/{pipeline_id}")
async def get_risk_analysis_result(pipeline_id: str):
    """파이프라인 ID로 위험 분석 결과 조회"""
    try:
        analysis_id = f"risk_analysis_{pipeline_id}"
        
        if analysis_id not in risk_analysis_results:
            # 404 오류는 정상적인 상황이므로 로깅하지 않음
            raise HTTPException(status_code=404, detail="위험 분석 결과를 찾을 수 없습니다.")
        
        result = risk_analysis_results[analysis_id]
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException:
        # HTTPException은 다시 raise (404는 정상)
        raise
    except Exception as e:
        logger.error(f"위험 분석 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/risk-analysis")
async def get_all_risk_analysis_results():
    """모든 위험 분석 결과 조회"""
    try:
        return {
            "success": True,
            "data": list(risk_analysis_results.values())
        }
        
    except Exception as e:
        logger.error(f"위험 분석 결과 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/risk-analysis/saved/{file_id}")
async def get_saved_risk_analysis_by_file(file_id: str):
    """특정 파일의 저장된 위험 분석 결과 조회"""
    try:
        import json
        from pathlib import Path
        
        print(f"🔍 특정 파일의 저장된 위험 분석 결과 조회 시작 - file_id: {file_id}", flush=True)
        
        # data 폴더에서 직접 JSON 파일 읽기
        data_dir = Path(__file__).parent / "riskAnalysis" / "data"
        results_file = data_dir / "risk_analysis_results.json"
        
        if not results_file.exists():
            print(f"🔍 results_file이 존재하지 않음", flush=True)
            return {
                "success": True,
                "data": {
                    "results": [],
                    "total_count": 0
                }
            }
        
        # JSON 파일 직접 읽기
        with open(results_file, 'r', encoding='utf-8') as f:
            all_results = json.load(f)
        
        # 해당 파일의 모든 분석 결과 조회
        file_results = []
        
        for result_id, result in all_results.items():
            if result.get('file_id') == file_id:
                file_results.append(result)
        
        print(f"🔍 해당 파일의 분석 결과 개수: {len(file_results)}", flush=True)
        
        # 최신순으로 정렬
        file_results.sort(
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )
        
        return {
            "success": True,
            "data": {
                "results": file_results,
                "total_count": len(file_results)
            }
        }
    except Exception as e:
        print(f"🔍 특정 파일의 저장된 위험 분석 결과 조회 실패: {e}", flush=True)
        logger.error(f"파일별 저장된 위험 분석 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/risk-analysis/analyze-contract")
async def analyze_contract_risk(
    contract_text: str = Form(...),
    contract_name: str = Form("계약서"),
    selected_parts: str = Form("all")  # "all" 또는 "1,2,3" 형태
):
    """독립적인 계약서 위험 분석 (RAG 없이 AI 직접 비교 분석)"""
    try:
        print(f"🛡️ 독립적인 위험 분석 시작 - contract_name: {contract_name}")
        logger.info(f"🛡️ 독립적인 위험 분석 시작 - contract_name: {contract_name}")
        
        # LLM 생성기만 필요 (RAG 시스템 불필요)
        if not rag_system or not rag_system.get("llm_generator"):
            raise HTTPException(status_code=500, detail="LLM 생성기가 로드되지 않았습니다.")
        
        # 분석할 파트 결정
        if selected_parts == "all":
            parts_to_analyze = list(range(1, 11))  # 1-10 파트
        else:
            parts_to_analyze = [int(p.strip()) for p in selected_parts.split(",")]
        
        # 위험 체크리스트 로드
        risk_check_data = load_risk_checklist()
        
        # AI 직접 비교 분석 실행
        analysis_result = await _analyze_contract_with_ai(
            contract_text, 
            contract_name, 
            risk_check_data, 
            parts_to_analyze,
            rag_system["llm_generator"]
        )
        
        # 분석 결과 저장
        analysis_id = f"standalone_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        risk_analysis_results[analysis_id] = {
            "analysis_id": analysis_id,
            "pipeline_id": None,
            "file_id": None,
            "contract_name": contract_name,
            "analysis_result": analysis_result,
            "created_at": datetime.now().isoformat(),
            "analysis_type": "standalone_ai_analysis"
        }
        
        print(f"✅ 독립적인 AI 위험 분석 완료 - analysis_id: {analysis_id}")
        logger.info(f"✅ 독립적인 AI 위험 분석 완료 - analysis_id: {analysis_id}")
        
        return {
            "success": True,
            "message": "AI 직접 비교 분석이 완료되었습니다.",
            "data": {
                "analysis_id": analysis_id,
                "analysis_result": analysis_result,
                "analysis_type": "ai_direct_comparison"
            }
        }
        
    except Exception as e:
        logger.error(f"독립적인 AI 위험 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/risk-analysis/analyze-uploaded-file")
async def analyze_uploaded_file_risk(request: Request):
    """업로드된 파일에 대한 하이브리드 위험 분석 (RAG 시스템 필요)"""
    try:
        # JSON 요청 데이터 파싱
        try:
            request_data = await request.json()
            print(f"🔍 JSON 요청 데이터: {request_data}", flush=True)
        except:
            # Form 데이터로 시도
            form_data = await request.form()
            request_data = dict(form_data)
            print(f"🔍 Form 요청 데이터: {request_data}", flush=True)
        
        file_id = request_data.get("file_id")
        selected_parts = request_data.get("selected_parts", "all")
        
        print(f"🔍 파싱된 데이터 - file_id: {file_id}, selected_parts: {selected_parts}", flush=True)
        
        # 데이터 타입 확인
        print(f"🔍 file_id 타입: {type(file_id)}", flush=True)
        print(f"🔍 selected_parts 타입: {type(selected_parts)}", flush=True)
        
        print(f"🛡️ 업로드된 파일 하이브리드 위험 분석 시작 - file_id: {file_id}", flush=True)
        logger.info(f"🛡️ 업로드된 파일 하이브리드 위험 분석 시작 - file_id: {file_id}")
        
        # 파일 정보 확인
        print(f"🔍 현재 uploaded_files 키들: {list(uploaded_files.keys())}", flush=True)
        print(f"🔍 요청된 file_id: {file_id}", flush=True)
        print(f"🔍 uploaded_files 전체: {uploaded_files}", flush=True)
        
        if file_id not in uploaded_files:
            logger.error(f"파일을 찾을 수 없습니다. 요청된 file_id: {file_id}")
            logger.error(f"현재 uploaded_files 키들: {list(uploaded_files.keys())}")
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다. file_id: {file_id}")
        
        file_info = uploaded_files[file_id]
        print(f"🔍 file_info type: {type(file_info)}", flush=True)
        print(f"🔍 file_info: {file_info}", flush=True)
        
        # file_info가 문자열인 경우 처리
        if isinstance(file_info, str):
            print(f"🔍 file_info가 문자열입니다. JSON 파싱 시도...", flush=True)
            import json
            try:
                file_info = json.loads(file_info)
                print(f"🔍 JSON 파싱 후 file_info: {file_info}", flush=True)
            except:
                print(f"🔍 JSON 파싱 실패. file_info를 그대로 사용", flush=True)
        
        print(f"🔍 file_info 접근 시도 전 - type: {type(file_info)}", flush=True)
        try:
            file_path = file_info["file_path"]
            print(f"🔍 file_path 추출 성공: {file_path}", flush=True)
        except Exception as e:
            print(f"🔍 file_path 추출 실패: {e}", flush=True)
            print(f"🔍 file_info 내용: {file_info}", flush=True)
            raise
        
        # RAG 시스템 확인
        if not rag_system:
            raise HTTPException(status_code=500, detail="RAG 시스템이 로드되지 않았습니다. 파이프라인을 먼저 실행해주세요.")
        
        # 계약서 내용 읽기
        print(f"🔍 계약서 파일 읽기 시작: {file_path}", flush=True)
        contract_text = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    print(f"🔍 JSON 파일로 인식됨", flush=True)
                    json_data = json.load(f)
                    if isinstance(json_data, dict) and 'content' in json_data:
                        contract_text = json_data['content']
                        print(f"🔍 JSON content 추출 성공", flush=True)
                    else:
                        contract_text = json.dumps(json_data, ensure_ascii=False, indent=2)
                        print(f"🔍 JSON 전체 내용 사용", flush=True)
                else:
                    print(f"🔍 텍스트 파일로 인식됨", flush=True)
                    contract_text = f.read()
                    print(f"🔍 텍스트 파일 읽기 성공, 길이: {len(contract_text)}", flush=True)
        except Exception as e:
            print(f"🔍 파일 읽기 실패: {e}", flush=True)
            raise
        
        # 분석할 파트 결정
        print(f"🔍 분석할 파트 결정 시작", flush=True)
        if selected_parts == "all":
            parts_to_analyze = list(range(1, 11))  # 1-10 파트
            print(f"🔍 전체 파트 분석: {parts_to_analyze}", flush=True)
        else:
            parts_to_analyze = [int(p.strip()) for p in selected_parts.split(",")]
            print(f"🔍 선택된 파트 분석: {parts_to_analyze}", flush=True)
        
        # 하이브리드 위험 분석기 초기화
        print(f"🔍 하이브리드 위험 분석기 초기화 시작", flush=True)
        try:
            from riskAnalysis.hybrid_risk_analyzer import HybridSequentialRiskAnalyzer
            print(f"🔍 HybridSequentialRiskAnalyzer import 성공", flush=True)
            
            # 올바른 위험 체크 데이터 로드 (JSON 파일)
            import json
            with open("riskAnalysis/checkList/riskCheck.json", "r", encoding="utf-8") as f:
                risk_check_data = json.load(f)
            print(f"🔍 risk_check_data 로드 성공", flush=True)
            print(f"🔍 risk_check_data 타입: {type(risk_check_data)}", flush=True)
            print(f"🔍 analysisParts 존재: {'analysisParts' in risk_check_data}", flush=True)
            
            print(f"🔍 RAG 시스템 구성 요소 확인", flush=True)
            print(f"🔍 enhanced_lkg_retriever: {type(rag_system.get('enhanced_lkg_retriever'))}", flush=True)
            print(f"🔍 hippo_retriever: {type(rag_system.get('hippo_retriever'))}", flush=True)
            print(f"🔍 llm_generator: {type(rag_system.get('llm_generator'))}", flush=True)
            print(f"🔍 neo4j_driver: {type(neo4j_driver)}", flush=True)
            
            analyzer = HybridSequentialRiskAnalyzer(
                risk_check_data,
                rag_system["enhanced_lkg_retriever"],
                rag_system["hippo_retriever"],
                rag_system["llm_generator"],
                neo4j_driver
            )
            print(f"🔍 HybridSequentialRiskAnalyzer 생성 성공", flush=True)
        except Exception as e:
            print(f"🔍 하이브리드 위험 분석기 초기화 실패: {e}", flush=True)
            raise
        
        # 하이브리드 위험 분석 실행
        print(f"🔍 하이브리드 위험 분석 실행 시작", flush=True)
        try:
            if selected_parts == "all":
                # 전체 파트 분석
                analysis_result = await analyzer.analyze_all_parts_with_hybrid(
                    contract_text, 
                    file_info["filename"]
                )
                print(f"🔍 전체 파트 하이브리드 위험 분석 실행 성공", flush=True)
            else:
                # 선택된 파트만 분석
                analysis_result = await analyzer.analyze_selected_parts_with_hybrid(
                    contract_text, 
                    file_info["filename"],
                    parts_to_analyze
                )
                print(f"🔍 선택된 파트 하이브리드 위험 분석 실행 성공: {parts_to_analyze}", flush=True)
        except Exception as e:
            print(f"🔍 하이브리드 위험 분석 실행 실패: {e}", flush=True)
            raise
        
        # 분석 결과 저장
        analysis_id = f"file_{file_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_based_id = f"{file_info['filename']}_{timestamp}"
        
        result_data = {
            "analysis_id": analysis_id,
            "file_based_id": file_based_id,
            "pipeline_id": None,
            "file_id": file_id,
            "contract_name": file_info["filename"],
            "analysis_result": analysis_result,
            "created_at": datetime.now().isoformat(),
            "analysis_type": "file_hybrid_analysis"
        }
        
        # 메모리에 저장
        risk_analysis_results[analysis_id] = result_data
        
        # 영구 저장 (파일) - 파일명 기반으로 저장
        from riskAnalysis.data_persistence import data_manager
        save_success = data_manager.save_analysis_result(file_based_id, result_data)
        if save_success:
            print(f"✅ 분석 결과 영구 저장 완료: {file_based_id}")
            logger.info(f"✅ 분석 결과 영구 저장 완료: {file_based_id}")
        else:
            print(f"❌ 분석 결과 영구 저장 실패: {file_based_id}")
            logger.error(f"❌ 분석 결과 영구 저장 실패: {file_based_id}")
        
        print(f"✅ 업로드된 파일 하이브리드 위험 분석 완료 - analysis_id: {analysis_id}")
        logger.info(f"✅ 업로드된 파일 하이브리드 위험 분석 완료 - analysis_id: {analysis_id}")
        
        return {
            "success": True,
            "message": "하이브리드 위험 분석이 완료되었습니다.",
            "data": {
                "analysis_id": analysis_id,
                "analysis_result": analysis_result,
                "hybrid_search_enabled": True,
                "rag_system_used": True
            }
        }
        
    except Exception as e:
        logger.error(f"업로드된 파일 하이브리드 위험 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AI 직접 비교 분석 함수
async def _analyze_contract_with_ai(contract_text: str, contract_name: str, risk_check_data: dict, parts_to_analyze: list, llm_generator):
    """AI가 계약서 내용과 riskCheck를 직접 비교하여 분석"""
    import time
    start_time = time.time()
    
    part_results = []
    
    for part_number in parts_to_analyze:
        # 파트 데이터 추출
        part_data = next((p for p in risk_check_data["analysisParts"] if p["partNumber"] == part_number), None)
        if not part_data:
            continue
            
        print(f"📋 Part {part_number} 분석 중: {part_data['partTitle']}")
        
        # AI 직접 비교 분석
        part_result = await _analyze_part_with_ai(
            part_data, contract_text, llm_generator
        )
        
        part_results.append(part_result)
        
        # Rate limit 고려한 지연
        await asyncio.sleep(1.0)
    
    # 전체 분석 결과 통합
    total_time = time.time() - start_time
    overall_risk_score = sum(r["risk_score"] for r in part_results) / len(part_results) if part_results else 0.0
    
    return {
        "contract_name": contract_name,
        "analysis_date": datetime.now().isoformat(),
        "total_analysis_time": total_time,
        "overall_risk_score": overall_risk_score,
        "overall_risk_level": _determine_risk_level(overall_risk_score),
        "part_results": part_results,
        "summary": _generate_analysis_summary(part_results)
    }

async def _analyze_part_with_ai(part_data: dict, contract_text: str, llm_generator):
    """AI가 특정 파트를 직접 분석"""
    try:
        # AI 분석 프롬프트 구성
        analysis_prompt = f"""
계약서 내용을 분석하여 다음 위험 요소들을 평가해주세요:

**분석 파트**: {part_data['partTitle']}
**핵심 질문**: {part_data['coreQuestion']}
**주요 위험 패턴**: {part_data['topRiskPattern']}

**체크리스트**:
{chr(10).join([f"- {item}" for item in part_data['deepDiveChecklist']])}

**계약서 내용**:
{contract_text[:2000]}...

각 체크리스트 항목에 대해 다음을 평가해주세요:
1. 해당 항목이 계약서에 포함되어 있는가?
2. 포함되어 있다면 위험도는 얼마인가? (1-5점)
3. 구체적인 문제점이나 우려사항은 무엇인가?

JSON 형태로 응답해주세요:
{{
    "part_title": "{part_data['partTitle']}",
    "risk_score": 0-5,
    "risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
    "checklist_results": [
        {{
            "item": "체크리스트 항목",
            "found": true/false,
            "risk_score": 1-5,
            "issues": ["구체적인 문제점들"]
        }}
    ],
    "recommendations": ["권고사항들"]
}}
"""
        
        # AI 분석 실행
        response = await llm_generator.generate_response(analysis_prompt)
        
        # JSON 파싱 시도
        try:
            import json
            result = json.loads(response)
        except:
            # JSON 파싱 실패 시 기본 구조 생성
            result = {
                "part_title": part_data['partTitle'],
                "risk_score": 2.0,
                "risk_level": "MEDIUM",
                "checklist_results": [],
                "recommendations": ["AI 분석 결과를 파싱할 수 없습니다."]
            }
        
        return {
            "part_number": part_data['partNumber'],
            "part_title": part_data['partTitle'],
            "risk_score": result.get("risk_score", 2.0),
            "risk_level": result.get("risk_level", "MEDIUM"),
            "checklist_results": result.get("checklist_results", []),
            "recommendations": result.get("recommendations", []),
            "analysis_time": 0.0
        }
        
    except Exception as e:
        print(f"❌ Part {part_data['partNumber']} AI 분석 실패: {e}")
        return {
            "part_number": part_data['partNumber'],
            "part_title": part_data['partTitle'],
            "risk_score": 0.0,
            "risk_level": "UNKNOWN",
            "checklist_results": [],
            "recommendations": [f"분석 실패: {str(e)}"],
            "analysis_time": 0.0
        }

def _determine_risk_level(risk_score: float) -> str:
    """위험도 점수에 따른 레벨 결정"""
    if risk_score >= 4.0:
        return "CRITICAL"
    elif risk_score >= 3.0:
        return "HIGH"
    elif risk_score >= 2.0:
        return "MEDIUM"
    else:
        return "LOW"

def _generate_analysis_summary(part_results: list) -> dict:
    """분석 요약 생성"""
    total_parts = len(part_results)
    high_risk_parts = len([r for r in part_results if r["risk_level"] in ["HIGH", "CRITICAL"]])
    critical_issues = [r["part_title"] for r in part_results if r["risk_level"] == "CRITICAL"]
    
    return {
        "total_parts_analyzed": total_parts,
        "high_risk_parts": high_risk_parts,
        "critical_issues": critical_issues
    }

async def get_file_content_by_id(file_id: str) -> str:
    """파일 ID로 파일 내용을 가져오는 함수"""
    try:
        if file_id not in uploaded_files:
            logger.error(f"파일을 찾을 수 없습니다. file_id: {file_id}")
            return None
        
        file_info = uploaded_files[file_id]
        file_path = file_info["file_path"]
        
        if not os.path.exists(file_path):
            logger.error(f"파일이 존재하지 않습니다. path: {file_path}")
            return None
        
        # 파일 내용 읽기
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # UTF-8로 읽기 실패 시 다른 인코딩 시도
            try:
                with open(file_path, 'r', encoding='cp949') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        return content
        
    except Exception as e:
        logger.error(f"파일 내용 조회 실패: {e}")
        return None

async def save_gpt_analysis_result(gpt_result: dict):
    """GPT 분석 결과를 저장하는 함수"""
    try:
        from riskAnalysis.data_persistence import RiskAnalysisDataManager
        
        # 데이터 매니저 초기화
        data_manager = RiskAnalysisDataManager()
        
        # 분석 ID 생성
        analysis_id = gpt_result.get("analysis_id", f"gpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # 결과 저장
        success = data_manager.save_analysis_result(analysis_id, gpt_result)
        
        if success:
            logger.info(f"GPT 분석 결과 저장 완료: {analysis_id}")
        else:
            logger.error(f"GPT 분석 결과 저장 실패: {analysis_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"GPT 분석 결과 저장 중 오류: {e}")
        return False

# GPT 전용 위험 분석 API
@app.post("/risk-analysis/analyze-gpt-only")
async def analyze_gpt_only(request: dict):
    """GPT만을 사용한 위험 분석"""
    try:
        file_id = request.get("file_id")
        if not file_id:
            return {"success": False, "error": "file_id가 필요합니다"}
        
        # 파일 내용 조회
        file_content = await get_file_content_by_id(file_id)
        if not file_content:
            return {"success": False, "error": "파일을 찾을 수 없습니다"}
        
        # SimpleGPTRiskAnalyzer import 및 사용
        from riskAnalysis.simple_gpt_risk_analyzer import SimpleGPTRiskAnalyzer
        
        # GPT 분석기 초기화
        analyzer = SimpleGPTRiskAnalyzer()
        
        # 계약서 분석
        result = analyzer.analyze_contract(
            contract_text=file_content,
            contract_name=f"contract_{file_id}"
        )
        
        # 결과를 하이브리드 분석과 동일한 형식으로 변환
        gpt_result = {
            "analysis_id": f"gpt_{file_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "file_id": file_id,
            "contract_name": f"GPT 분석 - {file_id}",
            "created_at": datetime.now().isoformat(),
            "analysis_type": "gpt_only",
            "analysis_result": {
                "overall_risk_score": 3.5,  # GPT 결과에서 추출하거나 기본값
                "part_results": [
                    {
                        "part_title": "GPT 전체 분석",
                        "risk_level": "MEDIUM",
                        "risk_score": 3.5,
                        "risk_clauses": ["GPT 분석에서 발견된 위험 조항들"],
                        "recommendations": ["GPT 분석 권고사항"],
                        "analysis_content": result.get("analysis_result", "")
                    }
                ],
                "total_analysis_time": result.get("analysis_time", 0),
                "summary": {
                    "total_parts_analyzed": 1,
                    "high_risk_parts": 0,
                    "critical_issues": [],
                    "gpt_analysis": result.get("analysis_result", "")
                }
            }
        }
        
        # 결과 저장
        await save_gpt_analysis_result(gpt_result)
        
        return {
            "success": True,
            "data": gpt_result,
            "message": "GPT 전용 분석이 완료되었습니다"
        }
        
    except Exception as e:
        logger.error(f"GPT 분석 실패: {str(e)}")
        return {"success": False, "error": f"GPT 분석 실패: {str(e)}"}

async def save_gpt_analysis_result(result: dict):
    """GPT 분석 결과 저장"""
    try:
        # GPT 분석 결과를 별도 파일에 저장
        gpt_results_file = "riskAnalysis/data/gpt_analysis_results.json"
        
        # 기존 결과 로드
        if os.path.exists(gpt_results_file):
            with open(gpt_results_file, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
        else:
            existing_results = []
        
        # 새 결과 추가
        existing_results.append(result)
        
        # 파일 저장
        with open(gpt_results_file, 'w', encoding='utf-8') as f:
            json.dump(existing_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"GPT 분석 결과 저장 완료: {result['analysis_id']}")
        
    except Exception as e:
        logger.error(f"GPT 분석 결과 저장 실패: {str(e)}")

@app.get("/risk-analysis/gpt-results")
async def get_gpt_analysis_results():
    """GPT 분석 결과 조회"""
    try:
        gpt_results_file = "riskAnalysis/data/gpt_analysis_results.json"
        
        if os.path.exists(gpt_results_file):
            with open(gpt_results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
        else:
            results = []
        
        return {
            "success": True,
            "data": {"results": results}
        }
        
    except Exception as e:
        logger.error(f"GPT 분석 결과 조회 실패: {str(e)}")
        return {"success": False, "error": f"GPT 분석 결과 조회 실패: {str(e)}"}

# OpenAI 기본 채팅 API
@app.post("/chat/openai-basic")
async def openai_basic_chat(request: ChatRequest):
    """OpenAI 기본 형식 채팅 (RAG 없이)"""
    try:
        if not request.question.strip():
            return {
                "success": False,
                "message": "질문을 입력해주세요."
            }
        
        # OpenAI API 호출
        import openai
        from openai import OpenAI
        
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # 업로드된 계약서 내용 가져오기
        contract_content = ""
        if uploaded_files:
            # 가장 최근 업로드된 파일의 내용 가져오기
            latest_file_id = max(uploaded_files.keys())
            file_info = uploaded_files[latest_file_id]
            file_path = UPLOAD_DIR / file_info['filename']
            
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        contract_content = f.read()
                    logger.info(f"계약서 내용 로드 성공: {file_info['filename']} ({len(contract_content)} 문자)")
                except Exception as e:
                    logger.error(f"계약서 내용 로드 실패: {str(e)}")
                    contract_content = ""
        
        # 메시지 구성 (시스템 프롬프트 없이 바로 질문과 계약서 내용 전달)
        if contract_content:
            messages = [
                {"role": "user", "content": f"다음은 분석할 계약서 내용입니다:\n\n{contract_content}\n\n이 계약서에 대해 다음 질문에 답변해주세요: {request.question}"}
            ]
        else:
            messages = [
                {"role": "user", "content": request.question}
            ]
        
        # OpenAI API 호출
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        answer = response.choices[0].message.content
        
        return {
            "success": True,
            "answer": answer,
            "context_count": 0,  # RAG를 사용하지 않으므로 0
            "processing_time": 0.0,
            "model": "gpt-4.1-mini",
            "method": "openai_basic"
        }
        
    except Exception as e:
        logger.error(f"OpenAI 기본 채팅 실패: {str(e)}")
        return {
            "success": False,
            "message": f"OpenAI 기본 채팅 실패: {str(e)}"
        }

# 특정 계약서를 위한 OpenAI 기본 채팅 API
@app.post("/chat/openai-basic/{file_id}")
async def openai_basic_chat_with_file(file_id: str, request: ChatRequest):
    """특정 계약서를 위한 OpenAI 기본 형식 채팅"""
    try:
        if not request.question.strip():
            return {
                "success": False,
                "message": "질문을 입력해주세요."
            }
        
        # OpenAI API 호출
        import openai
        from openai import OpenAI
        
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # 특정 계약서 내용 가져오기
        contract_content = ""
        if file_id in uploaded_files:
            file_info = uploaded_files[file_id]
            file_path = UPLOAD_DIR / file_info['filename']
            
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        contract_content = f.read()
                    logger.info(f"계약서 내용 로드 성공: {file_info['filename']} ({len(contract_content)} 문자)")
                except Exception as e:
                    logger.error(f"계약서 내용 로드 실패: {str(e)}")
                    contract_content = ""
        else:
            logger.warning(f"파일 ID {file_id}를 찾을 수 없습니다.")
        
        # 시스템 프롬프트 설정"""
        
        # 메시지 구성
        messages = [
            {"role": "user", "content": f"다음은 분석할 계약서 내용입니다:\n\n{contract_content}\n\n이 계약서에 대해 다음 질문에 답변해주세요: {request.question}"}
        ]
        
        
        # OpenAI API 호출
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        answer = response.choices[0].message.content
        
        return {
            "success": True,
            "answer": answer,
            "context_count": 0,  # RAG를 사용하지 않으므로 0
            "processing_time": 0.0,
            "model": "gpt-4.1-mini",
            "method": "openai_basic_with_file"
        }
        
    except Exception as e:
        logger.error(f"OpenAI 기본 채팅 실패: {str(e)}")
        return {
            "success": False,
            "message": f"OpenAI 기본 채팅 실패: {str(e)}"
        }

# 중복 API 제거 - analyze-uploaded-file과 동일한 기능
# @app.post("/risk-analysis/analyze-rag-contract") - 제거됨

if __name__ == "__main__":
    import uvicorn
    
    # 서버 실행
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

