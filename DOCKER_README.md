# Docker로 AutoSchemaKG 실행하기

## 사전 요구사항

1. **Docker Desktop** 설치

   - Windows: https://docs.docker.com/desktop/windows/install/
   - Mac: https://docs.docker.com/desktop/mac/install/
   - Linux: https://docs.docker.com/engine/install/

2. **Docker Compose** (Docker Desktop에 포함됨)

3. **Neo4j Desktop** (로컬에서 실행)
   - https://neo4j.com/download/
   - 데이터베이스를 생성하고 **실행 중**인 상태여야 합니다

## 빠른 시작

### 1. Neo4j Desktop 설정

1. Neo4j Desktop을 실행합니다
2. 새 프로젝트/데이터베이스를 생성합니다
3. 데이터베이스를 **Start** 합니다
4. 비밀번호를 기억해두세요

### 2. 환경변수 설정

```bash
# env.docker.example 파일을 .env로 복사
cp env.docker.example .env

# .env 파일을 열어 설정
# 반드시 수정해야 할 항목:
# - OPENAI_API_KEY: OpenAI API 키
# - NEO4J_PASSWORD: Neo4j Desktop에서 설정한 비밀번호
```

### 3. Docker 컨테이너 빌드 및 실행

```bash
# 모든 서비스 빌드 및 실행
docker-compose up --build

# 백그라운드에서 실행
docker-compose up --build -d
```

### 4. 서비스 접속

- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **백엔드 API 문서**: http://localhost:8000/docs
- **Neo4j Browser**: Neo4j Desktop에서 Open 클릭

## Docker 명령어 모음

### 서비스 관리

```bash
# 서비스 시작
docker-compose up -d

# 서비스 중지
docker-compose down

# 서비스 재시작
docker-compose restart

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그 확인
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 개별 서비스 관리

```bash
# 백엔드만 재빌드
docker-compose up --build backend

# 프론트엔드만 재빌드
docker-compose up --build frontend

# 특정 서비스만 중지
docker-compose stop backend
```

### 캐시 삭제 및 재빌드

```bash
# 사용하지 않는 이미지/볼륨 정리
docker system prune -a

# 캐시 없이 완전 재빌드
docker-compose build --no-cache
```

## 서비스 구성

| 서비스        | 설명                       | 포트 |
| ------------- | -------------------------- | ---- |
| `backend`     | FastAPI 백엔드 서버        | 8000 |
| `frontend`    | React 프론트엔드 (Nginx)   | 3000 |
| Neo4j Desktop | 그래프 데이터베이스 (로컬) | 7687 |

## 개발 모드

개발 시에는 핫 리로드를 위해 백엔드/프론트엔드를 로컬에서 실행하는 것을 권장합니다.

```bash
# 백엔드 (별도 터미널)
cd BE && uvicorn app.main:app --reload

# 프론트엔드 (별도 터미널)
cd FE/workspace/shadcn-ui && pnpm dev
```

## 문제 해결

### Neo4j 연결 실패

1. **Neo4j Desktop이 실행 중인지 확인**

   - 데이터베이스 상태가 "Running"인지 확인

2. **비밀번호 확인**

   - `.env` 파일의 `NEO4J_PASSWORD`가 정확한지 확인

3. **포트 확인**

   - Neo4j Desktop이 기본 포트(7687)를 사용 중인지 확인

4. **Docker 네트워크 확인**
   - `host.docker.internal`이 호스트에 접근 가능한지 확인

### 백엔드 오류

```bash
# 백엔드 로그 확인
docker-compose logs -f backend

# 컨테이너 내부 접속
docker exec -it autoschema-backend bash
```

### 프론트엔드 빌드 실패

```bash
# 프론트엔드 캐시 삭제 후 재빌드
docker-compose build --no-cache frontend
```

### 메모리 부족

Docker Desktop 설정에서 메모리 할당량을 늘려주세요.

- 권장: 최소 4GB RAM

## 프로덕션 배포

프로덕션 환경에서는 추가적인 보안 설정이 필요합니다:

1. HTTPS 인증서 설정
2. 환경변수 보안 관리
3. 로그 모니터링 설정
4. 백업 스케줄 구성

자세한 내용은 관련 문서를 참조하세요.
