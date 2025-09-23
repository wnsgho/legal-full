#!/bin/bash
echo "🚀 자동 평가 시스템 시작"
echo "================================"

echo ""
echo "1. API 서버 상태 확인 중..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ API 서버가 실행되지 않았습니다."
    echo "먼저 'python server.py'로 API 서버를 실행하세요."
    exit 1
fi
echo "✅ API 서버 연결 확인"

echo ""
echo "2. 질문 파일 확인 중..."
if [ ! -f "complete_question_validate_test.json" ]; then
    echo "❌ 질문 파일을 찾을 수 없습니다."
    echo "먼저 'python convert_questions.py'를 실행하여 JSON 파일을 생성하세요."
    exit 1
fi
echo "✅ 질문 파일 확인"

echo ""
echo "3. 평가 시작..."
python run_evaluation.py

echo ""
echo "🎉 평가 완료!"
