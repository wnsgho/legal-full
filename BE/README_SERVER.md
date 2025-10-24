# AutoSchemaKG 백엔드 서버

지식그래프 기반 RAG 시스템을 위한 FastAPI 백엔드 서버입니다.

## 🚀 주요 기능

- **파일 업로드**: JSON, TXT, MD 파일 업로드 지원
- **ATLAS 파이프라인**: 지식그래프 구축 및 임베딩 생성
- **RAG 시스템**: 하이브리드 검색 기반 질문 답변
- **위험조항 분석**: 계약서 위험요소 자동 분석
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
DEFAULT_MODEL=gpt-4.1-mini

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
├── server.py              # 메인 서버 파일
├── run_server.py          # 서버 실행 스크립트
├── run_server.bat         # Windows 실행 배치 파일
├── run_server.sh          # Linux/macOS 실행 스크립트
├── requirements.txt       # Python 의존성
├── env.example           # 환경변수 예시
├── main_pipeline.py      # ATLAS 파이프라인
└── README_SERVER.md      # 이 파일
```
<img width="3840" height="2126" alt="Image" src="https://github.com/user-attachments/assets/51aa53c4-a17a-4a2f-9536-3064f042c458" />
