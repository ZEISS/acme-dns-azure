import base64
import gc
import io
import runpy
import sys
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from acme_dns_azure import client as client_module
from acme_dns_azure.dns_validation import DNSChallenge
from acme_dns_azure.data import CertbotResult

DIRECTORIES = (
    "config",
    "work",
    "logs",
    "config/live",
    "config/accounts",
    "config/archive",
    "config/renewal",
)
CONFIG_FILE = Path(__file__).parent / "resources/config/accepted.yaml"


@pytest.fixture
def keyvault(monkeypatch):
    vault = Mock()
    vault.secret_exists.return_value = False
    monkeypatch.setattr(client_module, "DefaultAzureCredential", Mock())
    monkeypatch.setattr(client_module, "KeyVaultManager", lambda ctx: vault)
    monkeypatch.setattr(
        DNSChallenge,
        "validate",
        lambda self, name: (
            (
                "my-dev.domain.com"
                if name.endswith(("zyx.example.org", "abc.example.org"))
                else "example.org"
            ),
            None,
        ),
    )
    return vault


@pytest.mark.parametrize("path_object", [False, True])
def test_persistent_directory_is_created_and_retained(
    tmp_path, monkeypatch, keyvault, path_object
):
    monkeypatch.chdir(tmp_path)
    relative = Path("persistent ü") / "nested"
    directory = tmp_path / relative
    client = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE),
        work_dir=relative if path_object else str(relative),
    )

    assert client.ctx.work_dir == str(directory)
    for name in DIRECTORIES:
        assert (directory / name).is_dir()
    for name in ("certbot.ini", "certbot_dns_azure.ini"):
        assert (directory / name).is_file()
    assert f"config-dir = {directory}/config" in (directory / "certbot.ini").read_text(
        encoding="utf8"
    )

    del client
    gc.collect()
    assert directory.is_dir()
    assert (directory / "certbot.ini").is_file()


def test_existing_files_and_accounts_are_not_overwritten(tmp_path, keyvault):
    account = tmp_path / "config/accounts/existing/private_key.json"
    account.parent.mkdir(parents=True)
    files = {
        tmp_path / "certbot.ini": b"custom certbot settings\n",
        tmp_path / "certbot_dns_azure.ini": b"custom credentials\n",
        tmp_path / "notes.txt": b"caller-owned file\n",
        account: b"local account state\n",
    }
    for path, data in files.items():
        path.write_bytes(data)
    keyvault.secret_exists.return_value = True

    client = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE), work_dir=tmp_path
    )

    keyvault.secret_exists.assert_not_called()
    keyvault.get_secret.assert_not_called()
    for name in DIRECTORIES:
        assert (tmp_path / name).is_dir()
    del client
    gc.collect()
    for path, data in files.items():
        assert path.read_bytes() == data


def test_repeated_initialization_preserves_changes(tmp_path, keyvault):
    first = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE), work_dir=tmp_path
    )
    custom = tmp_path / "certbot.ini"
    custom.write_text("custom settings\n", encoding="utf8")
    (tmp_path / "certbot_dns_azure.ini").unlink()

    second = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE), work_dir=tmp_path
    )

    assert custom.read_text(encoding="utf8") == "custom settings\n"
    assert (tmp_path / "certbot_dns_azure.ini").is_file()
    assert first.ctx.work_dir == second.ctx.work_dir


def test_empty_account_directory_is_restored_once(tmp_path, keyvault):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("example/directory/account/regr.json", "account state")
    keyvault.secret_exists.return_value = True
    keyvault.get_secret.return_value.value = base64.b64encode(archive.getvalue())

    first = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE), work_dir=tmp_path
    )

    assert (
        tmp_path / "config/accounts/example/directory/account/regr.json"
    ).read_text() == "account state"
    keyvault.get_secret.assert_called_once()
    assert not (tmp_path / "accounts.zip").exists()
    keyvault.reset_mock()

    second = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE), work_dir=tmp_path
    )

    keyvault.secret_exists.assert_not_called()
    assert first.ctx.work_dir == second.ctx.work_dir


def test_default_directory_is_temporary(keyvault):
    client = client_module.AcmeDnsAzureClient(config_file=str(CONFIG_FILE))
    directory = Path(client.ctx.work_dir)
    assert directory.is_dir()

    del client
    gc.collect()

    assert not directory.exists()


def test_file_cannot_be_used_as_directory(tmp_path, keyvault):
    target = tmp_path / "file"
    target.write_text("preserve me", encoding="utf8")

    with pytest.raises(FileExistsError):
        client_module.AcmeDnsAzureClient(config_file=str(CONFIG_FILE), work_dir=target)

    assert target.read_text(encoding="utf8") == "preserve me"


def test_existing_certificate_lineage_is_preserved(tmp_path, keyvault):
    client = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE), work_dir=tmp_path
    )
    live = tmp_path / "config/live/example"
    archive = tmp_path / "config/archive/example"
    live.mkdir()
    archive.mkdir()
    files = {tmp_path / "config/renewal/example.conf": b"custom renewal\n"}
    for name in ("cert", "privkey", "chain", "fullchain"):
        files[live / f"{name}.pem"] = f"local {name}\n".encode()
        files[archive / f"{name}1.pem"] = f"old {name}\n".encode()
    for path, data in files.items():
        path.write_bytes(data)

    client.certbot._create_certificate_files(
        "example", "remote cert", "remote chain", "remote fullchain", "remote key"
    )

    for path, data in files.items():
        assert path.read_bytes() == data


def test_missing_certificate_parts_are_created(tmp_path, keyvault, monkeypatch):
    client = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE), work_dir=tmp_path
    )
    live = tmp_path / "config/live/example"
    live.mkdir()
    existing = live / "cert.pem"
    existing.write_bytes(b"existing certificate")
    create_symlink = Mock()
    monkeypatch.setattr(client.certbot._os_manager, "create_symlink", create_symlink)

    client.certbot._create_certificate_files(
        "example", "remote cert", "remote chain", "remote fullchain", "remote key"
    )

    assert existing.read_bytes() == b"existing certificate"
    assert (tmp_path / "config/renewal/example.conf").is_file()
    for name, value in (
        ("cert", "remote cert"),
        ("privkey", "remote key"),
        ("chain", "remote chain"),
        ("fullchain", "remote fullchain"),
    ):
        assert (
            tmp_path / f"config/archive/example/{name}1.pem"
        ).read_text().strip() == value
    assert create_symlink.call_count == 3
    for name in ("privkey", "chain", "fullchain"):
        create_symlink.assert_any_call(
            src=f"../../archive/example/{name}1.pem",
            dest=f"{tmp_path}/config/live/example/{name}.pem",
        )


def test_renewal_reuses_local_certificate_files(tmp_path, keyvault, monkeypatch):
    client = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE), work_dir=tmp_path
    )
    client.ctx.config["certificates"] = client.ctx.config["certificates"][:1]
    name = client.ctx.config["certificates"][0]["name"]
    keyvault.certificate_exists.side_effect = AssertionError("Use the local lineage")
    live = tmp_path / f"config/live/{name}"
    live.mkdir()
    files = {tmp_path / f"config/renewal/{name}.conf": b"local renewal"}
    for part in ("cert", "privkey", "chain", "fullchain"):
        files[live / f"{part}.pem"] = f"local {part}".encode()
    for path, data in files.items():
        path.write_bytes(data)
    renew = Mock(return_value=CertbotResult.STILL_VALID)
    monkeypatch.setattr(client.certbot, "_create_or_renew_certificate", renew)

    results = client.issue_certificates()

    assert len(results) == 1
    assert results[0].result == CertbotResult.STILL_VALID
    renew.assert_called_once_with(
        cert_name=name, domains=["xyz.example.org", "zyx.example.org"]
    )
    keyvault.import_certificate.assert_not_called()
    keyvault.certificate_exists.assert_not_called()
    keyvault.get_certificate.assert_not_called()
    for path, data in files.items():
        assert path.read_bytes() == data


def test_missing_lineage_can_be_restored_from_keyvault(tmp_path, keyvault, monkeypatch):
    client = client_module.AcmeDnsAzureClient(
        config_file=str(CONFIG_FILE), work_dir=tmp_path
    )
    client.ctx.config["certificates"] = client.ctx.config["certificates"][:1]
    name = client.ctx.config["certificates"][0]["name"]
    keyvault.certificate_exists.return_value = True
    keyvault.get_certificate.return_value.value = "synthetic PFX"
    keyvault.extract_pfx_data.return_value = (
        b"remote key",
        b"remote cert",
        b"remote chain",
        b"remote fullchain",
        ["xyz.example.org", "zyx.example.org"],
    )
    monkeypatch.setattr(client.certbot._os_manager, "create_symlink", Mock())
    monkeypatch.setattr(
        client.certbot,
        "_create_or_renew_certificate",
        Mock(return_value=CertbotResult.STILL_VALID),
    )

    results = client.issue_certificates()

    assert results[0].result == CertbotResult.STILL_VALID
    keyvault.get_certificate.assert_called_once_with(name=name)
    assert (tmp_path / f"config/renewal/{name}.conf").is_file()
    assert (
        tmp_path / f"config/archive/{name}/cert1.pem"
    ).read_text().strip() == "remote cert"


def test_module_command_accepts_persistent_directory(tmp_path, keyvault, monkeypatch):
    import acme_dns_azure.certbot_manager
    import acme_dns_azure.key_vault_manager
    import azure.identity

    monkeypatch.setattr(azure.identity, "DefaultAzureCredential", Mock())
    monkeypatch.setattr(
        acme_dns_azure.key_vault_manager, "KeyVaultManager", Mock(return_value=keyvault)
    )
    manager = Mock()
    manager.return_value.renew_certificates.return_value = []
    monkeypatch.setattr(acme_dns_azure.certbot_manager, "CertbotManager", manager)
    directory = tmp_path / "cli-state"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "acme-dns-azure",
            "--config-file-path",
            str(CONFIG_FILE),
            "--work-dir",
            str(directory),
        ],
    )

    runpy.run_path(client_module.__file__, run_name="__main__")

    assert manager.call_args.args[0].work_dir == str(directory)
    assert directory.is_dir()
