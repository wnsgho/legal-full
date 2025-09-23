# 자동 평가 시스템

JSON 형식의 질문 파일을 사용하여 API 서버의 `/chat` 엔드포인트를 통해 자동으로 질문을 전송하고 결과를 분석하는 시스템입니다.

## 파일 구조

```
BE/evaluate_ko/
├── auto_evaluation.py          # 메인 평가 클래스
├── run_evaluation.py          # 간편 실행 스크립트
├── complete_txt_to_json_converter.py  # TXT to JSON 변환기
├── convert_questions.py       # 변환 실행 스크립트
├── question_C1.txt           # 입력 질문 파일
├── complete_question_validate_test.json  # 변환된 JSON 파일
└── README_evaluation.md      # 이 파일
```

## 사용법

### 1. 사전 준비

#### 1.1 API 서버 실행

```bash
# BE 디렉토리에서 서버 실행
cd BE
python server.py
```

#### 1.2 API 연결 테스트

```bash
# API 연결 및 단일 질문 테스트
cd BE/evaluate_ko
python test_api.py
```

#### 1.3 질문 파일 준비

```bash
# TXT 파일을 JSON으로 변환
python convert_questions.py question_C1.txt complete_question_validate_test.json
```

### 2. 평가 실행

#### 2.1 간편 실행

```bash
python run_evaluation.py
```

#### 2.2 명령행 실행

```bash
# 전체 질문 평가
python auto_evaluation.py -i complete_question_validate_test.json

# 일부 질문만 평가 (처음 10개)
python auto_evaluation.py -i complete_question_validate_test.json -m 10

# 특정 범위 평가 (5번째부터 10개)
python auto_evaluation.py -i complete_question_validate_test.json -s 5 -m 10

# API URL 지정
python auto_evaluation.py -i complete_question_validate_test.json --api-url http://localhost:8000
```

### 3. 명령행 옵션

```bash
python auto_evaluation.py --help
```

- `-i, --input`: 입력 JSON 질문 파일 경로 (필수)
- `-o, --output`: 출력 결과 파일 경로 (기본: evaluation_results_YYYYMMDD_HHMMSS.json)
- `--api-url`: API 서버 URL (기본: http://localhost:8000)
- `-m, --max-questions`: 평가할 최대 질문 수
- `-s, --start-from`: 시작 질문 번호 (0부터)
- `-d, --delay`: 요청 간 지연 시간 (초, 기본: 1.0)
- `-t, --timeout`: API 요청 타임아웃 (초, 기본: 30)

## 출력 결과

### 1. 콘솔 출력

```
📊 평가 결과 요약
============================================================
총 질문 수: 100
성공한 질문: 85
실패한 질문: 15
성공률: 85.0%
평균 유사도: 0.723
평균 처리 시간: 2.34초
평균 API 처리 시간: 5.91초
평균 컨텍스트 수: 12.5개
총 검색된 컨텍스트: 1250개

📈 카테고리별 통계:
  독소조항: 8/10 (80.0%) - 점수: 72/100 (72.0%)
  거래종결: 15/18 (83.3%) - 점수: 68/90 (75.6%)
  진술보증: 25/30 (83.3%) - 점수: 120/150 (80.0%)
  손해배상: 20/25 (80.0%) - 점수: 95/125 (76.0%)
  일반조항: 17/17 (100.0%) - 점수: 85/85 (100.0%)

🎯 난이도별 통계:
  high: 15/20 (75.0%)
  medium: 35/40 (87.5%)
  low: 35/40 (87.5%)
============================================================
```

### 2. JSON 결과 파일

```json
{
  "evaluation_info": {
    "timestamp": "2024-01-15T10:30:00",
    "api_base_url": "http://localhost:8000",
    "total_questions": 100
  },
  "analysis": {
    "summary": {
      "total_questions": 100,
      "successful_questions": 85,
      "failed_questions": 15,
      "success_rate": 85.0,
      "average_similarity": 0.723,
      "average_processing_time": 2.34
    },
    "category_stats": { ... },
    "difficulty_stats": { ... }
  },
  "detailed_results": [
    {
      "question_id": 1,
      "original_question_id": 1,
      "question": "이 계약서에서 매수인에게 잠재적으로...",
      "expected_answer": "예, 있습니다. 제15조(확인실사)...",
      "actual_answer": "네, 이 계약서에는 여러 독소조항이...",
      "success": true,
      "processing_time": 2.1,
      "category": "독소조항",
      "difficulty": "high",
      "points": 10,
      "similarity_score": 0.85,
      "error_message": null
    }
  ]
}
```

## 평가 메트릭

### 1. 성공률 (Success Rate)

- API 호출이 성공적으로 완료된 질문의 비율
- `성공한 질문 수 / 전체 질문 수 * 100`

### 2. 유사도 점수 (Similarity Score)

- 예상 답변과 실제 답변 간의 키워드 기반 유사도
- 0.0 ~ 1.0 범위 (1.0이 완전 일치)

### 3. 카테고리별 분석

- 독소조항, 거래종결, 진술보증, 손해배상, 일반조항별 성과
- 각 카테고리별 성공률과 점수 획득률

### 4. 난이도별 분석

- high, medium, low 난이도별 성과
- 난이도에 따른 성공률 차이 분석

## 문제 해결

### 1. API 서버 연결 실패

```
❌ API 서버 연결 실패: Connection refused
```

**해결방법:**

- API 서버가 실행 중인지 확인: `python server.py`
- 포트 번호 확인 (기본: 8000)
- 방화벽 설정 확인

### 2. 질문 파일 로드 실패

```
❌ 질문 파일 로드 실패: [Errno 2] No such file or directory
```

**해결방법:**

- 입력 파일 경로 확인
- JSON 파일 형식 확인
- 파일 권한 확인

### 3. API 요청 타임아웃

```
❌ API 요청 타임아웃: 30초
```

**해결방법:**

- `--timeout` 옵션으로 타임아웃 시간 증가
- API 서버 성능 확인
- 네트워크 상태 확인

### 4. 메모리 부족

```
❌ 메모리 부족 오류
```

**해결방법:**

- `--max-questions` 옵션으로 질문 수 제한
- `--start-from` 옵션으로 배치 처리

## 고급 사용법

### 1. 배치 처리

```bash
# 100개 질문을 20개씩 5번에 나누어 처리
python auto_evaluation.py -i questions.json -s 0 -m 20 -o batch1.json
python auto_evaluation.py -i questions.json -s 20 -m 20 -o batch2.json
python auto_evaluation.py -i questions.json -s 40 -m 20 -o batch3.json
python auto_evaluation.py -i questions.json -s 60 -m 20 -o batch4.json
python auto_evaluation.py -i questions.json -s 80 -m 20 -o batch5.json
```

### 2. 결과 분석

```python
import json

# 결과 파일 로드
with open('evaluation_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 상세 분석
analysis = data['analysis']
print(f"전체 성공률: {analysis['summary']['success_rate']:.1f}%")

# 카테고리별 성과
for category, stats in analysis['category_stats'].items():
    print(f"{category}: {stats['successful']}/{stats['total']}")
```

### 3. 커스텀 유사도 계산

```python
from auto_evaluation import AutoEvaluator

# 커스텀 유사도 함수 정의
def custom_similarity(expected, actual):
    # 더 정교한 유사도 계산 로직
    pass

# 평가자 생성 및 실행
evaluator = AutoEvaluator()
evaluator.calculate_similarity = custom_similarity
results = evaluator.run_evaluation("questions.json")
```

## 성능 최적화

### 1. 요청 간 지연 조정

- 너무 짧으면 API 서버에 부하
- 너무 길면 평가 시간 증가
- 권장: 1.0 ~ 2.0초

### 2. 배치 크기 조정

- 메모리 사용량과 처리 시간의 균형
- 권장: 20 ~ 50개 질문

### 3. 타임아웃 설정

- API 응답 시간에 따라 조정
- 권장: 30 ~ 60초
