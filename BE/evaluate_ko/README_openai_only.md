# OpenAI GPT 전용 질문 테스트

이 스크립트는 OpenAI GPT에 본문을 넣고 질문에 대한 답변을 생성하는 간단한 도구입니다.

## 파일

- `openai_only_test.py`: 메인 스크립트
- `run_openai_test.bat`: Windows 배치 파일
- `README_openai_only.md`: 이 파일

## 사용 방법

### 1. 환경 설정

```bash
# .env 파일에 OpenAI API 키 추가
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. 기본 사용법

```bash
# 기본 실행
python openai_only_test.py \
    --questions contract1_questions.json \
    --document uploads/contract_01.md

# 최대 10개 질문만 테스트
python openai_only_test.py \
    --questions question_C1_questions.json \
    --document uploads/contract_01.md \
    --max-questions 10

# 다른 모델 사용
python openai_only_test.py \
    --questions question_C1_questions.json \
    --document uploads/contract_01.md \
    --model gpt-4

# 상세 결과 출력
python openai_only_test.py \
    --questions question_C1_questions.json \
    --document uploads/contract_01.md \
    --detailed

# 결과 파일 지정
python openai_only_test.py \
    --questions question_C1_questions.json \
    --document uploads/contract_01.md \
    --output my_results.json
```

### 3. Windows에서 사용

```cmd
# 배치 파일 실행
run_openai_test.bat --questions question_C1_questions.json --document uploads/contract_01.md

# 최대 5개 질문만 테스트
run_openai_test.bat --questions question_C1_questions.json --document uploads/contract_01.md --max-questions 5
```

## 옵션 설명

- `--questions`: 질문 파일 경로 (필수)
- `--document`: 문서 파일 경로 (필수)
- `--output`: 결과 저장 파일 경로 (기본값: openai_only_results.json)
- `--max-questions`: 최대 질문 수 (기본값: 모든 질문)
- `--model`: OpenAI 모델 (기본값: gpt-4o)
- `--detailed`: 상세 결과 출력

## 지원 모델

- `gpt-4o` (기본값)
- `gpt-4`
- `gpt-3.5-turbo`

## 결과 예시

```json
{
  "metadata": {
    "timestamp": "2024-01-01T12:00:00",
    "model": "gpt-4o",
    "total_questions": 10
  },
  "test_results": [
    {
      "question_id": 1,
      "question": "이 계약서에서 독소조항이 있습니까?",
      "expected_answer": "예, 있습니다...",
      "openai_result": {
        "success": true,
        "answer": "이 계약서를 분석한 결과...",
        "processing_time": 3.45,
        "model": "gpt-4o",
        "tokens_used": 1500,
        "prompt_tokens": 1200,
        "completion_tokens": 300
      },
      "processing_time": 3.45
    }
  ],
  "analysis": {
    "summary": {
      "total_questions": 10,
      "successful_tests": 10,
      "success_rate": 100.0,
      "average_processing_time": 3.45,
      "total_tokens_used": 15000,
      "average_tokens_per_question": 1500
    }
  }
}
```

## 성능 지표

- **성공률**: OpenAI가 성공적으로 답변을 생성한 비율
- **처리 시간**: 평균 응답 시간 (초)
- **토큰 사용량**: 총 토큰 사용량 및 질문당 평균
- **모델 정보**: 사용된 OpenAI 모델

## 주의사항

1. **API 키**: OpenAI API 키가 필요합니다.
2. **비용**: 토큰 사용량에 따라 비용이 발생합니다.
3. **타임아웃**: 긴 문서의 경우 처리 시간이 오래 걸릴 수 있습니다.
4. **파일 형식**: 질문 파일은 JSON 형식이어야 합니다.

## 문제 해결

### API 키 오류

```bash
# 환경변수 확인
echo $OPENAI_API_KEY

# .env 파일 확인
cat .env | grep OPENAI_API_KEY
```

### 파일을 찾을 수 없음

```bash
# 파일 존재 확인
ls -la question_C1_questions.json
ls -la uploads/contract_01.md
```

### 메모리 부족

- `--max-questions` 옵션으로 질문 수를 제한하세요.
- 문서 크기를 줄이거나 청크 단위로 나누어 처리하세요.
