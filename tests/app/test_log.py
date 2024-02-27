import os
import logging

from unittest import mock

from acme_dns_azure.log import setup_custom_logger


def test_default_logger():
    logger: logging.Logger = setup_custom_logger("test")
    assert logger.level == logging.INFO


def test_custom_logger():
    with mock.patch.dict(os.environ, {"ACME_DNS_AZURE_LOG_LEVEL": "WARN"}):
        logger: logging.Logger = setup_custom_logger("test")
        assert logger.level == logging.WARN


def test_default_for_incorrect_custom_logger():
    with mock.patch.dict(os.environ, {"ACME_DNS_AZURE_LOG_LEVEL": "RANDOM"}):
        logger: logging.Logger = setup_custom_logger("test")
        assert logger.level == logging.INFO
