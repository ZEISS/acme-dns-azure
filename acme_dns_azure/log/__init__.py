import logging
import os

def setup_custom_logger(name):
    log_level = os.environ.get('ACME_DNS_AZURE_LOG_LEVEL', logging.INFO)
    if log_level not in ['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'CRITICAL', 'FATAL']:
        logging.warning("Unknown log level '%s' - using INFO instead." % log_level)
        log_level = logging.INFO

    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.addHandler(handler)
    return logger
