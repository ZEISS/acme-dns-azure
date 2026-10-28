import base64
import io
import os
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from acme_dns_azure.certbot_manager import CertbotManager
from acme_dns_azure.context import Context

ACCOUNT_FILES = {
    "server/directory/account/regr.json": b'{"uri": "test-account"}',
    "server/directory/account/meta.json": b'{"creation_host": "test-host"}',
}


def make_manager(tmp_path, existing=True):
    ctx = Context()
    ctx.work_dir = str(tmp_path)
    ctx.config = {"keyvault_account_secret_name": "test-account", "certificates": []}
    ctx.keyvault = Mock()
    ctx.keyvault.secret_exists.return_value = existing
    if existing:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, content in ACCOUNT_FILES.items():
                archive.writestr(name, content)
        ctx.keyvault.get_secret.return_value = SimpleNamespace(
            value=base64.b64encode(buffer.getvalue()).decode()
        )
    with patch.object(CertbotManager, "_create_certbot_init_files"):
        return CertbotManager(ctx)


@pytest.mark.parametrize("change_timestamps", [False, True])
def test_unchanged_restored_account_is_not_uploaded(tmp_path, change_timestamps):
    manager = make_manager(tmp_path)
    if change_timestamps:
        for name in ACCOUNT_FILES:
            os.utime(tmp_path / "config/accounts" / name, (1600000000, 1600000000))

    assert manager.renew_certificates() == []

    manager.ctx.keyvault.set_secret.assert_not_called()


@pytest.mark.parametrize("change", ["modify", "add", "remove"])
def test_changed_account_is_uploaded(tmp_path, change):
    manager = make_manager(tmp_path)
    root = tmp_path / "config/accounts"
    expected = ACCOUNT_FILES.copy()
    name = next(iter(expected))
    if change == "modify":
        previous_stat = (root / name).stat()
        expected[name] = b'{"uri": "next-account"}'
        (root / name).write_bytes(expected[name])
        os.utime(root / name, ns=(previous_stat.st_atime_ns, previous_stat.st_mtime_ns))
    elif change == "add":
        expected["new-account.json"] = b"{}"
        (root / "new-account.json").write_bytes(b"{}")
    else:
        del expected[name]
        (root / name).unlink()

    manager.renew_certificates()

    manager.ctx.keyvault.set_secret.assert_called_once()
    secret_name, encoded = manager.ctx.keyvault.set_secret.call_args.args
    assert secret_name == "test-account"
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded))) as archive:
        assert {name: archive.read(name) for name in archive.namelist()} == expected


def test_new_account_is_uploaded_only_once(tmp_path):
    manager = make_manager(tmp_path, existing=False)
    (tmp_path / "config/accounts/regr.json").write_bytes(b"{}")

    manager.renew_certificates()
    manager.renew_certificates()

    manager.ctx.keyvault.set_secret.assert_called_once()


def test_failed_upload_is_retried(tmp_path):
    manager = make_manager(tmp_path)
    (tmp_path / "config/accounts/new-account.json").write_bytes(b"{}")
    manager.ctx.keyvault.set_secret.side_effect = [RuntimeError("test failure"), None]

    manager.renew_certificates()
    manager.renew_certificates()
    manager.renew_certificates()

    assert manager.ctx.keyvault.set_secret.call_count == 2
