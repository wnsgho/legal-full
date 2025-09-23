# AutoSchemaKG vs OpenAI 성능 비교

이 디렉토리는 AutoSchemaKG 프로젝트와 OpenAI GPT의 성능을 비교하는 도구들을 포함합니다.

## 파일 구조

- `openai_comparison.py`: 독립 실행형 비교 스크립트
- `run_comparison.py`: API 서버를 통한 비교 실행 스크립트
- `README_comparison.md`: 이 파일

## 사용 방법

### 1. 환경 설정

먼저 필요한 환경변수를 설정하세요:

```bash
# .env 파일에 추가
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. 독립 실행형 스크립트 사용

```bash
# 단일 질문 비교
python openai_comparison.py \
    --questions question_C1_questions.json \
    --document uploads/contract_01.md \
    --document-id contract_01 \
    --output comparison_results.json \
    --max-questions 10

# 모든 질문 비교
python openai_comparison.py \
    --questions question_C1_questions.json \
    --document uploads/contract_01.md \
    --document-id contract_01 \
    --output comparison_results.json
```

### 3. API 서버를 통한 비교

#### 서버 시작

```bash
cd BE
python server.py
```

#### 단일 질문 비교

```bash
python run_comparison.py \
    --mode single \
    --question "이 계약서에서 독소조항이 있습니까?" \
    --document-id contract_01 \
    --output single_result.json
```

#### 배치 비교

```bash
python run_comparison.py \
    --mode batch \
    --questions-file question_C1_questions.json \
    --document-id contract_01 \
    --max-questions 10 \
    --output batch_result.json
```

### 4. API 엔드포인트 직접 사용

#### 단일 질문 비교

```bash
curl -X POST "http://localhost:8000/compare-answers" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "question=이 계약서에서 독소조항이 있습니까?&document_id=contract_01"
```

#### 배치 비교

```bash
curl -X POST "http://localhost:8000/batch-compare" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "questions_file=question_C1_questions.json&document_id=contract_01&max_questions=10"
```

## 결과 분석

### 단일 질문 결과

```json
{
  "question": "질문 내용",
  "document_id": "contract_01",
  "atlas_result": {
    "success": true,
    "answer": "AutoSchemaKG 답변",
    "contexts": [...],
    "processing_time": 12.34,
    "context_count": 25
  },
  "openai_result": {
    "success": true,
    "answer": "OpenAI 답변",
    "processing_time": 3.45,
    "model": "gpt-4o",
    "tokens_used": 1500
  },
  "similarity": 0.234,
  "timestamp": "2024-01-01T12:00:00"
}
```

### 배치 비교 결과

```json
{
  "metadata": {
    "timestamp": "2024-01-01T12:00:00",
    "questions_file": "question_C1_questions.json",
    "document_id": "contract_01",
    "total_questions": 100,
    "max_questions": 10
  },
  "comparison_results": [...],
  "analysis": {
    "summary": {
      "total_questions": 10,
      "successful_comparisons": 10,
      "success_rate": 100.0,
      "average_similarity": 0.234,
      "average_atlas_time": 12.34,
      "average_openai_time": 3.45,
      "time_difference": 8.89
    }
  }
}
```

## 성능 지표

- **성공률**: 두 시스템 모두 성공적으로 답변을 생성한 비율
- **유사도**: 두 답변 간의 텍스트 유사도 (0-1, 높을수록 유사)
- **처리 시간**: 각 시스템의 평균 응답 시간
- **컨텍스트 수**: AutoSchemaKG가 사용한 컨텍스트 개수
- **토큰 사용량**: OpenAI가 사용한 토큰 수

## 주의사항

1. **API 키**: OpenAI API 키가 필요합니다.
2. **서버 상태**: API 서버가 실행 중이어야 합니다.
3. **문서 업로드**: 비교할 문서가 먼저 업로드되어야 합니다.
4. **타임아웃**: 긴 문서나 많은 질문의 경우 타임아웃이 발생할 수 있습니다.

## 문제 해결

### 서버 연결 실패

```bash
# 서버 상태 확인
curl http://localhost:8000/health

# 서버 재시작
cd BE
python server.py
```

### OpenAI API 오류

```bash
# API 키 확인
echo $OPENAI_API_KEY

# .env 파일 확인
cat .env | grep OPENAI_API_KEY
```

### 메모리 부족

- `--max-questions` 옵션으로 질문 수를 제한하세요.
- 문서 크기를 줄이거나 청크 단위로 나누어 처리하세요.
