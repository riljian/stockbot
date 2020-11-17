from pythonjsonlogger import jsonlogger


class StackdriverJsonFormatter(jsonlogger.JsonFormatter):

    def process_log_record(self, log_record):
        log_record['severity'] = log_record['levelname']
        return super().process_log_record(log_record)
