# 범용 질문-답변 파서

다양한 형식의 질문-답변 텍스트 파일을 JSON 형식으로 변환하는 범용 파서입니다.

## 특징

- **장/부 구분 무시**: 제1부, 제1장 등의 구분을 무시하고 질문과 답변만 추출
- **다양한 형식 지원**: 여러 가지 질문-답변 형식을 자동으로 인식
- **자동 분류**: 질문 내용을 기반으로 카테고리, 난이도, 점수 자동 할당
- **배치 처리**: 여러 파일을 한 번에 처리 가능

## 지원하는 형식

### 1. 기본 형식

```
질문 1: 질문 내용
정답: 답변 내용

질문 2: 질문 내용
정답: 답변 내용
```

### 2. Q&A 형식

```
Q1: 질문 내용
답변: 답변 내용

Q2: 질문 내용
답변: 답변 내용
```

### 3. 번호 형식

```
1. 질문 내용
정답: 답변 내용

2. 질문 내용
정답: 답변 내용
```

## 사용법

### 1. 개별 파일 변환

```bash
python universal_question_parser.py
```

### 2. 배치 변환 (모든 파일)

```bash
python batch_convert_all.py
```

## 출력 형식

변환된 JSON 파일은 다음과 같은 구조를 가집니다:

```json
{
  "metadata": {
    "total_questions": 100,
    "categories": ["독소조항 패턴 분석", "계약 조항별 상세 분석"],
    "difficulties": ["쉬움", "중간", "고난도"],
    "total_points": 104
  },
  "questions": [
    {
      "question_id": 1,
      "question": "질문 내용",
      "answer": "답변 내용",
      "category": "독소조항 패턴 분석",
      "difficulty": "고난도",
      "points": 3
    }
  ]
}
```

## 자동 분류 규칙

### 카테고리 분류

- 질문 앞의 텍스트에서 "제X부:", "제X장:" 등의 패턴을 찾아 분류
- 없으면 "일반"으로 분류

### 난이도 분류

- **고난도**: 종합적, 심층, 구조적, 연계, 복합, 고급
- **중간**: 분석, 검토, 평가, 확인
- **쉬움**: 무엇, 언제, 얼마, 어떤, 누구

### 점수 계산

- **3점**: 종합적, 심층, 구조적, 연계 키워드 포함
- **2점**: 분석, 검토, 평가 키워드 포함
- **1점**: 기타

## 파일 구조

```
evaluate_ko/
├── questionset/                    # 원본 질문 파일들
│   ├── question_C1.txt
│   ├── question_C2.txt
│   └── ...
├── universal_question_parser.py    # 범용 파서
├── batch_convert_all.py           # 배치 변환 스크립트
├── check_converted_files.py       # 변환 결과 확인
└── README_universal_parser.md     # 이 파일
```

## 변환 결과

- `question_C1_questions.json` ~ `question_C5_questions.json`: 개별 파일 변환 결과
- `all_questions_combined.json`: 전체 통합 파일

## 문제 해결

### 질문이 추출되지 않는 경우

1. 파일 형식이 지원되지 않는 형식인지 확인
2. 질문과 답변 사이의 구분자가 명확한지 확인
3. `_parse_simple_format` 함수가 작동하는지 확인

### 카테고리 분류가 잘못된 경우

1. `_extract_category` 함수의 패턴을 수정
2. 질문 앞에 카테고리 정보가 있는지 확인

### 난이도/점수 분류가 잘못된 경우

1. `_extract_difficulty` 함수의 키워드를 수정
2. `_calculate_points` 함수의 규칙을 조정

## 예시

### 입력 (question_C1.txt)

```
제1부: 독소조항 패턴 분석

질문 1: 이 계약서에서 매수인에게 잠재적으로 매우 불리하게 작용할 수 있는 독소조항이나 구조적 결함이 있습니까?

정답: 예, 있습니다. 제15조(확인실사), 제28조(하자담보책임 기간)...
```

### 출력 (question_C1_questions.json)

```json
{
  "metadata": {
    "total_questions": 100,
    "categories": ["독소조항 패턴 분석"],
    "difficulties": ["고난도"],
    "total_points": 104
  },
  "questions": [
    {
      "question_id": 1,
      "question": "이 계약서에서 매수인에게 잠재적으로 매우 불리하게 작용할 수 있는 독소조항이나 구조적 결함이 있습니까?",
      "answer": "예, 있습니다. 제15조(확인실사), 제28조(하자담보책임 기간)...",
      "category": "독소조항 패턴 분석",
      "difficulty": "고난도",
      "points": 3
    }
  ]
}
```




