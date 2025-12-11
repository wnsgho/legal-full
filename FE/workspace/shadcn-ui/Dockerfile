# AutoSchemaKG Frontend Dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# pnpm 설치
RUN corepack enable && corepack prepare pnpm@8.10.0 --activate

# 의존성 파일 복사
COPY package.json pnpm-lock.yaml ./

# 의존성 설치 (lock 파일과 package.json 불일치 허용)
RUN pnpm install --no-frozen-lockfile

# 소스 코드 복사
COPY . .

# 환경변수 설정 (빌드 시점)
# Docker 환경에서는 nginx가 프록시하므로 기본값을 빈 문자열로 설정 (상대 경로 사용)
ARG VITE_API_BASE_URL=
ARG VITE_APP_TITLE="계약서 분석 AI"
ARG VITE_NEO4J_URI=bolt://localhost:7687
ARG VITE_NEO4J_USER=neo4j
ARG VITE_NEO4J_PASSWORD
ARG VITE_NEO4J_DATABASE=neo4j

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_APP_TITLE=$VITE_APP_TITLE
ENV VITE_NEO4J_URI=$VITE_NEO4J_URI
ENV VITE_NEO4J_USER=$VITE_NEO4J_USER
ENV VITE_NEO4J_PASSWORD=$VITE_NEO4J_PASSWORD
ENV VITE_NEO4J_DATABASE=$VITE_NEO4J_DATABASE

# 빌드
# 개발 모드로 빌드 (소스맵 포함, 최적화 덜 함)
# 또는 프로덕션 모드: RUN pnpm build
RUN pnpm build --mode development

# Production stage
FROM nginx:alpine AS production

# nginx 설정 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 빌드된 파일 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# 포트 노출
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

