import logging
from logging import Logger
import os
import datetime
from atlas_rag.evaluation.benchmark import BenchMarkConfig
from atlas_rag.utils.utf8_logging import get_utf8_logger

def setup_logger(config:BenchMarkConfig, logger_name = "MyLogger", log_path = None) -> Logger:
    date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")    
    if log_path:
        log_file_path = log_path
    else:
        log_file_path = f'./log/{config.dataset_name}_event{config.include_events}_concept{config.include_concept}_{date_time}.log'
    
    # UTF-8 로거 생성
    return get_utf8_logger(
        name=logger_name,
        level=logging.INFO,
        log_file=log_file_path,
        max_bytes=50 * 1024 * 1024,
        backup_count=5
    )