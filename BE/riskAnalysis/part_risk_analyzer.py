"""
파트별 위험 분석 시스템
Rate limit을 고려한 직렬 처리 및 점진적 분석 구현
"""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

# 기존 RAG 시스템 import
from atlas_rag.retriever.vector_retriever import VectorRetriever
from atlas_rag.llm_generator.llm_generator import LLMGenerator

@dataclass
class PartAnalysisResult:
    """파트별 분석 결과"""
    part_number: int
    part_title: str
    risk_score: float  # 0-5점
    risk_level: str    # LOW, MEDIUM, HIGH, CRITICAL
    checklist_results: List[Dict[str, Any]]
    relevant_clauses: List[str]
    recommendations: List[str]
    analysis_time: float

class PartRiskAnalyzer:
    """파트별 위험 분석기"""
    
    def __init__(self, risk_check_data: Dict, retriever, llm_generator, neo4j_driver=None):
        self.risk_check_data = risk_check_data
        self.retriever = retriever  # enhanced_lkg_retriever
        self.llm_generator = llm_generator
        self.neo4j_driver = neo4j_driver
        self.rate_limit_delay = 2.0  # API 호출 간격 (초)
        
    async def analyze_part(self, part_number: int, contract_text: str) -> PartAnalysisResult:
        """특정 파트의 위험 분석 수행"""
        start_time = time.time()
        
        # 1. 파트 데이터 추출
        part_data = self._get_part_data(part_number)
        if not part_data:
            raise ValueError(f"Part {part_number} not found in risk check data")
        
        # 2. 관련 조항 검색
        relevant_clauses = await self._retrieve_relevant_clauses(part_data, contract_text)
        
        # 3. 체크리스트 항목별 분석
        checklist_results = await self._analyze_checklist_items(
            part_data, relevant_clauses, contract_text
        )
        
        # 4. 위험도 계산
        risk_score = self._calculate_risk_score(checklist_results)
        risk_level = self._determine_risk_level(risk_score)
        
        # 5. 권고사항 생성
        recommendations = await self._generate_recommendations(
            part_data, checklist_results, relevant_clauses
        )
        
        analysis_time = time.time() - start_time
        
        return PartAnalysisResult(
            part_number=part_number,
            part_title=part_data["partTitle"],
            risk_score=risk_score,
            risk_level=risk_level,
            checklist_results=checklist_results,
            relevant_clauses=relevant_clauses,
            recommendations=recommendations,
            analysis_time=analysis_time
        )
    
    def _get_part_data(self, part_number: int) -> Optional[Dict]:
        """특정 파트의 데이터 추출"""
        for part in self.risk_check_data["analysisParts"]:
            if part["partNumber"] == part_number:
                return part
        return None
    
    async def _retrieve_relevant_clauses(self, part_data: Dict, contract_text: str) -> List[str]:
        """파트와 관련된 조항 검색 - 하이브리드 리트리버 사용"""
        relevant_clauses = []
        
        # 파트별 핵심 질문을 기반으로 하이브리드 검색
        core_question = part_data.get("coreQuestion", "")
        top_risk_pattern = part_data.get("topRiskPattern", "")
        
        # 검색 쿼리 구성
        search_query = f"{core_question} {top_risk_pattern}"
        
        try:
            # 기존 하이브리드 리트리버 사용
            from experiment.run_questions_v3_with_concept import concept_enhanced_hybrid_retrieve
            
            # 하이브리드 검색 실행
            search_result = concept_enhanced_hybrid_retrieve(
                search_query,
                self.retriever,  # enhanced_lkg_retriever
                self.retriever,  # hippo_retriever (동일한 객체 사용)
                self.llm_generator,
                self.neo4j_driver,  # neo4j_driver
                topN=20  # 파트별로 적절한 수량
            )
            
            if search_result and len(search_result) == 2:
                sorted_context, context_ids = search_result
                if sorted_context:
                    # 결과를 리스트로 변환
                    if isinstance(sorted_context, str):
                        relevant_clauses = [sorted_context]
                    else:
                        relevant_clauses = sorted_context
            elif search_result:
                # 단일 결과인 경우
                relevant_clauses = [search_result] if isinstance(search_result, str) else search_result
                
        except Exception as e:
            logging.error(f"하이브리드 검색 실패: {e}")
            # 폴백: crossClauseAnalysis 기반 검색
            for clause_type in part_data.get("crossClauseAnalysis", []):
                clauses = await self._search_clauses_by_type(contract_text, clause_type)
                relevant_clauses.extend(clauses)
        
        return list(set(relevant_clauses))  # 중복 제거
    
    async def _search_clauses_by_type(self, contract_text: str, clause_type: str) -> List[str]:
        """특정 유형의 조항 검색"""
        try:
            # 벡터 검색을 통한 관련 조항 찾기
            results = await self.retriever.retrieve(
                query=clause_type,
                top_k=5,
                filter_metadata={"document_type": "contract_clause"}
            )
            return [result.content for result in results]
        except Exception as e:
            logging.error(f"Error searching clauses for type {clause_type}: {e}")
            return []
    
    async def _analyze_checklist_items(self, part_data: Dict, relevant_clauses: List[str], contract_text: str) -> List[Dict[str, Any]]:
        """체크리스트 항목별 분석"""
        checklist_results = []
        
        for i, checklist_item in enumerate(part_data.get("deepDiveChecklist", [])):
            # Rate limit 고려한 지연
            if i > 0:
                await asyncio.sleep(self.rate_limit_delay)
            
            # 각 체크리스트 항목 분석
            result = await self._analyze_single_checklist_item(
                checklist_item, relevant_clauses, contract_text, part_data
            )
            checklist_results.append(result)
        
        return checklist_results
    
    async def _analyze_single_checklist_item(self, checklist_item: str, relevant_clauses: List[str], contract_text: str, part_data: Dict) -> Dict[str, Any]:
        """단일 체크리스트 항목 분석"""
        
        # AI에게 파트별 체크리스트만 참고하도록 프롬프트 구성
        prompt = self._create_analysis_prompt(checklist_item, relevant_clauses, part_data)
        
        try:
            # LLM을 통한 분석
            analysis_result = await self.llm_generator.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.1  # 일관성을 위해 낮은 temperature
            )
            
            # 결과 파싱
            return self._parse_analysis_result(analysis_result, checklist_item)
            
        except Exception as e:
            logging.error(f"Error analyzing checklist item: {e}")
            return {
                "item": checklist_item,
                "risk_score": 0,
                "status": "ERROR",
                "analysis": f"분석 중 오류 발생: {str(e)}",
                "recommendation": "수동 검토 필요"
            }
    
    def _create_analysis_prompt(self, checklist_item: str, relevant_clauses: List[str], part_data: Dict) -> str:
        """분석용 프롬프트 생성"""
        
        # 파트별 컨텍스트 정보
        part_title = part_data["partTitle"]
        top_risk_pattern = part_data["topRiskPattern"]
        core_question = part_data["coreQuestion"]
        mitigation_strategy = part_data["mitigationStrategy"]
        
        prompt = f"""
당신은 계약서 위험 분석 전문가입니다. 다음 파트에 대해서만 분석해주세요:

**파트: {part_title}**
**핵심 위험 패턴: {top_risk_pattern}**
**핵심 질문: {core_question}**
**완화 전략: {mitigation_strategy}**

**분석할 체크리스트 항목: {checklist_item}**

**관련 조항들:**
{chr(10).join(f"- {clause}" for clause in relevant_clauses[:5])}

위의 체크리스트 항목을 관련 조항들과 비교하여 다음 형식으로 분석해주세요:

1. **위험도 점수**: 0-5점 (0=위험없음, 5=매우위험)
2. **상태**: SAFE, WARNING, DANGER, CRITICAL
3. **분석 내용**: 구체적인 위험 요소와 근거
4. **개선 권고**: 구체적인 개선 방안

JSON 형식으로 응답해주세요:
{{
    "risk_score": 점수,
    "status": "상태",
    "analysis": "분석내용",
    "recommendation": "개선권고"
}}
"""
        return prompt
    
    def _parse_analysis_result(self, analysis_result: str, checklist_item: str) -> Dict[str, Any]:
        """분석 결과 파싱"""
        try:
            # JSON 파싱 시도
            result = json.loads(analysis_result)
            result["item"] = checklist_item
            return result
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 기본값 반환
            return {
                "item": checklist_item,
                "risk_score": 3,  # 중간값
                "status": "WARNING",
                "analysis": analysis_result,
                "recommendation": "수동 검토 필요"
            }
    
    def _calculate_risk_score(self, checklist_results: List[Dict[str, Any]]) -> float:
        """전체 위험도 점수 계산"""
        if not checklist_results:
            return 0.0
        
        total_score = sum(result.get("risk_score", 0) for result in checklist_results)
        return total_score / len(checklist_results)
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """위험도 레벨 결정"""
        if risk_score >= 4.0:
            return "CRITICAL"
        elif risk_score >= 3.0:
            return "HIGH"
        elif risk_score >= 2.0:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _generate_recommendations(self, part_data: Dict, checklist_results: List[Dict[str, Any]], relevant_clauses: List[str]) -> List[str]:
        """권고사항 생성"""
        recommendations = []
        
        # 높은 위험도 항목들에 대한 권고사항
        high_risk_items = [item for item in checklist_results if item.get("risk_score", 0) >= 3.0]
        
        if high_risk_items:
            recommendations.append(f"총 {len(high_risk_items)}개의 고위험 항목이 발견되었습니다.")
            
            for item in high_risk_items:
                if item.get("recommendation"):
                    recommendations.append(f"• {item['recommendation']}")
        
        # 파트별 완화 전략 추가
        if part_data.get("mitigationStrategy"):
            recommendations.append(f"완화 전략: {part_data['mitigationStrategy']}")
        
        return recommendations

class SequentialRiskAnalyzer:
    """직렬 위험 분석기 - Rate limit 고려"""
    
    def __init__(self, risk_check_data: Dict, retriever, llm_generator, neo4j_driver=None):
        self.analyzer = PartRiskAnalyzer(risk_check_data, retriever, llm_generator, neo4j_driver)
        self.risk_check_data = risk_check_data
    
    async def analyze_all_parts(self, contract_text: str, contract_name: str = "계약서") -> Dict[str, Any]:
        """모든 파트를 직렬로 분석"""
        start_time = time.time()
        results = []
        
        # 파트별 순차 분석
        for part in self.risk_check_data["analysisParts"]:
            part_number = part["partNumber"]
            
            logging.info(f"Part {part_number} 분석 시작: {part['partTitle']}")
            
            try:
                # 파트별 분석 수행
                part_result = await self.analyzer.analyze_part(part_number, contract_text)
                results.append(part_result)
                
                logging.info(f"Part {part_number} 분석 완료 - 위험도: {part_result.risk_level}")
                
                # Rate limit 고려한 지연
                await asyncio.sleep(self.analyzer.rate_limit_delay)
                
            except Exception as e:
                logging.error(f"Part {part_number} 분석 실패: {e}")
                # 실패한 파트에 대한 기본 결과 생성
                results.append(PartAnalysisResult(
                    part_number=part_number,
                    part_title=part["partTitle"],
                    risk_score=0.0,
                    risk_level="UNKNOWN",
                    checklist_results=[],
                    relevant_clauses=[],
                    recommendations=[f"분석 실패: {str(e)}"],
                    analysis_time=0.0
                ))
        
        # 전체 분석 결과 통합
        total_time = time.time() - start_time
        overall_risk_score = sum(r.risk_score for r in results) / len(results) if results else 0.0
        
        return {
            "contract_name": contract_name,
            "analysis_date": datetime.now().isoformat(),
            "total_analysis_time": total_time,
            "overall_risk_score": overall_risk_score,
            "overall_risk_level": self.analyzer._determine_risk_level(overall_risk_score),
            "part_results": [self._serialize_part_result(r) for r in results],
            "summary": self._generate_summary(results)
        }
    
    def _serialize_part_result(self, result: PartAnalysisResult) -> Dict[str, Any]:
        """파트 결과 직렬화"""
        return {
            "part_number": result.part_number,
            "part_title": result.part_title,
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "checklist_results": result.checklist_results,
            "relevant_clauses": result.relevant_clauses,
            "recommendations": result.recommendations,
            "analysis_time": result.analysis_time
        }
    
    def _generate_summary(self, results: List[PartAnalysisResult]) -> Dict[str, Any]:
        """전체 요약 생성"""
        total_items = sum(len(r.checklist_results) for r in results)
        high_risk_parts = [r for r in results if r.risk_level in ["HIGH", "CRITICAL"]]
        
        return {
            "total_parts_analyzed": len(results),
            "total_checklist_items": total_items,
            "high_risk_parts": len(high_risk_parts),
            "critical_issues": [r.part_title for r in results if r.risk_level == "CRITICAL"],
            "top_recommendations": self._extract_top_recommendations(results)
        }
    
    def _extract_top_recommendations(self, results: List[PartAnalysisResult]) -> List[str]:
        """상위 권고사항 추출"""
        all_recommendations = []
        for result in results:
            all_recommendations.extend(result.recommendations)
        
        # 중복 제거 및 상위 5개 반환
        return list(set(all_recommendations))[:5]
