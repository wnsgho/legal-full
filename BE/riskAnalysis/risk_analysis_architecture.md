# 위험 분석 시스템 아키텍처

## 🎯 제안하는 위험 분석 플로우

### 1. 계층적 분석 구조

```
계약서 전체 → 파트별 분석 → 조항별 세부 분석 → 통합 결과
```

### 2. 개선된 분석 플로우

#### Phase 1: 파트별 리트리버 시스템

- 각 파트의 `crossClauseAnalysis`를 기반으로 관련 조항 검색
- `deepDiveChecklist`의 각 항목을 실제 계약서 조항과 매칭
- 조항별 위험도 평가

#### Phase 2: 위험도 평가 시스템

- `topRiskPattern`과 실제 조항 비교하여 위험도 산정
- 각 체크리스트 항목별 점수화 (0-5점)
- 파트별 종합 위험도 계산

#### Phase 3: 통합 리포트 생성

- 파트별 결과를 `계약서명.json`으로 통합
- 전체 위험도 대시보드 생성
- 개선 권고사항 제시

### 3. 구체적 구현 방안

#### A. 파트별 리트리버 구현

```python
class PartRiskRetriever:
    def __init__(self, part_number, risk_check_data):
        self.part_number = part_number
        self.part_data = risk_check_data[f"part{part_number}"]
        self.cross_clauses = self.part_data["crossClauseAnalysis"]
        self.checklist = self.part_data["deepDiveChecklist"]

    def retrieve_relevant_clauses(self, contract_text):
        # crossClauseAnalysis 기반으로 관련 조항 검색
        relevant_clauses = []
        for clause_type in self.cross_clauses:
            clauses = self.search_clauses_by_type(contract_text, clause_type)
            relevant_clauses.extend(clauses)
        return relevant_clauses

    def analyze_risk_items(self, relevant_clauses):
        # deepDiveChecklist 각 항목별로 분석
        risk_analysis = []
        for item in self.checklist:
            analysis = self.analyze_risk_item(item, relevant_clauses)
            risk_analysis.append(analysis)
        return risk_analysis
```

#### B. 위험도 평가 시스템

```python
class RiskEvaluator:
    def evaluate_risk_level(self, checklist_item, contract_clause):
        # 위험 패턴 매칭
        risk_score = 0

        # 1. 조항 존재 여부 (0-2점)
        if self.clause_exists(contract_clause):
            risk_score += 2
        elif self.partial_clause_exists(contract_clause):
            risk_score += 1

        # 2. 조항의 명확성 (0-2점)
        clarity_score = self.evaluate_clarity(contract_clause)
        risk_score += clarity_score

        # 3. 예외 조항 존재 여부 (0-1점)
        if self.has_exceptions(contract_clause):
            risk_score -= 1

        return min(5, max(0, risk_score))
```

#### C. 통합 리포트 생성

```python
class RiskReportGenerator:
    def generate_integrated_report(self, part_analyses):
        report = {
            "contract_name": "계약서명.json",
            "analysis_date": datetime.now().isoformat(),
            "overall_risk_score": self.calculate_overall_score(part_analyses),
            "part_analyses": part_analyses,
            "recommendations": self.generate_recommendations(part_analyses),
            "risk_summary": self.create_risk_summary(part_analyses)
        }
        return report
```

### 4. 추가 개선 방안

#### A. 동적 체크리스트 생성

- 계약서 유형에 따라 체크리스트 항목 동적 조정
- 업계별 특화 위험 요소 추가

#### B. 실시간 위험 모니터링

- 계약서 수정 시 실시간 위험도 재계산
- 변경사항별 위험도 영향 분석

#### C. 학습 기반 개선

- 과거 분석 결과를 통한 패턴 학습
- 위험도 예측 모델 정확도 향상

### 5. API 엔드포인트 설계

```python
# 위험 분석 시작
POST /api/risk-analysis/start
{
    "contract_id": "string",
    "analysis_type": "comprehensive" | "quick"
}

# 파트별 분석 결과 조회
GET /api/risk-analysis/{analysis_id}/part/{part_number}

# 통합 리포트 조회
GET /api/risk-analysis/{analysis_id}/report

# 실시간 분석 상태
GET /api/risk-analysis/{analysis_id}/status
```

이러한 구조로 구현하면 체계적이고 확장 가능한 위험 분석 시스템을 구축할 수 있습니다.
