@echo off
chcp 65001 >nul
echo 질문 파일에 번호를 추가하는 스크립트
echo ======================================

REM 현재 디렉토리에서 questionset 폴더의 모든 질문 파일 처리
python add_question_numbers.py -d questionset/

echo.
echo 처리가 완료되었습니다.
pause
