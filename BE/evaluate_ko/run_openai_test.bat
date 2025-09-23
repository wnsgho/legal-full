@echo off
chcp 65001 > nul
echo OpenAI GPT 전용 질문 테스트
echo ==========================

REM 환경 변수 확인
if "%OPENAI_API_KEY%"=="" (
    echo ❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.
    echo .env 파일을 확인하거나 환경변수를 설정하세요.
    pause
    exit /b 1
)

REM Python 스크립트 실행
python openai_only_test.py %*

pause
