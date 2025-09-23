#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoSchemaKG 백엔드 서버 실행 스크립트
"""

import os
import sys
import uvicorn
import io
from pathlib import Path

# Windows에서 UTF-8 출력을 위한 설정
if sys.platform.startswith('win'):
    # stdout과 stderr을 UTF-8로 설정
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def main():
    """서버 실행"""
    # 환경변수에서 설정 읽기
    host = os.getenv('SERVER_HOST', '0.0.0.0')
    port = int(os.getenv('SERVER_PORT', 8000))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    log_level = os.getenv('LOG_LEVEL', 'info').lower()
    
    print(f"🚀 AutoSchemaKG 백엔드 서버 시작 중...")
    print(f"📍 호스트: {host}")
    print(f"🔌 포트: {port}")
    print(f"🐛 디버그 모드: {debug}")
    print(f"📝 로그 레벨: {log_level}")
    print(f"🌐 서버 URL: http://{host}:{port}")
    print(f"📚 API 문서: http://{host}:{port}/docs")
    print("=" * 50)
    
    # 서버 실행
    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        reload=debug,
        log_level=log_level,
        access_log=True
    )

if __name__ == "__main__":
    main()
