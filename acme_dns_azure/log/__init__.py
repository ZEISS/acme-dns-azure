import logging
import os


def setup_custom_logger(name):
    """Setting up custom logger. Using INFO level as default when Log Level is not set via environment variable.

    Environment variables:

    ACME_DNS_AZURE_LOG_LEVEL -- Log level for all classes.

    Allowed values:

        "DEBUG"
        "INFO"
        "WARN"
        "WARNING"
        "ERROR"
        "CRITICAL"
        "FATAL"
    """
    log_level = logging.INFO
    custom_level = os.environ.get("ACME_DNS_AZURE_LOG_LEVEL", None)
    if custom_level and custom_level in [
        "DEBUG",
        "INFO",
        "WARN",
        "WARNING",
        "ERROR",
        "CRITICAL",
        "FATAL",
    ]:
        log_level = logging.getLevelName(custom_level)
        logging.info("Setting defined loglevel '%s'.", log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(log_level)
    logger.addHandler(handler)
    return logger
