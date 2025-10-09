"""
위험 분석 API 엔드포인트
직렬 처리 및 점진적 분석을 위한 REST API
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
import asyncio
from datetime import datetime
import logging

# from .part_risk_analyzer import SequentialRiskAnalyzer, PartRiskAnalyzer
# from atlas_rag.retriever.vector_retriever import VectorRetriever
# from atlas_rag.llm_generator.llm_generator import LLMGenerator

# API 라우터 설정
router = APIRouter(prefix="/api/risk-analysis", tags=["risk-analysis"])

# 전역 변수 (실제 운영에서는 Redis 등 사용)
analysis_sessions = {}
risk_check_data = None

class AnalysisRequest(BaseModel):
    contract_id: str
    contract_text: str
    contract_name: Optional[str] = "계약서"
    selected_parts: Optional[List[int]] = None  # 특정 파트만 분석할 경우

class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None

class PartAnalysisResponse(BaseModel):
    part_number: int
    part_title: str
    risk_score: float
    risk_level: str
    checklist_results: List[Dict[str, Any]]
    relevant_clauses: List[str]
    recommendations: List[str]
    analysis_time: float

class FullAnalysisResponse(BaseModel):
    contract_name: str
    analysis_date: str
    total_analysis_time: float
    overall_risk_score: float
    overall_risk_level: str
    part_results: List[PartAnalysisResponse]
    summary: Dict[str, Any]

def load_risk_check_data():
    """위험 체크 데이터 로드"""
    global risk_check_data
    try:
        with open("riskAnalysis/checkList/riskCheck.json", "r", encoding="utf-8") as f:
            risk_check_data = json.load(f)
        logging.info("Risk check data loaded successfully")
    except Exception as e:
        logging.error(f"Failed to load risk check data: {e}")
        raise HTTPException(status_code=500, detail="위험 체크 데이터 로드 실패")

@router.on_event("startup")
async def startup_event():
    """서버 시작 시 위험 체크 데이터 로드"""
    load_risk_check_data()

@router.post("/start", response_model=AnalysisResponse)
async def start_risk_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """위험 분석 시작"""
    if not risk_check_data:
        raise HTTPException(status_code=500, detail="위험 체크 데이터가 로드되지 않음")
    
    # 분석 세션 ID 생성
    analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.contract_id}"
    
    # 분석할 파트 결정
    if request.selected_parts:
        parts_to_analyze = request.selected_parts
    else:
        parts_to_analyze = [part["partNumber"] for part in risk_check_data["analysisParts"]]
    
    # 예상 소요 시간 계산 (파트당 평균 30초)
    estimated_time = len(parts_to_analyze) * 30
    
    # 분석 세션 초기화
    analysis_sessions[analysis_id] = {
        "status": "STARTING",
        "contract_id": request.contract_id,
        "contract_text": request.contract_text,
        "contract_name": request.contract_name,
        "selected_parts": parts_to_analyze,
        "start_time": datetime.now(),
        "results": {},
        "current_part": 0,
        "total_parts": len(parts_to_analyze)
    }
    
    # 백그라운드에서 분석 시작
    background_tasks.add_task(
        run_sequential_analysis, 
        analysis_id, 
        request.contract_text, 
        request.contract_name,
        parts_to_analyze
    )
    
    return AnalysisResponse(
        analysis_id=analysis_id,
        status="STARTED",
        message="위험 분석이 시작되었습니다.",
        estimated_time=estimated_time
    )

@router.get("/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    """분석 상태 조회"""
    if analysis_id not in analysis_sessions:
        raise HTTPException(status_code=404, detail="분석 세션을 찾을 수 없습니다.")
    
    session = analysis_sessions[analysis_id]
    
    return {
        "analysis_id": analysis_id,
        "status": session["status"],
        "progress": {
            "current_part": session["current_part"],
            "total_parts": session["total_parts"],
            "percentage": (session["current_part"] / session["total_parts"]) * 100
        },
        "elapsed_time": (datetime.now() - session["start_time"]).total_seconds(),
        "current_part_title": session.get("current_part_title", "")
    }

@router.get("/{analysis_id}/part/{part_number}", response_model=PartAnalysisResponse)
async def get_part_analysis(analysis_id: str, part_number: int):
    """특정 파트 분석 결과 조회"""
    if analysis_id not in analysis_sessions:
        raise HTTPException(status_code=404, detail="분석 세션을 찾을 수 없습니다.")
    
    session = analysis_sessions[analysis_id]
    
    if part_number not in session["results"]:
        raise HTTPException(status_code=404, detail=f"Part {part_number} 분석 결과를 찾을 수 없습니다.")
    
    result = session["results"][part_number]
    
    return PartAnalysisResponse(
        part_number=result["part_number"],
        part_title=result["part_title"],
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        checklist_results=result["checklist_results"],
        relevant_clauses=result.get("relevant_clauses", []),
        recommendations=result["recommendations"],
        analysis_time=result["analysis_time"]
    )

@router.get("/{analysis_id}/report", response_model=FullAnalysisResponse)
async def get_full_analysis_report(analysis_id: str):
    """전체 분석 리포트 조회"""
    if analysis_id not in analysis_sessions:
        raise HTTPException(status_code=404, detail="분석 세션을 찾을 수 없습니다.")
    
    session = analysis_sessions[analysis_id]
    
    if session["status"] != "COMPLETED":
        raise HTTPException(status_code=400, detail="분석이 아직 완료되지 않았습니다.")
    
    # 전체 결과 구성
    part_results = []
    total_risk_score = 0.0
    
    for part_number, result in session["results"].items():
        part_results.append(PartAnalysisResponse(
            part_number=result["part_number"],
            part_title=result["part_title"],
            risk_score=result["risk_score"],
            risk_level=result["risk_level"],
            checklist_results=result["checklist_results"],
            relevant_clauses=result.get("relevant_clauses", []),
            recommendations=result["recommendations"],
            analysis_time=result["analysis_time"]
        ))
        total_risk_score += result["risk_score"]
    
    overall_risk_score = total_risk_score / len(part_results) if part_results else 0.0
    overall_risk_level = determine_risk_level(overall_risk_score)
    
    # 요약 정보 생성
    summary = {
        "total_parts_analyzed": len(part_results),
        "overall_risk_score": overall_risk_score,
        "overall_risk_level": overall_risk_level,
        "high_risk_parts": [r.part_title for r in part_results if r.risk_level in ["HIGH", "CRITICAL"]],
        "total_analysis_time": session.get("total_analysis_time", 0)
    }
    
    return FullAnalysisResponse(
        contract_name=session["contract_name"],
        analysis_date=session["start_time"].isoformat(),
        total_analysis_time=session.get("total_analysis_time", 0),
        overall_risk_score=overall_risk_score,
        overall_risk_level=overall_risk_level,
        part_results=part_results,
        summary=summary
    )

@router.delete("/{analysis_id}")
async def delete_analysis_session(analysis_id: str):
    """분석 세션 삭제"""
    if analysis_id not in analysis_sessions:
        raise HTTPException(status_code=404, detail="분석 세션을 찾을 수 없습니다.")
    
    del analysis_sessions[analysis_id]
    return {"message": "분석 세션이 삭제되었습니다."}

async def run_sequential_analysis(analysis_id: str, contract_text: str, contract_name: str, parts_to_analyze: List[int]):
    """직렬 위험 분석 실행"""
    try:
        # RAG 시스템 초기화 (기존 서버의 RAG 시스템 사용)
        # 실제 구현에서는 전역 RAG 시스템 사용
        from server import rag_system, neo4j_driver
        
        if not rag_system:
            raise Exception("RAG 시스템이 로드되지 않았습니다.")
        
        # 하이브리드 순차 분석기 초기화
        from .hybrid_risk_analyzer import HybridSequentialRiskAnalyzer
        
        analyzer = HybridSequentialRiskAnalyzer(
            risk_check_data, 
            rag_system["enhanced_lkg_retriever"], 
            rag_system["hippo_retriever"],
            rag_system["llm_generator"],
            neo4j_driver
        )
        
        # 분석 세션 상태 업데이트
        analysis_sessions[analysis_id]["status"] = "RUNNING"
        
        # 파트별 순차 분석
        for i, part_number in enumerate(parts_to_analyze):
            try:
                # 현재 파트 정보 업데이트
                analysis_sessions[analysis_id]["current_part"] = i + 1
                part_data = next(p for p in risk_check_data["analysisParts"] if p["partNumber"] == part_number)
                analysis_sessions[analysis_id]["current_part_title"] = part_data["partTitle"]
                
                logging.info(f"Part {part_number} 분석 시작: {part_data['partTitle']}")
                
                # 파트별 하이브리드 분석 수행
                from .hybrid_risk_analyzer import HybridRiskAnalyzer
                
                part_analyzer = HybridRiskAnalyzer(
                    risk_check_data, 
                    rag_system["enhanced_lkg_retriever"], 
                    rag_system["hippo_retriever"],
                    rag_system["llm_generator"],
                    neo4j_driver
                )
                result = await part_analyzer.analyze_part_with_hybrid_retrieval(part_number, contract_text)
                
                # 하이브리드 분석 결과 저장
                analysis_sessions[analysis_id]["results"][part_number] = {
                    "part_number": result.part_number,
                    "part_title": result.part_title,
                    "risk_score": result.risk_score,
                    "risk_level": result.risk_level,
                    "checklist_results": result.checklist_results,
                    "relevant_clauses": result.relevant_clauses,
                    "hybrid_search_results": result.hybrid_search_results,
                    "recommendations": result.recommendations,
                    "analysis_time": result.analysis_time
                }
                
                logging.info(f"Part {part_number} 분석 완료 - 위험도: {result.risk_level}")
                
            except Exception as e:
                logging.error(f"Part {part_number} 분석 실패: {e}")
                # 실패한 파트에 대한 기본 결과
                analysis_sessions[analysis_id]["results"][part_number] = {
                    "part_number": part_number,
                    "part_title": f"Part {part_number}",
                    "risk_score": 0.0,
                    "risk_level": "ERROR",
                    "checklist_results": [],
                    "relevant_clauses": [],
                    "hybrid_search_results": {"error": str(e)},
                    "recommendations": [f"하이브리드 분석 실패: {str(e)}"],
                    "analysis_time": 0.0
                }
        
        # 분석 완료
        analysis_sessions[analysis_id]["status"] = "COMPLETED"
        analysis_sessions[analysis_id]["total_analysis_time"] = (datetime.now() - analysis_sessions[analysis_id]["start_time"]).total_seconds()
        
        logging.info(f"Analysis {analysis_id} completed successfully")
        
    except Exception as e:
        logging.error(f"Analysis {analysis_id} failed: {e}")
        analysis_sessions[analysis_id]["status"] = "FAILED"
        analysis_sessions[analysis_id]["error"] = str(e)

def determine_risk_level(risk_score: float) -> str:
    """위험도 레벨 결정"""
    if risk_score >= 4.0:
        return "CRITICAL"
    elif risk_score >= 3.0:
        return "HIGH"
    elif risk_score >= 2.0:
        return "MEDIUM"
    else:
        return "LOW"
