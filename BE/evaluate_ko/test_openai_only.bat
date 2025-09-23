@echo off
chcp 65001 > nul
echo OpenAI 전용 테스트 스크립트 검증
echo ===============================

REM Python 스크립트 실행
python test_openai_only.py

pause
