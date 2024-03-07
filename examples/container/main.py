import os
import logging
from typing import List
from acme_dns_azure.data import (
    RotationResult,
    CertbotResult,
)
from acme_dns_azure.client import AcmeDnsAzureClient


if __name__ == "__main__":

    acme_dns_config_env_name = "ACME_DNS_CONFIG"
    assert acme_dns_config_env_name in os.environ

    try:
        client = AcmeDnsAzureClient(config_env_var=acme_dns_config_env_name)
        results: List[RotationResult] = client.issue_certificates()
        for rotation in results:
            if rotation.result == CertbotResult.FAILED:
                logging.exception("Failed to rotate certificate %s.", rotation)
            if rotation.result == CertbotResult.SKIPPED:
                logging.warning("Skipped to rotate certificate %s.", rotation)
            else:
                logging.info(rotation)

    except Exception:
        logging.exception("Failed to rotate certificates")
