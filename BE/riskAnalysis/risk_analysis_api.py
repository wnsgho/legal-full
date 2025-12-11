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

# API 라우터 설정 (prefix는 api.py에서 설정됨)
router = APIRouter(tags=["risk-analysis"])

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


# ============================================
# 프론트엔드 호환 엔드포인트
# ============================================

from .data_persistence import data_manager

@router.get("/rag-contracts")
async def get_rag_contracts():
    """RAG 구축된 계약서 목록 조회"""
    try:
        from app.services.file_service import file_service
        files = file_service.list_files()
        
        return {
            "success": True,
            "data": [
                {
                    "file_id": f.file_id,
                    "filename": f.filename,
                    "uploaded_at": f.upload_time,
                    "file_size": f.file_size,
                    "file_type": "markdown" if f.filename.endswith(".md") else "text"
                }
                for f in files
            ],
            "total_count": len(files)
        }
    except Exception as e:
        logging.error(f"RAG contracts 조회 실패: {e}")
        return {"success": True, "data": [], "total_count": 0}


@router.get("/saved")
async def get_saved_risk_analysis():
    """저장된 위험 분석 결과 목록 조회"""
    try:
        results = data_manager.get_analysis_list()
        return {
            "success": True,
            "data": {
                "results": results
            }
        }
    except Exception as e:
        logging.error(f"저장된 분석 결과 조회 실패: {e}")
        return {"success": True, "data": {"results": []}}


@router.get("/saved/{file_id}")
async def get_saved_risk_analysis_by_file(file_id: str):
    """특정 파일의 저장된 위험 분석 결과 조회"""
    try:
        result = data_manager.load_analysis_result(file_id)
        if result:
            return {"success": True, "data": result}
        return {"success": False, "data": None, "message": "분석 결과를 찾을 수 없습니다."}
    except Exception as e:
        logging.error(f"파일 분석 결과 조회 실패: {e}")
        return {"success": False, "data": None, "message": str(e)}


@router.get("/gpt-results")
async def get_gpt_analysis_results():
    """GPT 분석 결과 목록 조회"""
    try:
        # GPT 분석 결과는 data_manager에서 가져옴 (gpt_ 접두사로 필터링)
        all_results = data_manager.load_all_results()
        gpt_results = [r for k, r in all_results.items() if k.startswith("gpt_")]
        
        return {
            "success": True,
            "data": {
                "results": gpt_results
            }
        }
    except Exception as e:
        logging.error(f"GPT 분석 결과 조회 실패: {e}")
        return {"success": True, "data": {"results": []}}


class GPTOnlyAnalysisRequest(BaseModel):
    file_id: str


@router.post("/analyze-gpt-only")
async def analyze_gpt_only(request: GPTOnlyAnalysisRequest):
    """GPT 전용 위험 분석 실행 (RAG 시스템 없이 OpenAI GPT만 사용)"""
    try:
        from app.services.file_service import file_service
        from .simple_gpt_risk_analyzer import SimpleGPTRiskAnalyzer
        
        # 파일 존재 확인
        file_info = file_service.get_file_info(request.file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        # 파일 내용 읽기
        contract_text = file_service.get_file_content(request.file_id)
        contract_name = file_info.get("filename", "계약서")
        
        logging.info(f"GPT 전용 분석 시작: {contract_name} (file_id: {request.file_id})")
        
        # GPT 분석기 초기화 및 분석 실행
        analyzer = SimpleGPTRiskAnalyzer()
        analysis_result = analyzer.analyze_contract(contract_text, contract_name)
        
        # 분석 ID 생성 (gpt_ 접두사 사용)
        analysis_id = f"gpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.file_id}"
        
        # 결과를 표준 형식으로 변환
        result = {
            "analysis_id": analysis_id,
            "file_id": request.file_id,
            "contract_name": contract_name,
            "created_at": datetime.now().isoformat(),
            "analysis_type": "gpt_only",
            "analysis_result": {
                "overall_risk_score": 0.0,  # GPT 분석은 점수를 제공하지 않으므로 0으로 설정
                "part_results": [],  # GPT 분석은 파트별 결과를 제공하지 않음
                "gpt_analysis": analysis_result.get("analysis_result", ""),
                "model_used": analysis_result.get("model_used", ""),
                "analysis_time": analysis_result.get("analysis_time", 0)
            }
        }
        
        # 결과 저장
        data_manager.save_analysis_result(analysis_id, result)
        
        logging.info(f"GPT 전용 분석 완료: {analysis_id}")
        
        return {
            "success": True,
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"GPT 전용 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"GPT 분석 중 오류가 발생했습니다: {str(e)}")


class UploadedFileAnalysisRequest(BaseModel):
    file_id: str
    selected_parts: Optional[str] = "all"


@router.post("/analyze-uploaded-file")
async def analyze_uploaded_file_risk(request: UploadedFileAnalysisRequest, background_tasks: BackgroundTasks):
    """업로드된 파일의 위험 분석 실행 (기존 로직 사용)"""
    try:
        from app.services.file_service import file_service
        
        # 파일 존재 확인
        file_info = file_service.get_file_info(request.file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        # 파일 내용 읽기
        contract_text = file_service.get_file_content(request.file_id)
        contract_name = file_info.get("filename", "계약서")
        
        # 분석 ID 생성
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.file_id}"
        
        # 분석할 파트 결정
        if request.selected_parts == "all":
            parts_to_analyze = [part["partNumber"] for part in risk_check_data["analysisParts"]] if risk_check_data else []
        else:
            parts_to_analyze = [int(p) for p in request.selected_parts.split(",")]
        
        # 분석 세션 초기화
        analysis_sessions[analysis_id] = {
            "status": "STARTING",
            "contract_id": request.file_id,
            "contract_text": contract_text,
            "contract_name": contract_name,
            "selected_parts": parts_to_analyze,
            "start_time": datetime.now(),
            "results": {},
            "current_part": 0,
            "total_parts": len(parts_to_analyze)
        }
        
        # 백그라운드에서 분석 실행
        background_tasks.add_task(
            run_uploaded_file_analysis,
            analysis_id,
            request.file_id,
            contract_text,
            contract_name,
            parts_to_analyze
        )
        
        return {
            "success": True,
            "message": "위험 분석이 시작되었습니다.",
            "data": {
                "analysis_id": analysis_id,
                "analysis_result": {
                    "analysis_id": analysis_id,
                    "contract_name": contract_name,
                    "status": "RUNNING"
                }
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"위험 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_uploaded_file_analysis(analysis_id: str, file_id: str, contract_text: str, contract_name: str, parts_to_analyze: List[int]):
    """업로드된 파일의 위험 분석 실행 (백그라운드)"""
    try:
        from .hybrid_risk_analyzer import HybridRiskAnalyzer
        
        analysis_sessions[analysis_id]["status"] = "RUNNING"
        start_time = datetime.now()
        
        # RAG 시스템 확인
        rag_system = None
        neo4j_driver = None
        
        try:
            from experiment.run_questions_v3_with_concept import load_enhanced_rag_system
            
            # 함수를 호출해서 RAG 시스템 로드
            enhanced_lkg_retriever, hippo_retriever, llm_generator, driver = load_enhanced_rag_system()
            
            if enhanced_lkg_retriever and llm_generator:
                rag_system = {
                    "enhanced_lkg_retriever": enhanced_lkg_retriever,
                    "hippo_retriever": hippo_retriever,
                    "llm_generator": llm_generator
                }
                neo4j_driver = driver
                logging.info("✅ RAG 시스템 로드 성공")
            else:
                logging.warning("⚠️ RAG 시스템 컴포넌트가 None입니다")
        except Exception as e:
            logging.warning(f"RAG 시스템 로드 실패, 기본 분석으로 진행: {e}")
        
        part_results = []
        total_risk_score = 0.0
        
        for i, part_number in enumerate(parts_to_analyze):
            try:
                analysis_sessions[analysis_id]["current_part"] = i + 1
                
                if risk_check_data:
                    part_data = next((p for p in risk_check_data["analysisParts"] if p["partNumber"] == part_number), None)
                    if part_data:
                        analysis_sessions[analysis_id]["current_part_title"] = part_data["partTitle"]
                
                # RAG 시스템이 있으면 하이브리드 분석 수행
                if rag_system and neo4j_driver and risk_check_data:
                    analyzer = HybridRiskAnalyzer(
                        risk_check_data,
                        rag_system["enhanced_lkg_retriever"],
                        rag_system.get("hippo_retriever"),
                        rag_system["llm_generator"],
                        neo4j_driver
                    )
                    result = await analyzer.analyze_part_with_hybrid_retrieval(part_number, contract_text)
                    
                    part_result = {
                        "part_number": result.part_number,
                        "part_title": result.part_title,
                        "risk_score": result.risk_score,
                        "risk_level": result.risk_level,
                        "checklist_results": result.checklist_results,
                        "relevant_clauses": result.relevant_clauses,
                        "risk_clauses": result.risk_clauses,
                        "recommendations": result.recommendations,
                        "analysis_time": result.analysis_time
                    }
                else:
                    # RAG 시스템 없이 기본 분석
                    part_result = await _basic_risk_analysis(part_number, contract_text, risk_check_data)
                
                part_results.append(part_result)
                total_risk_score += part_result["risk_score"]
                analysis_sessions[analysis_id]["results"][part_number] = part_result
                
            except Exception as e:
                logging.error(f"Part {part_number} 분석 실패: {e}")
                part_results.append({
                    "part_number": part_number,
                    "part_title": f"Part {part_number}",
                    "risk_score": 0.0,
                    "risk_level": "ERROR",
                    "checklist_results": [],
                    "relevant_clauses": [],
                    "risk_clauses": [],
                    "recommendations": [f"분석 실패: {str(e)}"],
                    "analysis_time": 0.0
                })
        
        # 전체 결과 계산
        overall_risk_score = total_risk_score / len(part_results) if part_results else 0.0
        overall_risk_level = determine_risk_level(overall_risk_score)
        total_analysis_time = (datetime.now() - start_time).total_seconds()
        
        # 최종 결과 구성
        final_result = {
            "analysis_id": analysis_id,
            "contract_name": contract_name,
            "created_at": start_time.isoformat(),
            "analysis_type": "hybrid" if rag_system else "basic",
            "analysis_result": {
                "overall_risk_score": overall_risk_score,
                "overall_risk_level": overall_risk_level,
                "part_results": part_results,
                "total_analysis_time": total_analysis_time,
                "summary": {
                    "total_parts_analyzed": len(part_results),
                    "high_risk_parts": len([p for p in part_results if p["risk_level"] in ["HIGH", "CRITICAL"]]),
                    "critical_issues": [p["part_title"] for p in part_results if p["risk_level"] == "CRITICAL"]
                }
            }
        }
        
        # 결과 저장
        data_manager.save_analysis_result(file_id, final_result)
        
        analysis_sessions[analysis_id]["status"] = "COMPLETED"
        analysis_sessions[analysis_id]["total_analysis_time"] = total_analysis_time
        analysis_sessions[analysis_id]["final_result"] = final_result
        
        logging.info(f"Analysis {analysis_id} completed: {overall_risk_level} ({overall_risk_score:.2f})")
        
    except Exception as e:
        logging.error(f"Analysis {analysis_id} failed: {e}")
        analysis_sessions[analysis_id]["status"] = "FAILED"
        analysis_sessions[analysis_id]["error"] = str(e)


async def _basic_risk_analysis(part_number: int, contract_text: str, risk_check_data: Dict) -> Dict:
    """RAG 없이 기본 위험 분석 수행"""
    import re
    
    part_data = None
    if risk_check_data:
        part_data = next((p for p in risk_check_data["analysisParts"] if p["partNumber"] == part_number), None)
    
    if not part_data:
        return {
            "part_number": part_number,
            "part_title": f"Part {part_number}",
            "risk_score": 0.0,
            "risk_level": "UNKNOWN",
            "checklist_results": [],
            "relevant_clauses": [],
            "risk_clauses": [],
            "recommendations": ["위험 체크 데이터가 없습니다."],
            "analysis_time": 0.0
        }
    
    checklist_results = []
    total_score = 0.0
    relevant_clauses = []
    risk_clauses = []
    
    # 체크리스트 항목별 기본 분석
    for item in part_data.get("checklistItems", []):
        item_text = item.get("item", "")
        keywords = item.get("keywords", [])
        
        # 키워드 기반 분석
        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in contract_text.lower():
                found_keywords.append(keyword)
        
        # 관련 조항 찾기
        clause_pattern = r'제\d+조[^\n]*'
        clauses = re.findall(clause_pattern, contract_text)
        item_clauses = [c for c in clauses if any(kw.lower() in c.lower() for kw in keywords)]
        relevant_clauses.extend(item_clauses[:3])
        
        # 위험도 판단 (키워드 발견 여부 기반)
        if found_keywords:
            risk_score = min(len(found_keywords) * 1.5, 5.0)
            if risk_score >= 3:
                risk_clauses.extend(item_clauses[:2])
        else:
            risk_score = 1.0
        
        total_score += risk_score
        
        checklist_results.append({
            "item": item_text,
            "keywords_found": found_keywords,
            "risk_score": risk_score,
            "risk_level": determine_risk_level(risk_score),
            "related_clauses": item_clauses[:3],
            "analysis": f"키워드 {len(found_keywords)}개 발견" if found_keywords else "관련 키워드 미발견"
        })
    
    avg_score = total_score / len(checklist_results) if checklist_results else 0.0
    
    return {
        "part_number": part_number,
        "part_title": part_data["partTitle"],
        "risk_score": avg_score,
        "risk_level": determine_risk_level(avg_score),
        "checklist_results": checklist_results,
        "relevant_clauses": list(set(relevant_clauses))[:10],
        "risk_clauses": list(set(risk_clauses))[:5],
        "recommendations": _generate_basic_recommendations(part_data, checklist_results),
        "analysis_time": 0.0
    }


def _generate_basic_recommendations(part_data: Dict, checklist_results: List[Dict]) -> List[str]:
    """기본 권고사항 생성"""
    recommendations = []
    
    high_risk_items = [r for r in checklist_results if r.get("risk_score", 0) >= 3]
    
    if high_risk_items:
        recommendations.append(f"⚠️ {len(high_risk_items)}개의 고위험 항목이 발견되었습니다.")
        for item in high_risk_items[:3]:
            recommendations.append(f"- {item.get('item', '')[:50]}... 검토 필요")
    else:
        recommendations.append("✅ 특별한 고위험 항목이 발견되지 않았습니다.")
    
    recommendations.append(f"📋 {part_data.get('partTitle', '')} 영역의 상세 검토를 권장합니다.")
    
    return recommendations
