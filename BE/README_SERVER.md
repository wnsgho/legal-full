# AutoSchemaKG 백엔드 서버

지식그래프 기반 RAG 시스템을 위한 FastAPI 백엔드 서버입니다.

## 🚀 주요 기능

- **파일 업로드**: JSON, TXT, MD 파일 업로드 지원
- **ATLAS 파이프라인**: 지식그래프 구축 및 임베딩 생성
- **RAG 시스템**: 하이브리드 검색 기반 질문 답변
- **위험조항 분석**:
  - 하이브리드 리트리버 기반 분석 (Neo4j + Concept + HiPPO-RAG2)
  - GPT 전용 분석
  - 10개 파트별 체크리스트 분석
  - 분석 결과 저장 및 조회
- **실시간 상태 모니터링**: 파이프라인 실행 상태 추적

## 📋 요구사항

- Python 3.9+
- Neo4j Desktop 또는 Neo4j Server
- OpenAI API 키

## 🛠️ 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`env.example` 파일을 `.env`로 복사하고 설정을 수정하세요:

```bash
cp env.example .env
```

`.env` 파일에서 다음 설정을 수정하세요:

```env
# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-4.1-2025-04-14

# Neo4j 데이터베이스 설정
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
NEO4J_DATABASE=neo4j

# 데이터 디렉토리 설정
DATA_DIRECTORY=BE/example_data
IMPORT_DIRECTORY=BE/import
```

### 3. 서버 실행

#### Windows

```bash
run_server.bat
```

#### Linux/macOS

```bash
./run_server.sh
```

#### 직접 실행

```bash
python run_server.py
```

## 📚 API 엔드포인트

### 기본 엔드포인트

- `GET /` - 서버 상태 확인
- `GET /health` - 헬스 체크
- `GET /status` - 시스템 상태 조회
- `GET /api/docs` - API 문서 정보

### 파일 관리

- `POST /upload/contract` - 계약서 파일 업로드
- `GET /files` - 업로드된 파일 목록 조회
- `DELETE /files/{file_id}` - 업로드된 파일 삭제

### 파이프라인 관리

- `POST /pipeline/run` - ATLAS 파이프라인 실행
- `POST /pipeline/run-with-file` - 업로드된 파일로 파이프라인 실행
- `POST /upload-and-run` - 파일 업로드와 파이프라인 실행을 한 번에 처리
- `GET /pipeline/status/{pipeline_id}` - 파이프라인 실행 상태 조회

### 챗봇 및 분석

- `POST /chat` - 챗봇 질문 처리
- `POST /analyze-risks` - 계약서 위험조항 분석
- `GET /chat/history` - 챗봇 대화 기록 조회
- `DELETE /chat/history` - 챗봇 대화 기록 삭제

### 위험 분석 (하이브리드 리트리버 기반)

- `POST /api/risk-analysis/start` - 위험 분석 시작
- `POST /api/risk-analysis/analyze-uploaded-file` - 업로드된 파일 분석
- `POST /api/risk-analysis/analyze-gpt-only` - GPT 전용 위험 분석
- `GET /api/risk-analysis/{analysis_id}/status` - 분석 상태 조회
- `GET /api/risk-analysis/{analysis_id}/part/{part_number}` - 파트별 결과 조회
- `GET /api/risk-analysis/{analysis_id}/report` - 전체 리포트 조회
- `GET /api/risk-analysis/saved` - 저장된 분석 결과 목록
- `GET /api/risk-analysis/saved/{file_id}` - 특정 파일의 분석 결과 조회
- `GET /api/risk-analysis/gpt-results` - GPT 분석 결과 목록
- `GET /api/risk-analysis/rag-contracts` - RAG 구축된 계약서 목록
- `DELETE /api/risk-analysis/{analysis_id}` - 분석 세션 삭제

## 🔧 사용 예시

### 1. 파일 업로드 및 파이프라인 실행

```bash
curl -X POST "http://localhost:8000/upload-and-run" \
  -F "file=@contract.json" \
  -F "start_step=1"
```

### 2. 챗봇 질문

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "이 계약서의 주요 위험요소는 무엇인가요?",
    "max_tokens": 2048,
    "temperature": 0.5
  }'
```

### 3. 위험조항 분석

#### 하이브리드 리트리버 기반 분석 (권장)

```bash
# 업로드된 파일 분석
curl -X POST "http://localhost:8000/api/risk-analysis/analyze-uploaded-file" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "file_id_here",
    "selected_parts": "all"
  }'

# 분석 상태 확인
curl -X GET "http://localhost:8000/api/risk-analysis/{analysis_id}/status"

# 전체 리포트 조회
curl -X GET "http://localhost:8000/api/risk-analysis/{analysis_id}/report"
```

#### GPT 전용 분석

```bash
curl -X POST "http://localhost:8000/api/risk-analysis/analyze-gpt-only" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "file_id_here"
  }'
```

#### 기존 분석 API

```bash
curl -X POST "http://localhost:8000/analyze-risks" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "계약서의 위험조항을 분석해주세요"
  }'
```

### 4. 파이프라인 상태 확인

```bash
curl -X GET "http://localhost:8000/pipeline/status/{pipeline_id}"
```

## 📊 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔍 문제 해결

### 일반적인 문제

1. **Neo4j 연결 실패**

   - Neo4j Desktop이 실행 중인지 확인
   - 연결 정보가 올바른지 확인

2. **OpenAI API 오류**

   - API 키가 유효한지 확인
   - API 사용량 한도 확인

3. **파이프라인 실행 실패**
   - 로그를 확인하여 구체적인 오류 메시지 확인
   - 필요한 의존성이 설치되었는지 확인

### 로그 확인

서버 실행 시 콘솔에 상세한 로그가 출력됩니다. 오류 발생 시 로그를 확인하여 문제를 진단하세요.

## 🏗️ 아키텍처

```
BE/
├── app/                   # FastAPI 애플리케이션
│   ├── main.py           # 메인 애플리케이션
│   ├── api/              # API 엔드포인트
│   ├── core/             # 핵심 설정 (config.py)
│   ├── services/         # 비즈니스 로직
│   └── schemas/          # Pydantic 스키마
├── riskAnalysis/         # 위험 분석 모듈
│   ├── hybrid_risk_analyzer.py    # 하이브리드 리트리버 기반 분석기
│   ├── simple_gpt_risk_analyzer.py # GPT 전용 분석기
│   ├── risk_analysis_api.py       # 위험 분석 API
│   └── data_persistence.py         # 분석 결과 저장
├── atlas_rag/            # ATLAS RAG 시스템
├── run_server.py         # 서버 실행 스크립트
├── run_server.bat        # Windows 실행 배치 파일
├── run_server.sh         # Linux/macOS 실행 스크립트
├── requirements.txt      # Python 의존성
├── env.example           # 환경변수 예시
├── main_pipeline.py      # ATLAS 파이프라인
└── README_SERVER.md      # 이 파일
```
