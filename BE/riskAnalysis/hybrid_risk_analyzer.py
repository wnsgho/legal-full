"""
하이브리드 리트리버를 활용한 위험 분석 시스템
기존 /chat 기능의 concept_enhanced_hybrid_retrieve를 활용
"""

import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class HybridPartAnalysisResult:
    """하이브리드 파트별 분석 결과"""
    part_number: int
    part_title: str
    risk_score: float
    risk_level: str
    checklist_results: List[Dict[str, Any]]
    relevant_clauses: List[str]
    hybrid_search_results: Dict[str, Any]  # 하이브리드 검색 상세 결과
    recommendations: List[str]
    analysis_time: float

class HybridRiskAnalyzer:
    """하이브리드 리트리버를 활용한 위험 분석기"""
    
    def __init__(self, risk_check_data: Dict, enhanced_lkg_retriever, hippo_retriever, llm_generator, neo4j_driver):
        self.risk_check_data = risk_check_data
        self.enhanced_lkg_retriever = enhanced_lkg_retriever
        self.hippo_retriever = hippo_retriever
        self.llm_generator = llm_generator
        self.neo4j_driver = neo4j_driver
        self.rate_limit_delay = 2.0
        
    async def analyze_part_with_hybrid_retrieval(self, part_number: int, contract_text: str) -> HybridPartAnalysisResult:
        """하이브리드 리트리버를 사용한 파트별 위험 분석"""
        start_time = time.time()
        
        # 1. 파트 데이터 추출
        part_data = self._get_part_data(part_number)
        if not part_data:
            raise ValueError(f"Part {part_number} not found in risk check data")
        
        # 2. 하이브리드 검색 실행
        hybrid_results = await self._execute_hybrid_search(part_data, contract_text)
        
        # 3. 체크리스트 항목별 분석
        checklist_results = await self._analyze_checklist_with_hybrid_results(
            part_data, hybrid_results, contract_text
        )
        
        # 4. 위험도 계산
        risk_score = self._calculate_risk_score(checklist_results)
        risk_level = self._determine_risk_level(risk_score)
        
        # 5. 권고사항 생성
        recommendations = await self._generate_hybrid_recommendations(
            part_data, checklist_results, hybrid_results
        )
        
        analysis_time = time.time() - start_time
        
        return HybridPartAnalysisResult(
            part_number=part_number,
            part_title=part_data["partTitle"],
            risk_score=risk_score,
            risk_level=risk_level,
            checklist_results=checklist_results,
            relevant_clauses=hybrid_results.get("relevant_clauses", []),
            hybrid_search_results=hybrid_results,
            recommendations=recommendations,
            analysis_time=analysis_time
        )
    
    def _get_part_data(self, part_number: int) -> Optional[Dict]:
        """특정 파트의 데이터 추출"""
        for part in self.risk_check_data["analysisParts"]:
            if part["partNumber"] == part_number:
                return part
        return None
    
    async def _execute_hybrid_search(self, part_data: Dict, contract_text: str) -> Dict[str, Any]:
        """하이브리드 검색 실행"""
        try:
            # 파트별 검색 쿼리 구성
            core_question = part_data.get("coreQuestion", "")
            top_risk_pattern = part_data.get("topRiskPattern", "")
            cross_clauses = part_data.get("crossClauseAnalysis", [])
            
            # 다중 검색 쿼리 구성
            search_queries = [
                core_question,
                top_risk_pattern,
                " ".join(cross_clauses)
            ]
            
            hybrid_results = {
                "search_queries": search_queries,
                "relevant_clauses": [],
                "concept_results": [],
                "hippo_results": [],
                "neo4j_results": []
            }
            
            # 각 쿼리별로 하이브리드 검색 실행
            for query in search_queries:
                if not query.strip():
                    continue
                    
                try:
                    # 기존 하이브리드 리트리버 사용
                    from experiment.run_questions_v3_with_concept import concept_enhanced_hybrid_retrieve
                    
                    search_result = concept_enhanced_hybrid_retrieve(
                        query,
                        self.enhanced_lkg_retriever,
                        self.hippo_retriever,
                        self.llm_generator,
                        self.neo4j_driver,
                        topN=15  # 파트별로 적절한 수량
                    )
                    
                    if search_result:
                        if len(search_result) == 2:
                            sorted_context, context_ids = search_result
                            if sorted_context:
                                if isinstance(sorted_context, str):
                                    hybrid_results["relevant_clauses"].append(sorted_context)
                                else:
                                    hybrid_results["relevant_clauses"].extend(sorted_context)
                        else:
                            hybrid_results["relevant_clauses"].append(search_result)
                            
                except Exception as e:
                    logging.error(f"하이브리드 검색 실패 (쿼리: {query}): {e}")
                    continue
            
            # 중복 제거
            hybrid_results["relevant_clauses"] = list(set(hybrid_results["relevant_clauses"]))
            
            return hybrid_results
            
        except Exception as e:
            logging.error(f"하이브리드 검색 전체 실패: {e}")
            return {"relevant_clauses": [], "error": str(e)}
    
    async def _analyze_checklist_with_hybrid_results(self, part_data: Dict, hybrid_results: Dict, contract_text: str) -> List[Dict[str, Any]]:
        """하이브리드 검색 결과를 활용한 체크리스트 분석"""
        checklist_results = []
        relevant_clauses = hybrid_results.get("relevant_clauses", [])
        
        for i, checklist_item in enumerate(part_data.get("deepDiveChecklist", [])):
            # Rate limit 고려한 지연
            if i > 0:
                await asyncio.sleep(self.rate_limit_delay)
            
            # 하이브리드 검색 결과를 활용한 분석
            result = await self._analyze_single_checklist_with_hybrid(
                checklist_item, relevant_clauses, contract_text, part_data, hybrid_results
            )
            checklist_results.append(result)
        
        return checklist_results
    
    async def _analyze_single_checklist_with_hybrid(self, checklist_item: str, relevant_clauses: List[str], contract_text: str, part_data: Dict, hybrid_results: Dict) -> Dict[str, Any]:
        """하이브리드 검색 결과를 활용한 단일 체크리스트 분석"""
        
        # 하이브리드 검색 결과를 포함한 프롬프트 구성
        prompt = self._create_hybrid_analysis_prompt(checklist_item, relevant_clauses, part_data, hybrid_results)
        
        try:
            # LLM을 통한 분석
            analysis_result = await self.llm_generator.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.1
            )
            
            # 결과 파싱
            return self._parse_analysis_result(analysis_result, checklist_item)
            
        except Exception as e:
            logging.error(f"하이브리드 체크리스트 분석 오류: {e}")
            return {
                "item": checklist_item,
                "risk_score": 0,
                "status": "ERROR",
                "analysis": f"하이브리드 분석 중 오류 발생: {str(e)}",
                "recommendation": "수동 검토 필요"
            }
    
    def _create_hybrid_analysis_prompt(self, checklist_item: str, relevant_clauses: List[str], part_data: Dict, hybrid_results: Dict) -> str:
        """하이브리드 검색 결과를 포함한 분석 프롬프트 생성"""
        
        # 파트별 컨텍스트 정보
        part_title = part_data["partTitle"]
        top_risk_pattern = part_data["topRiskPattern"]
        core_question = part_data["coreQuestion"]
        mitigation_strategy = part_data["mitigationStrategy"]
        
        # 하이브리드 검색 결과 정보
        search_queries = hybrid_results.get("search_queries", [])
        
        prompt = f"""
당신은 계약서 위험 분석 전문가입니다. 다음 파트에 대해서만 분석해주세요:

**파트: {part_title}**
**핵심 위험 패턴: {top_risk_pattern}**
**핵심 질문: {core_question}**
**완화 전략: {mitigation_strategy}**

**하이브리드 검색 쿼리들:**
{chr(10).join(f"- {query}" for query in search_queries)}

**검색된 관련 조항들:**
{chr(10).join(f"- {clause}" for clause in relevant_clauses[:10])}

**분석할 체크리스트 항목: {checklist_item}**

위의 체크리스트 항목을 하이브리드 검색으로 찾은 관련 조항들과 비교하여 다음 형식으로 분석해주세요:

1. **위험도 점수**: 0-5점 (0=위험없음, 5=매우위험)
2. **상태**: SAFE, WARNING, DANGER, CRITICAL
3. **분석 내용**: 구체적인 위험 요소와 근거 (검색된 조항 인용)
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
                "risk_score": 3,
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
    
    async def _generate_hybrid_recommendations(self, part_data: Dict, checklist_results: List[Dict[str, Any]], hybrid_results: Dict) -> List[str]:
        """하이브리드 검색 결과를 활용한 권고사항 생성"""
        recommendations = []
        
        # 높은 위험도 항목들에 대한 권고사항
        high_risk_items = [item for item in checklist_results if item.get("risk_score", 0) >= 3.0]
        
        if high_risk_items:
            recommendations.append(f"총 {len(high_risk_items)}개의 고위험 항목이 발견되었습니다.")
            
            for item in high_risk_items:
                if item.get("recommendation"):
                    recommendations.append(f"• {item['recommendation']}")
        
        # 하이브리드 검색 결과 기반 추가 권고사항
        if hybrid_results.get("relevant_clauses"):
            recommendations.append(f"하이브리드 검색으로 {len(hybrid_results['relevant_clauses'])}개의 관련 조항을 발견했습니다.")
        
        # 파트별 완화 전략 추가
        if part_data.get("mitigationStrategy"):
            recommendations.append(f"완화 전략: {part_data['mitigationStrategy']}")
        
        return recommendations

class HybridSequentialRiskAnalyzer:
    """하이브리드 리트리버를 활용한 직렬 위험 분석기"""
    
    def __init__(self, risk_check_data: Dict, enhanced_lkg_retriever, hippo_retriever, llm_generator, neo4j_driver):
        self.analyzer = HybridRiskAnalyzer(risk_check_data, enhanced_lkg_retriever, hippo_retriever, llm_generator, neo4j_driver)
        self.risk_check_data = risk_check_data
    
    async def analyze_all_parts_with_hybrid(self, contract_text: str, contract_name: str = "계약서") -> Dict[str, Any]:
        """하이브리드 리트리버를 사용한 모든 파트 직렬 분석"""
        start_time = time.time()
        results = []
        
        # 파트별 순차 분석
        for part in self.risk_check_data["analysisParts"]:
            part_number = part["partNumber"]
            
            logging.info(f"Part {part_number} 하이브리드 분석 시작: {part['partTitle']}")
            
            try:
                # 파트별 하이브리드 분석 수행
                part_result = await self.analyzer.analyze_part_with_hybrid_retrieval(part_number, contract_text)
                results.append(part_result)
                
                logging.info(f"Part {part_number} 하이브리드 분석 완료 - 위험도: {part_result.risk_level}")
                
                # Rate limit 고려한 지연
                await asyncio.sleep(self.analyzer.rate_limit_delay)
                
            except Exception as e:
                logging.error(f"Part {part_number} 하이브리드 분석 실패: {e}")
                # 실패한 파트에 대한 기본 결과 생성
                results.append(HybridPartAnalysisResult(
                    part_number=part_number,
                    part_title=part["partTitle"],
                    risk_score=0.0,
                    risk_level="UNKNOWN",
                    checklist_results=[],
                    relevant_clauses=[],
                    hybrid_search_results={"error": str(e)},
                    recommendations=[f"하이브리드 분석 실패: {str(e)}"],
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
            "part_results": [self._serialize_hybrid_part_result(r) for r in results],
            "summary": self._generate_hybrid_summary(results)
        }
    
    def _serialize_hybrid_part_result(self, result: HybridPartAnalysisResult) -> Dict[str, Any]:
        """하이브리드 파트 결과 직렬화"""
        return {
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
    
    def _generate_hybrid_summary(self, results: List[HybridPartAnalysisResult]) -> Dict[str, Any]:
        """하이브리드 분석 전체 요약 생성"""
        total_items = sum(len(r.checklist_results) for r in results)
        high_risk_parts = [r for r in results if r.risk_level in ["HIGH", "CRITICAL"]]
        
        # 하이브리드 검색 통계
        total_clauses_found = sum(len(r.relevant_clauses) for r in results)
        successful_searches = len([r for r in results if not r.hybrid_search_results.get("error")])
        
        return {
            "total_parts_analyzed": len(results),
            "total_checklist_items": total_items,
            "high_risk_parts": len(high_risk_parts),
            "critical_issues": [r.part_title for r in results if r.risk_level == "CRITICAL"],
            "hybrid_search_stats": {
                "total_clauses_found": total_clauses_found,
                "successful_searches": successful_searches,
                "search_success_rate": successful_searches / len(results) if results else 0
            },
            "top_recommendations": self._extract_top_recommendations(results)
        }
    
    def _extract_top_recommendations(self, results: List[HybridPartAnalysisResult]) -> List[str]:
        """상위 권고사항 추출"""
        all_recommendations = []
        for result in results:
            all_recommendations.extend(result.recommendations)
        
        # 중복 제거 및 상위 5개 반환
        return list(set(all_recommendations))[:5]
