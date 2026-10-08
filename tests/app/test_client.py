from unittest.mock import Mock, patch

from acme_dns_azure.client import AcmeDnsAzureClient
from acme_dns_azure.data import CertbotResult, RotationResult


def _result(result: CertbotResult) -> RotationResult:
    return RotationResult(certificate=None, result=result)


def test_issue_certificates_logs_renewed_and_failed_counts():
    client = AcmeDnsAzureClient.__new__(AcmeDnsAzureClient)
    client.ctx = Mock(work_dir="test-work-dir")
    client.certbot = Mock()
    client.certbot.renew_certificates.return_value = [
        _result(CertbotResult.RENEWED),
        _result(CertbotResult.CREATED),
        _result(CertbotResult.FAILED),
    ]

    with patch("acme_dns_azure.client.logger") as logger:
        results = client.issue_certificates()

    assert len(results) == 3
    logger.info.assert_any_call(
        "Certificate renewal finished: %d renewed, %d failed", 2, 1
    )


def test_failed_certificate_results_set_failure_exit_condition():
    from acme_dns_azure.client import _has_failed_certificates

    assert _has_failed_certificates([_result(CertbotResult.RENEWED)]) is False
    assert _has_failed_certificates([_result(CertbotResult.FAILED)]) is True
