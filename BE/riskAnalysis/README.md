# 위험 분석 시스템

## 🎯 개요

계약서의 위험 조항을 파트별로 분석하는 시스템입니다. Rate limit을 고려한 직렬 처리와 점진적 분석을 통해 효율적인 위험 평가를 제공합니다.

## 🏗️ 아키텍처

### 핵심 구성 요소

1. **PartRiskAnalyzer**: 파트별 위험 분석기
2. **SequentialRiskAnalyzer**: 직렬 처리 분석기
3. **Risk Analysis API**: REST API 엔드포인트

### 분석 플로우

```
계약서 입력 → 파트별 순차 분석 → 조항 검색 → AI 분석 → 결과 통합 → 리포트 생성
```

## 📋 파트별 분석 구조

### 1. 거래의 기본 골격 (Part 1)

- **핵심 위험**: 계약 당사자의 법적 권한 부재와 '전체 합의' 조항 결합
- **분석 항목**: 계약 체결 권한, 전체 합의 조항, 협상 과정 합의사항
- **완화 전략**: 공식 문서 요구, 핵심 합의사항 명시적 포함

### 2. 거래 대상 자산의 정의 및 소유권 (Part 2)

- **핵심 위험**: '완전 희석 기준' 미명시로 인한 지분율 하락
- **분석 항목**: 주식 정의, 스톡옵션 처리, 소유권 보장
- **완화 전략**: 완전 희석 기준 명시, Cap Table 보증

### 3. 거래대금 산정 및 지급 메커니즘 (Part 3)

- **핵심 위험**: 순운전자본 조정 기준 모호로 인한 거래대금 부풀림
- **분석 항목**: 순운전자본 정의, 회계 관행 일관성, 분쟁 해결 절차
- **완화 전략**: 상세한 산정 원칙 부속서, 중립적 회계법인 결정권

### 4. 재무 상태 및 부채에 관한 진술 및 보장 (Part 4)

- **핵심 위험**: 미기재 부채 보증 부재로 인한 우발부채 발견
- **분석 항목**: 재무제표 정확성, 미기재 부채, 우발부채
- **완화 전략**: 명시적 미기재 부채 보증, 긴 손해배상 기간

### 5. 영업, 자산 및 법규 준수에 관한 진술 및 보장 (Part 5)

- **핵심 위험**: 포괄적 법규 준수 진술로 인한 규제 지뢰
- **분석 항목**: 인허가, 중요 계약, IP, 소송, 개인정보보호, 부패방지
- **완화 전략**: 구체적 법규 준수 보증, 특별 배상 조항

### 6. 계약 체결 후 종결까지의 운영 (Part 6)

- **핵심 위험**: 통상적 영업 과정 규정 모호로 인한 가치 훼손
- **분석 항목**: 확약 조항, 선행조건, MAE 정의
- **완화 전략**: 구체적 금지 행위 목록, MAE 예외 조항 축소

### 7. 계약 위반 시 구제수단 및 손해배상 (Part 7)

- **핵심 위험**: 낮은 배상 한도와 짧은 청구 기간
- **분석 항목**: 배상 한도, 최소 청구금액, 청구 기간, 손해 정의
- **완화 전략**: 합리적 Cap/Basket 설정, Anti-sandbagging 조항

### 8. 계약의 종료, 해제 및 위약금 (Part 8)

- **핵심 위험**: 일방적 계약 해제와 불균형한 위약금
- **분석 항목**: 해제 사유, 위약금, 이행 강제
- **완화 전략**: 상호 대등한 해제 조항, 합리적 위약금

### 9. 거래종결 후 의무 및 제한사항 (Part 9)

- **핵심 위험**: 과도한 경업금지와 불명확한 협조 의무
- **분석 항목**: 경업금지, 유인 금지, 비밀유지, 향후 협조
- **완화 전략**: 합리적 범위의 제한 조항, 명확한 협조 의무

### 10. 분쟁 해결 및 계약 해석 원칙 (Part 10)

- **핵심 위험**: 부적절한 준거법과 비효율적 분쟁 해결
- **분석 항목**: 준거법, 관할, 중재, 통지, 분리 가능성
- **완화 전략**: 안정된 준거법 선택, 신속한 중재 절차

## 🚀 사용법

### 1. 업로드된 파일 분석 (권장)

```python
# API 호출
POST /api/risk-analysis/analyze-uploaded-file
{
    "file_id": "file_id_here",
    "selected_parts": "all"  # 또는 "1,2,3" 형태로 특정 파트 선택
}
```

### 2. GPT 전용 분석

```python
# GPT만 사용한 빠른 분석
POST /api/risk-analysis/analyze-gpt-only
{
    "file_id": "file_id_here"
}
```

### 3. 분석 시작 (텍스트 직접 전달)

```python
# API 호출
POST /api/risk-analysis/start
{
    "contract_id": "contract_001",
    "contract_text": "계약서 내용...",
    "contract_name": "주식매수계약서",
    "selected_parts": [1, 2, 3]  # 선택적 파트 분석
}
```

### 4. 분석 상태 확인

```python
# 진행 상황 조회
GET /api/risk-analysis/{analysis_id}/status
```

### 5. 파트별 결과 조회

```python
# 특정 파트 결과
GET /api/risk-analysis/{analysis_id}/part/{part_number}
```

### 6. 전체 리포트 조회

```python
# 완료된 분석 리포트
GET /api/risk-analysis/{analysis_id}/report
```

### 7. 저장된 분석 결과 조회

```python
# 저장된 분석 결과 목록
GET /api/risk-analysis/saved

# 특정 파일의 분석 결과
GET /api/risk-analysis/saved/{file_id}

# GPT 분석 결과 목록
GET /api/risk-analysis/gpt-results

# RAG 구축된 계약서 목록
GET /api/risk-analysis/rag-contracts
```

## ⚙️ 설정

### Rate Limit 설정

```python
# part_risk_analyzer.py에서 조정
self.rate_limit_delay = 2.0  # API 호출 간격 (초)
```

### 분석 파라미터

```python
# LLM 생성 파라미터
max_tokens=500,
temperature=0.1  # 일관성을 위해 낮은 값
```

## 📊 결과 형식

### 파트별 분석 결과

```json
{
  "part_number": 1,
  "part_title": "거래의 기본 골격",
  "risk_score": 3.2,
  "risk_level": "HIGH",
  "checklist_results": [
    {
      "item": "계약서에 명시된 당사자의 법인명...",
      "risk_score": 4,
      "status": "DANGER",
      "analysis": "법인명 불일치 위험 발견",
      "recommendation": "법인 등기부 확인 필요"
    }
  ],
  "recommendations": [
    "법인 등기부와 정확히 일치하는지 확인",
    "대표이사 권한 확인"
  ],
  "analysis_time": 25.3
}
```

### 전체 분석 리포트

```json
{
    "contract_name": "주식매수계약서",
    "analysis_date": "2024-01-15T10:30:00",
    "total_analysis_time": 300.5,
    "overall_risk_score": 2.8,
    "overall_risk_level": "MEDIUM",
    "part_results": [...],
    "summary": {
        "total_parts_analyzed": 10,
        "overall_risk_score": 2.8,
        "overall_risk_level": "MEDIUM",
        "high_risk_parts": ["거래의 기본 골격", "재무 상태"],
        "total_analysis_time": 300.5
    }
}
```

## 🔧 개발 및 확장

### 새로운 파트 추가

1. `riskCheck.json`에 새 파트 추가
2. `PartRiskAnalyzer`에서 파트별 로직 구현
3. API 엔드포인트 업데이트

### 커스텀 분석 로직

```python
class CustomPartAnalyzer(PartRiskAnalyzer):
    async def _analyze_single_checklist_item(self, checklist_item, relevant_clauses, contract_text, part_data):
        # 커스텀 분석 로직 구현
        pass
```

## 📈 성능 최적화

### 1. 캐싱 전략

- 동일한 계약서 유형의 분석 결과 캐싱
- 파트별 중간 결과 저장

### 2. 병렬 처리

- 파트 내 체크리스트 항목 병렬 분석
- 조항 검색과 AI 분석 분리

### 3. 점진적 결과 제공

- 파트별 완료 시 즉시 결과 제공
- 실시간 진행 상황 업데이트

## 🛡️ 에러 처리

### 일반적인 에러 상황

1. **API Rate Limit**: 자동 재시도 및 지연
2. **LLM 응답 오류**: 기본값 반환 및 로깅
3. **조항 검색 실패**: 대체 검색 방법 사용
4. **분석 시간 초과**: 부분 결과 반환

### 복구 전략

- 실패한 파트에 대한 재분석
- 부분 결과를 통한 점진적 완성
- 사용자 알림 및 수동 개입 옵션
