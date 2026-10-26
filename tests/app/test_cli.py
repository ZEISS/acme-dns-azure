import sys
from importlib.metadata import distribution
from unittest.mock import Mock

import pytest

from acme_dns_azure import client
from acme_dns_azure.data import CertbotResult, RotationResult


def _console_main():
    entry_point = next(
        entry
        for entry in distribution("acme-dns-azure").entry_points
        if entry.group == "console_scripts" and entry.name == "acme-dns-azure"
    )
    return entry_point.load()


def test_installed_console_entry_point_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["acme-dns-azure", "--help"])

    with pytest.raises(SystemExit) as error:
        _console_main()()

    assert error.value.code == 0
    output = capsys.readouterr().out
    assert "--config-file-path" in output
    assert "--config-env-var" in output


@pytest.mark.parametrize(
    ("result", "exit_code"),
    [(CertbotResult.RENEWED, None), (CertbotResult.FAILED, 2)],
)
def test_installed_console_entry_point_rotation(monkeypatch, result, exit_code):
    monkeypatch.setattr(
        sys, "argv", ["acme-dns-azure", "--config-env-var", "TEST_CONFIG"]
    )
    instance = Mock()
    instance.issue_certificates.return_value = [
        RotationResult(certificate=None, result=result)
    ]
    factory = Mock(return_value=instance)
    monkeypatch.setattr(client, "AcmeDnsAzureClient", factory)

    if exit_code is None:
        assert _console_main()() is None
    else:
        with pytest.raises(SystemExit) as error:
            _console_main()()
        assert error.value.code == exit_code

    factory.assert_called_once_with(config_file=None, config_env_var="TEST_CONFIG")
    instance.issue_certificates.assert_called_once_with()


@pytest.mark.parametrize(
    "error_type", [client.ConfigurationError, client.KeyVaultError, RuntimeError]
)
def test_installed_console_entry_point_initialization_error(monkeypatch, error_type):
    monkeypatch.setattr(sys, "argv", ["acme-dns-azure"])
    factory = Mock(side_effect=error_type("Initialization failed"))
    monkeypatch.setattr(client, "AcmeDnsAzureClient", factory)

    with pytest.raises(SystemExit) as error:
        _console_main()()

    assert error.value.code == 1
