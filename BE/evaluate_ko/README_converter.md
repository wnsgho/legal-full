# TXT to JSON 질문 변환기

이 도구는 TXT 형식의 질문 파일을 구조화된 JSON 형식으로 변환하는 자동화 스크립트입니다.

## 파일 구조

```
BE/
├── complete_txt_to_json_converter.py  # 메인 변환 클래스
├── convert_questions.py               # 간단한 실행 스크립트
├── question_validate_test.txt         # 입력 파일 (예제)
├── complete_question_validate_test.json # 출력 파일 (예제)
└── README_converter.md               # 이 파일
```

## 사용법

### 1. 기본 사용법

```bash
# 기본 변환 (question_validate_test.txt -> question_validate_test.json)
python convert_questions.py

# 특정 파일 변환
python convert_questions.py input.txt output.json
```

### 2. 프로그래밍 방식 사용

```python
from complete_txt_to_json_converter import CompleteQuestionConverter

# 파일에서 변환
converter = CompleteQuestionConverter("input.txt", "output.json")
converter.convert_from_file("input.txt")

# 텍스트에서 직접 변환
text_content = "제1부: ..."
converter = CompleteQuestionConverter()
converter.convert_from_text(text_content)
```

## 입력 파일 형식

TXT 파일은 다음과 같은 구조를 가져야 합니다:

```
제1부: 섹션 제목 (설명)

    질문 1: 질문 내용?

        정답: 답변 내용

    질문 2: 질문 내용?

        정답: 답변 내용

제2부: 다음 섹션 제목
...
```

## 출력 JSON 형식

```json
{
  "test_info": {
    "title": "계약서 분석 평가",
    "description": "M&A 계약서 분석을 위한 종합 평가 질문셋",
    "total_questions": 100,
    "sections": 2
  },
  "sections": [
    {
      "section_id": 1,
      "title": "제1부: 독소조항 패턴 분석",
      "description": "심층 추론 능력 평가",
      "questions": [
        {
          "question_id": 1,
          "original_question_id": 1,
          "question": "질문 내용",
          "answer": "답변 내용",
          "category": "독소조항",
          "difficulty": "high",
          "points": 10
        }
      ]
    }
  ]
}
```

## 자동 분류 기능

변환기는 질문 내용을 분석하여 자동으로 다음을 결정합니다:

- **카테고리**: 독소조항, 거래종결, 진술보증, 손해배상, 일반조항, 기타
- **난이도**: high, medium, low
- **점수**: 10점(high), 5점(medium), 3점(low)

## 특징

1. **자동 섹션 분리**: "제1부:", "제2부:" 등의 패턴으로 섹션을 자동 분리
2. **질문-답변 매칭**: 들여쓰기된 질문과 정답을 자동으로 매칭
3. **메타데이터 생성**: 카테고리, 난이도, 점수 자동 할당
4. **유니코드 지원**: 한글 텍스트 완벽 지원
5. **에러 처리**: 잘못된 형식에 대한 안전한 처리

## 예제 실행

```bash
# 예제 파일 변환
python convert_questions.py question_validate_test.txt my_questions.json

# 결과 확인
python -c "import json; data=json.load(open('my_questions.json', 'r', encoding='utf-8')); print(f'총 질문 수: {data[\"test_info\"][\"total_questions\"]}')"
```

## 요구사항

- Python 3.6+
- 표준 라이브러리만 사용 (외부 의존성 없음)

## 문제 해결

1. **인코딩 오류**: 파일이 UTF-8로 저장되어 있는지 확인
2. **섹션 인식 실패**: "제1부:", "제2부:" 형식으로 섹션 제목을 작성
3. **질문 인식 실패**: 질문은 "질문 1:", "질문 2:" 형식으로 작성
4. **정답 인식 실패**: 정답은 "정답:" 형식으로 작성하고 적절히 들여쓰기
