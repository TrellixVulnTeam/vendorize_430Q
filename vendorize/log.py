import logging
import sys


class ColoredLogFormatter(logging.Formatter):
    colors = {
        'DEBUG': '\033[0;34m',      # Green
        'INFO': '\033[0;32m',      # Green
        'WARNING': '\033[1;33m',   # Yellow
        'ERROR': '\033[0;31m',     # Dark red
        'CRITICAL': '\033[1;31m',  # Light red
    }

    def format(self, record):
        message = super().format(record)
        color = self.colors.get(record.levelname)
        if color:
            return '{color}{message}\033[0m'.format(
                color=color, message=message)
        return message


def get_logger(name: str):
    logger = logging.getLogger(name)
    formatter = ColoredLogFormatter()
    for stream in [sys.stdout]:
        handler = logging.StreamHandler(stream=stream)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
