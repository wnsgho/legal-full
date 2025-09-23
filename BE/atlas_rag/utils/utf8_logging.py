#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTF-8 로깅 유틸리티
Windows에서 이모지와 특수문자가 포함된 로깅을 안전하게 처리합니다.
"""

import sys
import io
import logging
from logging.handlers import RotatingFileHandler


def setup_utf8_environment():
    """Windows에서 UTF-8 출력을 위한 환경 설정"""
    if sys.platform.startswith('win'):
        # stdout과 stderr을 UTF-8로 설정
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class UTF8StreamHandler(logging.StreamHandler):
    """UTF-8 인코딩을 지원하는 스트림 핸들러"""
    
    def __init__(self, stream=None):
        super().__init__(stream)
        if stream is None:
            stream = sys.stdout
        self.stream = stream

    def emit(self, record):
        try:
            msg = self.format(record)
            # UTF-8로 인코딩하여 출력
            if hasattr(self.stream, 'buffer'):
                # 바이너리 스트림인 경우 UTF-8로 인코딩
                self.stream.buffer.write((msg + self.terminator).encode('utf-8'))
                self.stream.buffer.flush()
            else:
                # 텍스트 스트림인 경우 UTF-8로 인코딩하여 쓰기
                self.stream.write((msg + self.terminator).encode('utf-8').decode('utf-8'))
                self.stream.flush()
        except UnicodeEncodeError:
            # 이모지나 특수문자로 인한 인코딩 오류 시 안전하게 처리
            safe_msg = msg.encode('utf-8', errors='replace').decode('utf-8')
            if hasattr(self.stream, 'buffer'):
                self.stream.buffer.write((safe_msg + self.terminator).encode('utf-8'))
                self.stream.buffer.flush()
            else:
                self.stream.write(safe_msg + self.terminator)
                self.stream.flush()
        except Exception:
            self.handleError(record)


class UTF8RotatingFileHandler(RotatingFileHandler):
    """UTF-8 인코딩을 지원하는 로테이팅 파일 핸들러"""
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding='utf-8', delay=False):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)

    def emit(self, record):
        try:
            msg = self.format(record)
            # UTF-8로 인코딩하여 파일에 쓰기
            self.stream.write((msg + self.terminator).encode('utf-8').decode('utf-8'))
            self.stream.flush()
        except UnicodeEncodeError:
            # 이모지나 특수문자로 인한 인코딩 오류 시 안전하게 처리
            safe_msg = msg.encode('utf-8', errors='replace').decode('utf-8')
            self.stream.write(safe_msg + self.terminator)
            self.stream.flush()
        except Exception:
            self.handleError(record)


def setup_utf8_logging(level=logging.INFO, format_string=None, force=True):
    """UTF-8 로깅 설정을 초기화합니다"""
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 환경 설정
    setup_utf8_environment()
    
    # 로깅 설정
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[UTF8StreamHandler()],
        force=force
    )


def get_utf8_logger(name, level=logging.INFO, log_file=None, max_bytes=50*1024*1024, backup_count=5):
    """UTF-8 로깅을 지원하는 로거를 생성합니다"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 콘솔 핸들러 추가
    console_handler = UTF8StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (선택사항)
    if log_file:
        file_handler = UTF8RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
