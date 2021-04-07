import logging
import sys

from pythonjsonlogger import jsonlogger


class StackdriverJsonFormatter(jsonlogger.JsonFormatter):

    def process_log_record(self, log_record):
        log_record['severity'] = log_record['levelname']
        return super().process_log_record(log_record)


class MinorStreamHandler(logging.StreamHandler):

    def __init__(self, stream=sys.stdout, levelno=logging.WARNING):
        super().__init__(stream)
        self.addFilter(lambda record: record.levelno <= levelno)
