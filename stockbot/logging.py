import logging
import sys

from pythonjsonlogger import jsonlogger


class StackdriverJsonFormatter(jsonlogger.JsonFormatter):

    def process_log_record(self, log_record):
        log_record['severity'] = log_record['levelname']
        return super().process_log_record(log_record)


class MaxLevelFilter:

    def __init__(self, max_level):
        self._max_level = max_level

    def filter(self, log_record):
        return log_record.levelno <= self._max_level


class MinorStreamHandler(logging.StreamHandler):

    def __init__(self, stream=sys.stdout, levelno=logging.WARNING):
        super().__init__(stream)
        self.addFilter(MaxLevelFilter(levelno))
