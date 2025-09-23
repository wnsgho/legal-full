# 프론트엔드-백엔드 연결 가이드

## 개요

이 문서는 AutoSchemaKG 프로젝트의 프론트엔드와 백엔드 연결 방법을 설명합니다.

## 구현된 기능

### 1. 파일 업로드 및 파이프라인 실행

- **API 엔드포인트**: `POST /upload-and-run`
- **기능**: 파일 업로드와 파이프라인 실행을 한 번에 처리
- **지원 파일 형식**: JSON, TXT, MD
- **구현 위치**: `FileUpload.tsx`

### 2. 파이프라인 상태 조회

- **API 엔드포인트**: `GET /pipeline/status/{pipeline_id}`
- **기능**: 실시간 파이프라인 진행 상태 확인
- **폴링 간격**: 2초
- **구현 위치**: `AnalysisProgress.tsx`

### 3. AI 챗봇

- **API 엔드포인트**: `POST /chat`
- **기능**: 계약서 관련 질문 답변
- **구현 위치**: `ChatInterface.tsx`

### 4. 위험조항 분석

- **API 엔드포인트**: `POST /analysis/auto-risk`
- **기능**: 파이프라인 처리된 계약서 데이터 자동 위험조항 분석
- **구현 위치**: `RiskClauses.tsx`

### 5. 시스템 상태 확인

- **API 엔드포인트**: `GET /status`
- **기능**: RAG 시스템 및 Neo4j 연결 상태 확인
- **구현 위치**: `Dashboard.tsx`

## 환경 설정

### 1. 환경변수 설정

프론트엔드 루트 디렉토리에 `.env.local` 파일을 생성하고 다음 내용을 추가하세요:

```env
# API 설정
VITE_API_BASE_URL=http://localhost:8000

# 개발 환경 설정
VITE_APP_TITLE=계약서 분석 AI
VITE_APP_VERSION=1.0.0
```

### 2. 백엔드 서버 실행

```bash
cd BE
python backend_server.py
```

### 3. 프론트엔드 서버 실행

```bash
cd FE/workspace/shadcn-ui
npm install
npm run dev
```

## API 서비스 레이어

### 위치: `src/services/api.ts`

- 모든 백엔드 API 호출을 담당
- 타입 안전성을 위한 TypeScript 인터페이스 정의
- 에러 처리 및 응답 변환

### 주요 함수들:

- `uploadAndRunPipeline()`: 파일 업로드 및 파이프라인 실행
- `getPipelineStatus()`: 파이프라인 상태 조회
- `sendChatMessage()`: AI 챗봇 메시지 전송
- `autoAnalyzeRisks()`: 위험조항 자동 분석
- `getStatus()`: 시스템 상태 확인

## 컴포넌트별 연결 상태

### ✅ 완료된 연결

1. **FileUpload**: 백엔드 파일 업로드 API 연결
2. **AnalysisProgress**: 파이프라인 상태 폴링 구현
3. **ChatInterface**: AI 챗봇 API 연결
4. **RiskClauses**: 위험조항 분석 API 연결
5. **Dashboard**: 시스템 상태 확인 및 전체 통합

### 🔧 추가 구현 필요

1. **실제 채팅 메시지 저장/로드**: 현재는 로컬 상태로만 관리
2. **파일 목록 조회**: 업로드된 파일 목록을 백엔드에서 가져오기
3. **분석 결과 상세 보기**: 실제 분석 결과 데이터 표시

## CORS 설정

백엔드 서버에서 CORS가 이미 설정되어 있습니다:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 문제 해결

### 1. API 연결 실패

- 백엔드 서버가 실행 중인지 확인
- 환경변수 `VITE_API_BASE_URL`이 올바른지 확인
- 브라우저 개발자 도구에서 네트워크 탭 확인

### 2. CORS 오류

- 백엔드 서버의 CORS 설정 확인
- 프론트엔드와 백엔드가 같은 포트에서 실행되지 않는지 확인

### 3. 파일 업로드 실패

- 지원되는 파일 형식인지 확인 (JSON, TXT, MD)
- 파일 크기가 10MB 이하인지 확인

## 다음 단계

1. **실제 데이터 연동**: Mock 데이터를 실제 백엔드 데이터로 교체
2. **에러 처리 개선**: 더 상세한 에러 메시지 및 사용자 안내
3. **로딩 상태 개선**: 더 나은 사용자 경험을 위한 로딩 인디케이터
4. **테스트**: 전체 플로우에 대한 통합 테스트
