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
    risk_clauses: List[str]  # 실제 위험으로 판단된 조항들
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
        
        # 위험 조항 추출
        risk_clauses = self._extract_risk_clauses(checklist_results, hybrid_results.get("relevant_clauses", []))
        
        return HybridPartAnalysisResult(
            part_number=part_number,
            part_title=part_data["partTitle"],
            risk_score=risk_score,
            risk_level=risk_level,
            checklist_results=checklist_results,
            relevant_clauses=hybrid_results.get("relevant_clauses", []),
            risk_clauses=risk_clauses,
            hybrid_search_results=hybrid_results,
            recommendations=recommendations,
            analysis_time=analysis_time
        )
    
    def _extract_risk_clauses(self, checklist_results: List[Dict], relevant_clauses: List[str]) -> List[str]:
        """체크리스트 결과에서 위험으로 판단된 조항들을 추출"""
        risk_clauses = []
        
        for result in checklist_results:
            # 위험도가 높은 항목들 (3점 이상)에서 관련 조항 추출
            if result.get("risk_score", 0) >= 3:
                # 분석 내용에서 조항 번호나 특정 조항을 찾아서 추출
                analysis = result.get("analysis", "")
                item = result.get("item", "")
                
                # 분석 내용에서 조항 번호 패턴 찾기 (예: "제19조", "제39조" 등)
                import re
                clause_patterns = re.findall(r'제\d+조', analysis)
                
                # 관련 조항에서 해당 조항들 찾기
                for clause in relevant_clauses:
                    for pattern in clause_patterns:
                        if pattern in clause:
                            if clause not in risk_clauses:
                                risk_clauses.append(clause)
        
        return risk_clauses
    
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
                    
                    print(f"🔍 search_result 타입: {type(search_result)}", flush=True)
                    print(f"🔍 search_result 내용: {search_result}", flush=True)
                    
                    if search_result:
                        if len(search_result) == 2:
                            sorted_context, context_ids = search_result
                            print(f"🔍 sorted_context 타입: {type(sorted_context)}", flush=True)
                            print(f"🔍 context_ids 타입: {type(context_ids)}", flush=True)
                            if sorted_context:
                                print(f"🔍 sorted_context 처리 시작", flush=True)
                                if isinstance(sorted_context, str):
                                    print(f"🔍 sorted_context가 문자열", flush=True)
                                    hybrid_results["relevant_clauses"].append(sorted_context)
                                else:
                                    print(f"🔍 sorted_context가 리스트, 길이: {len(sorted_context)}", flush=True)
                                    print(f"🔍 sorted_context 첫 번째 요소: {sorted_context[0] if sorted_context else 'None'}", flush=True)
                                    hybrid_results["relevant_clauses"].extend(sorted_context)
                        else:
                            print(f"🔍 search_result 길이가 2가 아님: {len(search_result)}", flush=True)
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
        print(f"🔍 _analyze_checklist_with_hybrid_results 시작", flush=True)
        print(f"🔍 hybrid_results 타입: {type(hybrid_results)}", flush=True)
        print(f"🔍 hybrid_results 내용: {hybrid_results}", flush=True)
        
        checklist_results = []
        try:
            relevant_clauses = hybrid_results.get("relevant_clauses", [])
            print(f"🔍 relevant_clauses 타입: {type(relevant_clauses)}", flush=True)
            print(f"🔍 relevant_clauses 길이: {len(relevant_clauses) if isinstance(relevant_clauses, list) else 'Not a list'}", flush=True)
        except Exception as e:
            print(f"🔍 relevant_clauses 접근 실패: {e}", flush=True)
            raise
        
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
            # LLM을 통한 분석 - 문자열 프롬프트를 메시지 배열로 변환
            messages = [{"role": "user", "content": prompt}]
            analysis_result = self.llm_generator.generate_response(
                messages,
                max_new_tokens=500,
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
        print(f"🔍 _parse_analysis_result 시작", flush=True)
        print(f"🔍 analysis_result 타입: {type(analysis_result)}", flush=True)
        print(f"🔍 analysis_result 내용: {analysis_result}", flush=True)
        print(f"🔍 checklist_item: {checklist_item}", flush=True)
        
        try:
            # JSON 파싱 시도 - ```json으로 감싸진 경우 처리
            json_text = analysis_result.strip()
            if json_text.startswith('```json'):
                # ```json으로 시작하는 경우 JSON 부분만 추출
                json_text = json_text[7:]  # ```json 제거
                if json_text.endswith('```'):
                    json_text = json_text[:-3]  # 끝의 ``` 제거
                json_text = json_text.strip()
            
            result = json.loads(json_text)
            print(f"🔍 JSON 파싱 성공: {result}", flush=True)
            result["item"] = checklist_item
            return result
        except json.JSONDecodeError as e:
            print(f"🔍 JSON 파싱 실패: {e}", flush=True)
            print(f"🔍 원본 텍스트: {analysis_result}", flush=True)
            # JSON 파싱 실패 시 기본값 반환
            return {
                "item": checklist_item,
                "risk_score": 3,
                "status": "WARNING",
                "analysis": analysis_result,
                "recommendation": "수동 검토 필요"
            }
        except Exception as e:
            print(f"🔍 _parse_analysis_result 예외: {e}", flush=True)
            raise
    
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
        print(f"🔍 analyze_all_parts_with_hybrid 시작", flush=True)
        print(f"🔍 contract_text 타입: {type(contract_text)}", flush=True)
        print(f"🔍 contract_name: {contract_name}", flush=True)
        print(f"🔍 risk_check_data 타입: {type(self.risk_check_data)}", flush=True)
        
        start_time = time.time()
        results = []
        
        try:
            print(f"🔍 analysisParts 접근 시도", flush=True)
            analysis_parts = self.risk_check_data["analysisParts"]
            print(f"🔍 analysisParts 타입: {type(analysis_parts)}", flush=True)
            print(f"🔍 analysisParts 길이: {len(analysis_parts)}", flush=True)
        except Exception as e:
            print(f"🔍 analysisParts 접근 실패: {e}", flush=True)
            raise
        
        # 파트별 순차 분석
        for i, part in enumerate(analysis_parts):
            print(f"🔍 파트 {i} 처리 시작", flush=True)
            print(f"🔍 part 타입: {type(part)}", flush=True)
            print(f"🔍 part 내용: {part}", flush=True)
            
            try:
                part_number = part["partNumber"]
                print(f"🔍 part_number: {part_number}", flush=True)
            except Exception as e:
                print(f"🔍 part_number 접근 실패: {e}", flush=True)
                raise
            
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
    
    async def analyze_selected_parts_with_hybrid(self, contract_text: str, contract_name: str, parts_to_analyze: List[int]) -> Dict[str, Any]:
        """하이브리드 리트리버를 사용한 선택된 파트 직렬 분석"""
        print(f"🔍 analyze_selected_parts_with_hybrid 시작 - 선택된 파트: {parts_to_analyze}", flush=True)
        
        start_time = time.time()
        results = []
        
        try:
            analysis_parts = self.risk_check_data["analysisParts"]
            print(f"🔍 analysisParts 길이: {len(analysis_parts)}", flush=True)
        except Exception as e:
            print(f"🔍 analysisParts 접근 실패: {e}", flush=True)
            raise
        
        # 선택된 파트만 순차 분석
        for i, part_number in enumerate(parts_to_analyze):
            print(f"🔍 선택된 파트 {part_number} 처리 시작", flush=True)
            
            # 해당 파트 데이터 찾기
            part_data = None
            for part in analysis_parts:
                if part["partNumber"] == part_number:
                    part_data = part
                    break
            
            if not part_data:
                print(f"🔍 파트 {part_number} 데이터를 찾을 수 없음", flush=True)
                continue
            
            logging.info(f"Part {part_number} 하이브리드 분석 시작: {part_data['partTitle']}")
            
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
                    part_title=part_data["partTitle"],
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
        if results:
            overall_risk_score = sum(r.risk_score for r in results) / len(results)
        else:
            overall_risk_score = 0.0
        
        print(f"🔍 선택된 파트 분석 완료 - 전체 위험도: {overall_risk_score}", flush=True)
        
        return {
            "contract_name": contract_name,
            "analysis_type": "hybrid_selected_parts_analysis",
            "selected_parts": parts_to_analyze,
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
