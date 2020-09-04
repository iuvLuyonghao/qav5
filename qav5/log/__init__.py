# -*- coding: utf-8 -*-
"""
Usage:
from qav5 import log
"""
import sys
import logging.config
import os
from logging.handlers import TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger
try:
    import simplejson as json
except (ImportError, SyntaxError):
    import json

_log_dir = os.environ.get('HULK_LOG_DIR', None)
_log_name = os.environ.get("HULK_LOG_NAME", "hulk.log")

if _log_dir and os.path.isdir(_log_dir):
    LOG_FILE = os.path.join(_log_dir, _log_name)
else:
    LOG_FILE = _log_name

# https://docs.python.org/2/library/logging.html#logrecord-attributes
simple_fmt = "%(asctime)s - %(levelname)s - %(funcName)s: %(message)s"
thread_fmt = "%(asctime)s - %(levelname)s - %(funcName)s - %(threadName)s: %(message)s"
json_formatter = jsonlogger.JsonFormatter(simple_fmt, json_encoder=json.JSONEncoder, json_ensure_ascii=False)
simple_formatter = logging.Formatter(simple_fmt)
thread_formatter = logging.Formatter(thread_fmt)

# json日志的handler
json_console_handler = logging.StreamHandler()
json_console_handler.setFormatter(json_formatter)
json_console_handler.setLevel(logging.INFO)
json_file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
json_file_handler.setFormatter(json_formatter)
json_file_handler.setLevel(logging.INFO)

# 非json日志handler
basic_console_handler = logging.StreamHandler()
basic_console_handler.setFormatter(simple_formatter)
basic_file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight")
basic_file_handler.setFormatter(thread_formatter)

# 日志默认配置
logging.config.dictConfig({"disable_existing_loggers": False, "version": 1})
logging.root.handlers = [json_console_handler, json_file_handler]  # 默认会添加一个默认的handler,需要移除
logging.root.setLevel(logging.INFO)
logging.getLogger("requests").setLevel(logging.WARN)


def handle_uncaught_exception(exctype, value, traceback):
    if issubclass(exctype, KeyboardInterrupt):
        sys.__excepthook__(exctype, value, traceback)
        return
    logging.root.error("Uncaught exception", exc_info=(exctype, value, traceback))
# sys.excepthook = handle_uncaught_exception


def disable_json_format_log():
    """关闭json格式的日志"""
    logging.root.removeHandler(json_console_handler)
    logging.root.removeHandler(json_file_handler)
    logging.root.addHandler(basic_console_handler)
    logging.root.addHandler(basic_file_handler)


def enable_json_format_log():
    """开启json格式的日志"""
    logging.root.removeHandler(basic_console_handler)
    logging.root.removeHandler(basic_file_handler)
    logging.root.addHandler(json_file_handler)
    logging.root.addHandler(json_console_handler)
