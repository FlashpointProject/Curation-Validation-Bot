import datetime
import inspect
import logging
import os

import colorlog

LOGFILE_PATH = "logs"
LEVELS = {
    1: 'TTRACE',
    5: 'TRACE',
    10: 'DEBUG',
    20: 'INFO',
    30: 'WARNING',
    40: 'ERROR',
    50: 'CRITICAL',
}
LOGGING_LEVEL = 'TTRACE'
loggers = {}

logging.addLevelName(1, LEVELS[1])
logging.addLevelName(5, LEVELS[5])
handler = logging.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    "%(log_color)s%(message)s",
    datefmt='%Y-%d-%m %H:%M:%S',
    reset=True,
    log_colors={
        'TTRACE': 'purple',
        'TRACE': 'blue',
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    },
    secondary_log_colors={},
    style='%'
))


def format_message(msg, func, level):
    return f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}][{LEVELS[level]}][{os.getpid()}][{func.co_filename}:{func.co_firstlineno}] -- {msg}"


# Yes, very hacky, but it does what I need it to do
def getLogger(name: str):
    if loggers.get(name) is not None:
        return loggers[name]

    logger = colorlog.getLogger(name)

    def lmw(msg, level, *args, **kwargs):
        logger.log(msg=format_message(msg, inspect.currentframe().f_back.f_back.f_code, level), level=level, *args, **kwargs)

    def ttrace(msg, *args, **kwargs):
        lmw(msg, 1, *args, **kwargs)

    def trace(msg, *args, **kwargs):
        lmw(msg, 5, *args, **kwargs)

    def debug(msg, *args, **kwargs):
        lmw(msg, 10, *args, **kwargs)

    def info(msg, *args, **kwargs):
        lmw(msg, 20, *args, **kwargs)

    def warning(msg, *args, **kwargs):
        lmw(msg, 30, *args, **kwargs)

    def error(msg, *args, **kwargs):
        lmw(msg, 40, *args, **kwargs)

    def critical(msg, *args, **kwargs):
        lmw(msg, 50, *args, **kwargs)

    logger.ttrace = ttrace
    logger.trace = trace
    logger.debug = debug
    logger.info = info
    logger.warning = warning
    logger.error = error
    logger.critical = critical
    logger.addHandler(handler)
    logger.setLevel(LOGGING_LEVEL)
    loggers[name] = logger
    return logger


def set_global_logging_level(level: str):
    if level not in LEVELS.values():
        raise ValueError(f"Unknown logger level '{level}'.")
    for _, logger in loggers.items():
        logger.setLevel(level)
