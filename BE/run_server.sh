#!/bin/bash
# AutoSchemaKG 백엔드 서버 실행 스크립트 (Linux/macOS)

echo "🚀 AutoSchemaKG 백엔드 서버 시작 중..."

# Python 경로 설정
export PYTHONPATH=$(pwd)

# 환경변수 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️ .env 파일이 없습니다. env.example을 참고하여 .env 파일을 생성하세요."
    echo "📝 env.example 파일을 .env로 복사하고 설정을 수정하세요."
    exit 1
fi

# 서버 실행
python run_server.py


