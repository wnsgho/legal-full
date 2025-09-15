#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSchemaKG 백엔드 서버
FastAPI를 사용한 REST API 서버
"""

import os
import sys
import json
import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# 로깅 설정에 인코딩 추가 (Windows cp949 오류 해결)
import sys
import io
import warnings

# stdout을 utf-8로 설정
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 불필요한 로그 억제
warnings.filterwarnings("ignore")
logging.getLogger("faiss.loader").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("nltk").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

# 전역 변수
rag_system = None
neo4j_driver = None
pipeline_status = {}  # 파이프라인 실행 상태 관리
uploaded_files = {}   # 업로드된 파일 관리

# 업로드 디렉토리 설정 (프로젝트 루트 기준)
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

def restore_uploaded_files():
    """서버 시작 시 업로드 디렉토리의 파일들을 스캔하여 uploaded_files 복구 (가장 최근 파일만)"""
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
            
            # 나머지 파일들은 삭제 (선택사항)
            for other_file, _ in files_with_time[1:]:
                try:
                    other_file.unlink()
                    logger.info(f"🗑️ 이전 파일 삭제: {other_file.name}")
                except Exception as e:
                    logger.warning(f"⚠️ 파일 삭제 실패 {other_file.name}: {e}")

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
    """기존 임베딩 데이터가 있는 키워드 찾기"""
    # 환경변수에서 import 디렉토리 경로 가져오기 (절대 경로 또는 상대 경로)
    import_dir = Path(os.getenv('IMPORT_DIRECTORY', 'BE/import'))
    logger.info(f"🔍 임베딩 데이터 탐색 중... import_dir: {import_dir.absolute()}")
    
    if not import_dir.exists():
        logger.warning(f"❌ import 디렉토리가 존재하지 않습니다: {import_dir.absolute()}")
        return None
    
    # import 폴더에서 키워드 찾기
    for keyword_dir in import_dir.iterdir():
        if keyword_dir.is_dir():
            logger.info(f"📁 키워드 디렉토리 발견: {keyword_dir.name}")
            precompute_dir = keyword_dir / os.getenv('PRECOMPUTE_DIRECTORY', 'precompute')
            logger.info(f"🔍 precompute 디렉토리 확인: {precompute_dir.absolute()}")
            
            if precompute_dir.exists():
                # FAISS 인덱스 파일이 있는지 확인
                faiss_files = list(precompute_dir.glob("*_faiss.index"))
                logger.info(f"📊 FAISS 파일 개수: {len(faiss_files)}")
                if faiss_files:
                    logger.info(f"✅ 기존 임베딩 데이터 발견: {keyword_dir.name}")
                    return keyword_dir.name
                else:
                    logger.info(f"⚠️ precompute 디렉토리는 있지만 FAISS 파일이 없습니다: {keyword_dir.name}")
            else:
                logger.info(f"⚠️ precompute 디렉토리가 없습니다: {keyword_dir.name}")
    
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
            neo4j_database = os.getenv('NEO4J_DATABASE', 'neo4j')
            
            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            
            # Neo4j에서 노드 수 확인
            with driver.session(database=neo4j_database) as session:
                result = session.run("MATCH (n) RETURN count(n) as node_count")
                node_count = result.single()["node_count"]
                
                if node_count > 0:
                    logger.info(f"✅ 기존 Neo4j 데이터 발견: {node_count}개 노드")
                    
                    # GDS 그래프 확인 및 생성
                    try:
                        from .experiment.create_gds_graph import create_gds_graph
                        logger.info("🔄 GDS 그래프 확인 및 생성 중...")
                        create_gds_graph()
                        logger.info("✅ GDS 그래프 생성 완료")
                    except Exception as e:
                        logger.warning(f"⚠️ GDS 그래프 생성 실패: {e}")
                    
                    # 기존 임베딩 데이터가 있는 키워드 찾기
                    existing_keyword = find_existing_keyword()
                    if existing_keyword:
                        # 환경변수에 키워드 설정
                        os.environ['KEYWORD'] = existing_keyword
                        logger.info(f"🔑 키워드 설정: {existing_keyword}")
                        
                        # RAG 시스템 로드 시도
                        try:
                            from .experiment.run_questions_v3_with_concept import load_enhanced_rag_system
                            enhanced_lkg_retriever, hippo_retriever, llm_generator, _ = load_enhanced_rag_system()
                            
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
    version="1.0.0",
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
    max_tokens: int = 8192  # 더 긴 응답을 위해 증가
    temperature: float = 0.5

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

class RiskAnalysisRequest(BaseModel):
    contract_text: str
    analysis_type: str = "comprehensive"  # comprehensive, basic, specific

class RiskAnalysisResponse(BaseModel):
    success: bool
    risks: List[Dict[str, Any]]
    risk_score: float
    recommendations: List[str]
    processing_time: float

def load_rag_system():
    """RAG 시스템 로드"""
    global rag_system, neo4j_driver
    
    try:
        from .experiment.run_questions_v3_with_concept import load_enhanced_rag_system
        
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
        version="1.0.0"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
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
        from .experiment.run_questions_v3_with_concept import concept_enhanced_hybrid_retrieve
        
        sorted_context = concept_enhanced_hybrid_retrieve(
            request.question, 
            rag_system["enhanced_lkg_retriever"], 
            rag_system["hippo_retriever"],
            rag_system["llm_generator"],
            neo4j_driver
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
    """파이프라인 실행 함수 (백그라운드)"""
    global pipeline_status
    
    if pipeline_id:
        pipeline_status[pipeline_id] = {
            "status": "running",
            "progress": 0,
            "message": "파이프라인 실행 중...",
            "start_time": datetime.now().isoformat()
        }
    
    try:
        from .main_pipeline import test_atlas_pipeline
        
        if pipeline_id:
            pipeline_status[pipeline_id]["progress"] = 25
            pipeline_status[pipeline_id]["message"] = "지식그래프 추출 중..."
        
        # keyword를 직접 매개변수로 전달 (환경변수 충돌 방지)
        success = test_atlas_pipeline(start_step, keyword)
        
        if success:
            logger.info("✅ 파이프라인 실행 완료")
            
            # 파이프라인 완료 후 RAG 시스템 자동 로드
            logger.info("🔄 RAG 시스템 자동 로드 중...")
            if check_and_load_existing_data():
                logger.info("✅ 파이프라인 완료 후 RAG 시스템 로드 성공")
            else:
                logger.warning("⚠️ 파이프라인 완료 후 RAG 시스템 로드 실패")
            
            if pipeline_id:
                pipeline_status[pipeline_id] = {
                    "status": "completed",
                    "progress": 100,
                    "message": "파이프라인 실행 완료",
                    "end_time": datetime.now().isoformat()
                }
        else:
            logger.error("❌ 파이프라인 실행 실패")
            if pipeline_id:
                pipeline_status[pipeline_id] = {
                    "status": "failed",
                    "progress": 0,
                    "message": "파이프라인 실행 실패",
                    "end_time": datetime.now().isoformat()
                }
            
    except Exception as e:
        logger.error(f"파이프라인 실행 중 오류: {e}")
        if pipeline_id:
            pipeline_status[pipeline_id] = {
                "status": "failed",
                "progress": 0,
                "message": f"파이프라인 실행 오류: {str(e)}",
                "end_time": datetime.now().isoformat()
            }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """챗봇 질문 처리"""
    start_time = datetime.now()
    
    try:
        # RAG 시스템이 로드되지 않은 경우 로드 시도
        if rag_system is None:
            if not load_rag_system():
                raise HTTPException(status_code=500, detail="RAG 시스템을 로드할 수 없습니다.")
        
        # 질문 처리 - 직접 LLM 호출로 max_tokens 제어
        from .experiment.run_questions_v3_with_concept import concept_enhanced_hybrid_retrieve
        
        # Concept 활용 하이브리드 검색 실행
        sorted_context = concept_enhanced_hybrid_retrieve(
            request.question, 
            rag_system["enhanced_lkg_retriever"], 
            rag_system["hippo_retriever"],
            rag_system["llm_generator"],
            neo4j_driver
        )
        
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
            context_count=0,  # 실제 구현에서는 컨텍스트 개수 반환
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"챗봇 처리 실패: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ChatResponse(
            success=False,
            answer=f"오류가 발생했습니다: {str(e)}",
            context_count=0,
            processing_time=processing_time
        )

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

@app.get("/status")
async def get_status():
    """시스템 상태 조회"""
    try:
        status = {
            "rag_system_loaded": rag_system is not None,
            "neo4j_connected": neo4j_driver is not None,
            "timestamp": datetime.now().isoformat()
        }
        
        return {"success": True, "status": status}
        
    except Exception as e:
        logger.error(f"상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 새로운 웹 플로우 API 엔드포인트들

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
        if pipeline_id not in pipeline_status:
            raise HTTPException(status_code=404, detail="파이프라인을 찾을 수 없습니다.")
        
        status_info = pipeline_status[pipeline_id]
        
        return PipelineStatusResponse(
            success=True,
            status=status_info["status"],
            progress=status_info["progress"],
            message=status_info["message"],
            data=status_info
        )
        
    except Exception as e:
        logger.error(f"파이프라인 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analysis/risk", response_model=RiskAnalysisResponse)
async def analyze_contract_risk(request: RiskAnalysisRequest):
    """계약서 위험 분석"""
    start_time = datetime.now()
    
    try:
        # RAG 시스템이 로드되지 않은 경우 로드 시도
        if rag_system is None:
            if not load_rag_system():
                raise HTTPException(status_code=500, detail="RAG 시스템을 로드할 수 없습니다.")
        
        # 위험 분석 수행
        risks, risk_score, recommendations = await perform_risk_analysis(
            request.contract_text, 
            request.analysis_type,
            rag_system["llm_generator"]
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return RiskAnalysisResponse(
            success=True,
            risks=risks,
            risk_score=risk_score,
            recommendations=recommendations,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"❌ 위험 분석 실패: {e}")
        return RiskAnalysisResponse(
            success=False,
            risks=[],
            risk_score=0,
            recommendations=[],
            processing_time=(datetime.now() - start_time).total_seconds()
        )

@app.post("/analysis/auto-risk", response_model=ChatResponse)
async def auto_analyze_contract_risks(request: ChatRequest):
    """파이프라인 처리된 계약서 데이터 자동 위험조항 분석"""
    start_time = datetime.now()
    
    try:
        # RAG 시스템이 로드되지 않은 경우 로드 시도
        if rag_system is None:
            if not load_rag_system():
                raise HTTPException(status_code=500, detail="RAG 시스템을 로드할 수 없습니다.")
        
        # Concept 활용 하이브리드 검색으로 계약서 데이터 추출
        from .experiment.run_questions_v3_with_concept import concept_enhanced_hybrid_retrieve
        
        # 위험조항 분석을 위한 검색 쿼리
        search_query = "계약서 조항 당사자 거래대금 선행조건 진술보장 손해배상 해제조건"
        sorted_context, context_ids = concept_enhanced_hybrid_retrieve(
            search_query, 
            rag_system["enhanced_lkg_retriever"], 
            rag_system["hippo_retriever"],
            rag_system["llm_generator"],
            neo4j_driver
        )
        
        if sorted_context:
            # 위험조항 체크리스트 로드
            risk_checklist = load_risk_checklist()
            
            # sorted_context를 문자열로 변환
            context_text = '\n'.join(sorted_context) if isinstance(sorted_context, list) else str(sorted_context)
            
            # 자동 위험조항 분석 시스템 프롬프트
            system_instruction = (
                "당신은 대한민국의 계약서 위험조항 분석 전문가입니다. "
                "파이프라인으로 처리된 계약서 데이터를 기반으로 위험조항을 자동 분석하세요.\n\n"
                "분석 시 다음 구조로 답변하세요:\n"
                "## 🔍 발견된 위험요소\n"
                "### 1. 당사자 관련 위험\n"
                "### 2. 거래대금 관련 위험\n"
                "### 3. 선행조건 관련 위험\n"
                "### 4. 진술 및 보장 관련 위험\n"
                "### 5. 손해배상 관련 위험\n"
                "### 6. 계약 해제 관련 위험\n"
                "### 7. 기타 조항 관련 위험\n\n"
                "각 위험요소마다:\n"
                "- **위험 내용**: 구체적인 위험조항\n"
                "- **위험도**: 매우 높음/높음/중간/낮음\n"
                "- **영향 당사자**: 매수인/매도인/양 당사자\n"
                "- **개선 권고**: 구체적인 수정 제안\n\n"
                "## 📊 종합 평가\n"
                "- 전체 위험 수준\n"
                "- 주요 우려사항\n"
                "- 우선순위 개선 항목\n\n"
                f"=== 계약서 위험조항 체크리스트 ===\n{risk_checklist}\n"
                "위 체크리스트의 각 항목을 계약서 데이터와 대조하여 분석하세요."
            )
            
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"계약서 데이터:\n{context_text}\n\n분석 요청: {request.question}"},
            ]
            
            result = rag_system["llm_generator"].generate_response(
                messages, 
                max_new_tokens=request.max_tokens, 
                temperature=request.temperature
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 자동 위험조항 분석 완료 (소요시간: {processing_time:.2f}초)")
            
            return ChatResponse(
                success=True,
                answer=result,
                context_count=len(sorted_context) if isinstance(sorted_context, list) else 0,
                processing_time=processing_time
            )
        else:
            logger.warning("⚠️ 계약서 데이터를 찾을 수 없습니다.")
            return ChatResponse(
                success=False,
                answer="계약서 데이터를 찾을 수 없습니다. 파이프라인을 먼저 실행해주세요.",
                context_count=0,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
    except Exception as e:
        logger.error(f"❌ 자동 위험조항 분석 실패: {e}")
        return ChatResponse(
            success=False,
            answer=f"자동 위험조항 분석 중 오류가 발생했습니다: {str(e)}",
            context_count=0,
            processing_time=(datetime.now() - start_time).total_seconds()
        )
        logger.error(f"위험 분석 실패: {e}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return RiskAnalysisResponse(
            success=False,
            risks=[],
            risk_score=0.0,
            recommendations=[],
            processing_time=processing_time
        )

async def perform_risk_analysis(contract_text: str, analysis_type: str, llm_generator):
    """위험 분석 수행"""
    try:
        # 위험 분석 프롬프트
        risk_analysis_prompt = f"""
다음 계약서를 분석하여 위험 요소를 찾아주세요.

계약서 내용:
{contract_text}

분석 유형: {analysis_type}

다음 형식으로 분석해주세요:
1. 위험 요소 목록 (위험도: 높음/중간/낮음)
2. 각 위험 요소의 설명
3. 위험 점수 (0-100)
4. 개선 권장사항

JSON 형식으로 응답해주세요:
{{
    "risks": [
        {{
            "type": "위험 유형",
            "description": "위험 설명",
            "severity": "높음/중간/낮음",
            "clause": "관련 조항"
        }}
    ],
    "risk_score": 75,
    "recommendations": [
        "권장사항 1",
        "권장사항 2"
    ]
}}
"""
        
        messages = [
            {"role": "system", "content": "당신은 계약서 위험 분석 전문가입니다. 계약서의 위험 요소를 정확히 분석하고 개선 방안을 제시해주세요."},
            {"role": "user", "content": risk_analysis_prompt}
        ]
        
        response = llm_generator.generate_response(
            messages, 
            max_new_tokens=8192,  # 더 긴 응답을 위해 증가
            temperature=0.3
        )
        
        # JSON 응답 파싱
        try:
            import json
            analysis_result = json.loads(response)
            
            risks = analysis_result.get("risks", [])
            risk_score = analysis_result.get("risk_score", 0.0)
            recommendations = analysis_result.get("recommendations", [])
            
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 기본값 반환
            risks = [{"type": "분석 오류", "description": "위험 분석 결과를 파싱할 수 없습니다.", "severity": "중간", "clause": "전체"}]
            risk_score = 50.0
            recommendations = ["계약서를 다시 검토해주세요."]
        
        return risks, risk_score, recommendations
        
    except Exception as e:
        logger.error(f"위험 분석 수행 실패: {e}")
        return [], 0.0, []

@app.get("/files")
async def list_uploaded_files():
    """업로드된 파일 목록 조회"""
    try:
        files = []
        for file_id, file_info in uploaded_files.items():
            files.append({
                "file_id": file_id,
                "filename": file_info["filename"],
                "upload_time": file_info["upload_time"],
                "file_size": file_info["file_size"]
            })
        
        return {"success": True, "files": files}
        
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

if __name__ == "__main__":
    import uvicorn
    
    # 서버 실행
    uvicorn.run(
        "BE.backend_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
