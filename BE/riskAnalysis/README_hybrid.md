# 하이브리드 리트리버 기반 위험 분석 시스템

## 🎯 개요

기존 `/chat` 기능에서 사용하는 `concept_enhanced_hybrid_retrieve` 함수를 활용한 고도화된 위험 분석 시스템입니다.

## 🔄 하이브리드 검색 플로우

### 1. 다단계 하이브리드 검색

```
파트별 핵심 질문 → Concept 추출 → Neo4j 직접 검색 → Concept 매칭 → Concept 확장 → HiPPO-RAG2 → 결과 재순위화
```

### 2. 파트별 검색 전략

- **핵심 질문**: `coreQuestion`을 기반으로 한 검색
- **위험 패턴**: `topRiskPattern`을 기반으로 한 검색
- **조항 분석**: `crossClauseAnalysis`를 기반으로 한 검색

## 🏗️ 아키텍처

### 핵심 구성 요소

1. **HybridRiskAnalyzer**: 하이브리드 리트리버를 활용한 파트별 분석기
2. **HybridSequentialRiskAnalyzer**: 직렬 처리 하이브리드 분석기
3. **Enhanced API**: 하이브리드 검색 결과를 포함한 API

### 검색 전략

```python
# 다중 쿼리 하이브리드 검색
search_queries = [
    core_question,        # "이 계약은 법적으로 유효하게 체결되었는가?"
    top_risk_pattern,     # "계약 당사자의 법적 권한 부재와 '전체 합의' 조항 결합"
    " ".join(cross_clauses)  # "전문/당사자 조항, 진술 및 보장 조항, 일반/기타 조항"
]
```

## 📊 하이브리드 검색 결과

### 검색 통계

```json
{
  "hybrid_search_stats": {
    "total_clauses_found": 45,
    "successful_searches": 8,
    "search_success_rate": 0.8
  }
}
```

### 상세 검색 결과

```json
{
    "hybrid_search_results": {
        "search_queries": [
            "이 계약은 법적으로 유효하게 체결되었는가?",
            "계약 당사자의 법적 권한 부재와 '전체 합의' 조항 결합"
        ],
        "relevant_clauses": [
            "제1조 (당사자) ...",
            "제2조 (계약의 성립) ..."
        ],
        "concept_results": [...],
        "hippo_results": [...],
        "neo4j_results": [...]
    }
}
```

## 🚀 사용법

### 1. 하이브리드 분석 시작

```python
# API 호출
POST /api/risk-analysis/start
{
    "contract_id": "contract_001",
    "contract_text": "계약서 내용...",
    "contract_name": "주식매수계약서"
}
```

### 2. 하이브리드 검색 결과 조회

```python
# 파트별 하이브리드 결과
GET /api/risk-analysis/{analysis_id}/part/{part_number}

# 응답 예시
{
    "part_number": 1,
    "part_title": "거래의 기본 골격",
    "risk_score": 3.2,
    "risk_level": "HIGH",
    "relevant_clauses": [
        "제1조 (당사자) ...",
        "제2조 (계약의 성립) ..."
    ],
    "hybrid_search_results": {
        "search_queries": [...],
        "relevant_clauses": [...],
        "concept_results": [...],
        "hippo_results": [...],
        "neo4j_results": [...]
    },
    "recommendations": [...]
}
```

## 🔍 하이브리드 검색의 장점

### 1. **다층 검색 전략**

- **Neo4j 직접 검색**: 키워드 기반 정확한 매칭
- **Concept 매칭**: 의미적 유사도 기반 검색
- **Concept 확장**: 관련 개념 확장 검색
- **HiPPO-RAG2**: 계층적 검색으로 정확도 향상

### 2. **파트별 맞춤 검색**

- 각 파트의 특성에 맞는 검색 쿼리 구성
- 위험 패턴과 조항 분석을 통한 정밀 검색
- 다중 검색 결과의 통합 및 재순위화

### 3. **검색 결과 품질 향상**

- 중복 제거 및 유사도 기반 재순위화
- 검색 성공률 모니터링
- 실패 시 폴백 전략

## ⚙️ 설정 및 최적화

### Rate Limit 고려

```python
# 하이브리드 검색 간격 조정
self.rate_limit_delay = 2.0  # API 호출 간격 (초)

# 파트별 검색 수량 조정
topN=15  # 파트별로 적절한 수량
```

### 검색 성능 최적화

```python
# 다중 쿼리 검색 최적화
search_queries = [
    core_question,        # 1차 검색
    top_risk_pattern,     # 2차 검색
    " ".join(cross_clauses)  # 3차 검색
]

# 각 쿼리별 하이브리드 검색 실행
for query in search_queries:
    search_result = concept_enhanced_hybrid_retrieve(
        query, enhanced_lkg_retriever, hippo_retriever,
        llm_generator, neo4j_driver, topN=15
    )
```

## 📈 성능 지표

### 검색 성공률

- **성공률**: 80% 이상 목표
- **검색 품질**: 관련 조항 발견 수
- **응답 시간**: 파트당 평균 30초 이내

### 위험 분석 정확도

- **체크리스트 매칭**: 90% 이상
- **위험도 평가**: 5점 척도 정확도
- **권고사항 품질**: 구체적이고 실행 가능한 제안

## 🔧 문제 해결

### 일반적인 문제

1. **검색 실패**: 폴백 전략으로 기본 검색 수행
2. **Rate Limit**: 자동 재시도 및 지연 처리
3. **결과 품질**: 다중 검색 결과 통합으로 개선

### 디버깅

```python
# 하이브리드 검색 로그 확인
logging.info(f"Part {part_number} 하이브리드 분석 시작")
logging.info(f"검색 쿼리: {search_queries}")
logging.info(f"검색 결과: {len(relevant_clauses)}개 조항 발견")
```

## 🚀 확장 가능성

### 1. **학습 기반 개선**

- 검색 성공률 기반 쿼리 최적화
- 위험 패턴 학습을 통한 검색 정확도 향상

### 2. **실시간 검색 품질 모니터링**

- 검색 결과 품질 평가
- 사용자 피드백 기반 개선

### 3. **커스텀 검색 전략**

- 계약서 유형별 맞춤 검색 전략
- 업계별 특화 검색 알고리즘
