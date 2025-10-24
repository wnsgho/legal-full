2025 서초 AI 칼리지 리걸케어팀(박재연, 최준호) 프로젝트 입니다.

지식그래프 기반 RAG 구축을 통한 계약서 위험 분석을 제공하는 Full-stack 프로젝트입니다. 백엔드는 FastAPI + Neo4j, 프런트엔드는 Vite + React + shadcn-ui를 사용합니다.

<img width="1904" height="1793" alt="Image" src="https://github.com/user-attachments/assets/442cd4e7-4193-4743-8fd0-78a1cfd75e69" />

## 📦 레포지토리 구조

```
AutoSchemaKG-1/
├── BE/                         # 백엔드 (FastAPI)
│   ├── server.py               # 메인 서버
│   ├── run_server.py           # 서버 실행 스크립트
│   ├── requirements.txt        # Python 의존성
│   ├── env.example             # 환경변수 예시
│   ├── README_SERVER.md        # 백엔드 전용 설명서
│   └── riskAnalysis/           # 위험분석 모듈
│       └── README.md           # 위험분석 시스템 설명서
└── FE/
    └── workspace/
        └── shadcn-ui/          # 프런트엔드 (Vite + React)
            └── README.md       # 프런트엔드 전용 설명서
```

## 🚀 빠른 시작

파이썬은 3.12 버전을 사용했습니다. conda 환경으로 사용했으며, conda 사용시 `conda install -c conda-forge faiss-gpu=1.8.0` 로 faiss-gpu를 먼저 설치하세요.

### 1) 백엔드 실행

```bash
cd BE
pip install -r requirements.txt
# 환경변수 파일 생성
# Windows
copy env.example .env
# Linux/macOS
cp env.example .env

# 서버 실행 (Windows)
run_server.bat
# 또는 (공통)
python run_server.py
```

- 기본 API 문서: http://localhost:8000/docs (Swagger), http://localhost:8000/redoc

### 2) 프런트엔드 실행

```bash
cd FE/workspace/shadcn-ui
pnpm i
or
npm i

pnpm run dev
or
npm run dev
```

- 기본 개발 서버: http://localhost:5173 (Vite 기본 포트)

## ⚙️ 환경변수

`FE/workspace/shadcn-ui/env.local.example`을 같은 폴더내 `.env.local`로 복사 후 값 수정,
`BE/env.example`를 같은 폴더내 `.env`로 복사 후 값 설정:

- 배포 환경에 따라 `NEO4J_URI`는 `neo4j`, `neo4j+s`, `bolt` 등을 사용할 수 있습니다.

## 🧠 주요 기능

- 파일 업로드 및 파이프라인 실행 (ATLAS 기반 지식그래프 구축/임베딩)
- 하이브리드 RAG 검색과 질의응답
- 계약서 위험 조항 분석 (파트별 체크리스트/직렬 처리/결과 통합)
- 실시간 상태 모니터링 및 로그

## 📚 핵심 API (요약)

- `POST /upload-and-run`: 파일 업로드 후 파이프라인 실행
- `POST /pipeline/run`: 파이프라인 실행
- `GET /pipeline/status/{pipeline_id}`: 파이프라인 상태
- `POST /chat`: RAG 기반 Q&A
- `POST /analyze-risks`: 계약서 위험분석
- 더 보기: http://localhost:8000/docs

## 🔗 세부 문서

- 백엔드 전용 가이드: `BE/README_SERVER.md`
- 위험분석 시스템: `BE/riskAnalysis/README.md`
- 프런트엔드 가이드: `FE/workspace/shadcn-ui/README.md`

## 🛠️ 트러블슈팅 (요약)

- Neo4j 연결 오류: Neo4j 실행 여부 및 접속 정보 확인 (`NEO4J_*`).
- OpenAI 오류: API Key/요금제/사용량 확인.
- CORS/프록시 이슈: 프런트 개발 서버와 백엔드 포트 확인, 필요 시 프록시 설정.
- 모델/설정 값 불일치: `.env`의 `DEFAULT_MODEL`이 코드 기본값과 일치하는지 확인.

## 🏗️ 아키텍처 개요

```
[FE] React(shadcn-ui, Vite)
   │  └─ REST 호출
[BE] FastAPI ── RAG/위험분석 서비스 계층
   ├─ ATLAS 파이프라인
   ├─ Neo4j (지식그래프)
   └─ OpenAI (LLM)
```
## 🅿️ 파이프라인 개요 
<img width="3840" height="2126" alt="Image" src="https://github.com/user-attachments/assets/51aa53c4-a17a-4a2f-9536-3064f042c458" />

## 📒 참고 문헌

- AutoSchemaKG: Autonomous Knowledge Graph Construction through Dynamic Schema Induction from Web-Scale Corpora
- Automating construction contract review using knowledge graph-enhanced large language models
