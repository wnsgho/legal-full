@echo off
chcp 65001 >nul
REM AutoSchemaKG 백엔드 서버 실행 배치 파일 (Windows)

echo 🚀 AutoSchemaKG 백엔드 서버 시작 중...

REM Python 경로 설정
set PYTHONPATH=%CD%

REM 환경변수 파일 확인
if not exist ".env" (
    echo ⚠️ .env 파일이 없습니다. env.example을 참고하여 .env 파일을 생성하세요.
    echo 📝 env.example 파일을 .env로 복사하고 설정을 수정하세요.
    pause
    exit /b 1
)

REM 서버 실행
python run_server.py

pause
