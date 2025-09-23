@echo off
chcp 65001 > nul
echo AutoSchemaKG vs OpenAI 성능 비교 테스트
echo ======================================

REM Python 스크립트 실행
python test_comparison.py

pause
