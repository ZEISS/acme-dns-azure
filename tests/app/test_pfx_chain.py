from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from acme_dns_azure.key_vault_manager import KeyVaultManager


def issue_certificate(name, key, issuer=None, issuer_key=None, ca=False):
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(timezone.utc)
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer.subject if issuer is not None else subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .sign(issuer_key if issuer_key is not None else key, hashes.SHA256())
    )


@pytest.mark.parametrize("chain_length", [1, 2, 3])
def test_generate_pfx_preserves_all_chain_certificates(tmp_path, chain_length):
    authorities = []
    issuer = issuer_key = None
    for number in range(chain_length):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        issuer = issue_certificate(
            f"test-ca-{number}", key, issuer, issuer_key, ca=True
        )
        issuer_key = key
        authorities.append(issuer)
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf = issue_certificate("test-leaf", leaf_key, issuer, issuer_key)
    encoding = serialization.Encoding.PEM
    key_path = tmp_path / "key.pem"
    cert_path = tmp_path / "cert.pem"
    chain_path = tmp_path / "chain.pem"
    key_path.write_bytes(
        leaf_key.private_bytes(
            encoding, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
    )
    cert_path.write_bytes(leaf.public_bytes(encoding))
    chain_path.write_bytes(
        b"".join(cert.public_bytes(encoding) for cert in reversed(authorities))
    )
    manager = KeyVaultManager.__new__(KeyVaultManager)

    result = pkcs12.load_pkcs12(
        manager.generate_pfx(str(key_path), str(cert_path), str(chain_path)), None
    )

    assert result.cert.certificate == leaf
    assert (
        result.key.public_key().public_numbers()
        == leaf_key.public_key().public_numbers()
    )
    assert len(result.additional_certs) == chain_length
    assert {
        cert.certificate.fingerprint(hashes.SHA256())
        for cert in result.additional_certs
    } == {cert.fingerprint(hashes.SHA256()) for cert in authorities}
