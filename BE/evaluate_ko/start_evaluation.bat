@echo off
echo 🚀 자동 평가 시스템 시작
echo ================================

echo.
echo 1. API 서버 상태 확인 중...
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ API 서버가 실행되지 않았습니다.
    echo 먼저 'python server.py'로 API 서버를 실행하세요.
    pause
    exit /b 1
)
echo ✅ API 서버 연결 확인

echo.
echo 2. 질문 파일 확인 중...
if not exist "complete_question_validate_test.json" (
    echo ❌ 질문 파일을 찾을 수 없습니다.
    echo 먼저 'python convert_questions.py'를 실행하여 JSON 파일을 생성하세요.
    pause
    exit /b 1
)
echo ✅ 질문 파일 확인

echo.
echo 3. 평가 시작...
python run_evaluation.py

echo.
echo 🎉 평가 완료!
pause
