"""
위험 분석 결과 영구 저장을 위한 데이터 관리 모듈
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

class RiskAnalysisDataManager:
    """위험 분석 데이터 관리자"""
    
    def __init__(self, data_dir: str = "BE/riskAnalysis/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.results_file = self.data_dir / "risk_analysis_results.json"
        self.metadata_file = self.data_dir / "analysis_metadata.json"
    
    def save_analysis_result(self, analysis_id: str, result: Dict[str, Any]) -> bool:
        """분석 결과 저장"""
        try:
            # 기존 데이터 로드
            existing_data = self.load_all_results()
            
            # 새 결과 추가
            existing_data[analysis_id] = result
            
            # 파일에 저장
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            # 메타데이터 업데이트
            self._update_metadata(analysis_id, result)
            
            return True
        except Exception as e:
            print(f"❌ 분석 결과 저장 실패: {e}")
            return False
    
    def load_analysis_result(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """특정 분석 결과 로드"""
        try:
            all_results = self.load_all_results()
            return all_results.get(analysis_id)
        except Exception as e:
            print(f"❌ 분석 결과 로드 실패: {e}")
            return None
    
    def load_all_results(self) -> Dict[str, Any]:
        """모든 분석 결과 로드"""
        try:
            if not self.results_file.exists():
                return {}
            
            with open(self.results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 모든 분석 결과 로드 실패: {e}")
            return {}
    
    def delete_analysis_result(self, analysis_id: str) -> bool:
        """분석 결과 삭제"""
        try:
            all_results = self.load_all_results()
            if analysis_id in all_results:
                del all_results[analysis_id]
                
                with open(self.results_file, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, ensure_ascii=False, indent=2)
                
                self._update_metadata(analysis_id, None, delete=True)
                return True
            return False
        except Exception as e:
            print(f"❌ 분석 결과 삭제 실패: {e}")
            return False
    
    def get_analysis_list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """분석 목록 조회 (최신순)"""
        try:
            all_results = self.load_all_results()
            results_list = list(all_results.values())
            
            # 생성일 기준 정렬 (최신순)
            results_list.sort(
                key=lambda x: x.get('created_at', ''), 
                reverse=True
            )
            
            return results_list[:limit]
        except Exception as e:
            print(f"❌ 분석 목록 조회 실패: {e}")
            return []
    
    def search_analysis_results(self, query: str) -> List[Dict[str, Any]]:
        """분석 결과 검색"""
        try:
            all_results = self.load_all_results()
            matching_results = []
            
            query_lower = query.lower()
            
            for result in all_results.values():
                # 계약서명으로 검색
                if query_lower in result.get('contract_name', '').lower():
                    matching_results.append(result)
                    continue
                
                # 분석 결과 내용으로 검색
                analysis_result = result.get('analysis_result', {})
                if query_lower in str(analysis_result).lower():
                    matching_results.append(result)
                    continue
            
            return matching_results
        except Exception as e:
            print(f"❌ 분석 결과 검색 실패: {e}")
            return []
    
    def _update_metadata(self, analysis_id: str, result: Optional[Dict[str, Any]], delete: bool = False):
        """메타데이터 업데이트"""
        try:
            # 기존 메타데이터 로드
            metadata = {}
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            if delete:
                # 삭제된 경우 메타데이터에서 제거
                if analysis_id in metadata:
                    del metadata[analysis_id]
            else:
                # 새 결과의 메타데이터 추가
                metadata[analysis_id] = {
                    "analysis_id": analysis_id,
                    "contract_name": result.get('contract_name', ''),
                    "created_at": result.get('created_at', ''),
                    "analysis_type": result.get('analysis_type', ''),
                    "overall_risk_score": result.get('analysis_result', {}).get('overall_risk_score', 0),
                    "total_parts": len(result.get('analysis_result', {}).get('part_results', [])),
                    "file_size": len(str(result))
                }
            
            # 메타데이터 저장
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"❌ 메타데이터 업데이트 실패: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """분석 통계 조회"""
        try:
            all_results = self.load_all_results()
            
            if not all_results:
                return {
                    "total_analyses": 0,
                    "average_risk_score": 0,
                    "high_risk_analyses": 0,
                    "analysis_types": {}
                }
            
            total_analyses = len(all_results)
            risk_scores = []
            high_risk_count = 0
            analysis_types = {}
            
            for result in all_results.values():
                # 위험도 점수 수집
                overall_risk_score = result.get('analysis_result', {}).get('overall_risk_score', 0)
                risk_scores.append(overall_risk_score)
                
                if overall_risk_score >= 3.0:
                    high_risk_count += 1
                
                # 분석 유형별 통계
                analysis_type = result.get('analysis_type', 'unknown')
                analysis_types[analysis_type] = analysis_types.get(analysis_type, 0) + 1
            
            return {
                "total_analyses": total_analyses,
                "average_risk_score": sum(risk_scores) / len(risk_scores) if risk_scores else 0,
                "high_risk_analyses": high_risk_count,
                "analysis_types": analysis_types
            }
        except Exception as e:
            print(f"❌ 통계 조회 실패: {e}")
            return {}
    
    def cleanup_old_results(self, days: int = 30) -> int:
        """오래된 분석 결과 정리"""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            all_results = self.load_all_results()
            deleted_count = 0
            
            results_to_delete = []
            
            for analysis_id, result in all_results.items():
                created_at_str = result.get('created_at', '')
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        if created_at < cutoff_date:
                            results_to_delete.append(analysis_id)
                    except:
                        # 날짜 파싱 실패 시 스킵
                        continue
            
            # 오래된 결과 삭제
            for analysis_id in results_to_delete:
                if self.delete_analysis_result(analysis_id):
                    deleted_count += 1
            
            return deleted_count
        except Exception as e:
            print(f"❌ 오래된 결과 정리 실패: {e}")
            return 0

# 전역 데이터 매니저 인스턴스
data_manager = RiskAnalysisDataManager()
