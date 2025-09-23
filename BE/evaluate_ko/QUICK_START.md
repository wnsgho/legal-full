# 🚀 빠른 시작 가이드

## 1단계: API 서버 실행

```bash
cd BE
python server.py
```

## 2단계: API 연결 테스트

```bash
cd BE/evaluate_ko
python test_api.py
```

## 3단계: 질문 파일 준비

```bash
python convert_questions.py question_C1.txt complete_question_validate_test.json
```

## 4단계: 평가 실행

### 빠른 테스트 (5개 질문)

```bash
python quick_test.py
```

### 전체 평가

```bash
python run_evaluation.py
```

### 명령행 실행

```bash
# 전체 질문 평가
python auto_evaluation.py -i question_C2_question.json -t 50

# 일부만 평가 (처음 10개)
python auto_evaluation.py -i complete_question_validate_test.json -m 10
```

## 📊 결과 확인

평가 완료 후 다음 파일들이 생성됩니다:

- `evaluation_results_YYYYMMDD_HHMMSS.json` - 상세 결과
- 콘솔에 요약 통계 출력

## 🔧 문제 해결

### API 서버 연결 실패

- `python server.py`로 서버가 실행 중인지 확인
- 포트 8000이 사용 중인지 확인

### 질문 파일 없음

- `python convert_questions.py`로 JSON 파일 생성

### 메모리 부족

- `-m` 옵션으로 질문 수 제한
- `-s` 옵션으로 배치 처리

## 📈 평가 메트릭

- **성공률**: API 호출 성공 비율
- **유사도**: 예상 답변과 실제 답변의 유사도 (0-1)
- **컨텍스트 수**: 검색된 관련 문서 수
- **처리 시간**: 전체 및 API 처리 시간
- **카테고리별**: 독소조항, 거래종결, 진술보증 등
- **난이도별**: high, medium, low
