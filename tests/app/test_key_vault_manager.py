import os
import base64
from datetime import datetime, timedelta, timezone

from mock import patch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization.pkcs12 import PKCS12KeyAndCertificates
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.x509 import load_pem_x509_certificate, Certificate

from acme_dns_azure.key_vault_manager import KeyVaultManager
import acme_dns_azure.config as config


path_to_current_file = os.path.realpath(__file__)
current_directory = os.path.split(path_to_current_file)[0]
resources_dir = current_directory + "/resources/"


def keyvault_manager_init(self, working_dir) -> None:
    self._config = config.load_from_file(resources_dir + "config/accepted.yaml")
    self._azure_credentials = "..."
    self._work_dir = working_dir


def create_pkc_s12(private_key_bytes, certificate_bytes, name="test"):
    return pkcs12.serialize_key_and_certificates(
        name=name.encode(),
        key=serialization.load_pem_private_key(private_key_bytes, password=None),
        cert=x509.load_pem_x509_certificate(certificate_bytes),
        cas=None,
        encryption_algorithm=serialization.NoEncryption(),
    )


def create_x509_certificate(domain: str):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "DE"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Province"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "loc"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "org"),
            x509.NameAttribute(NameOID.COMMON_NAME, "company"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(30))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(domain)]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )
    certificate_bytes = cert.public_bytes(encoding=serialization.Encoding.PEM)
    return private_bytes, certificate_bytes


@patch.object(KeyVaultManager, "__init__", keyvault_manager_init)
def test_key_and_certs_extraced_from_pfx(working_dir):
    gen_domain = "test.net"
    gen_private_bytes, gen_certificate_bytes = create_x509_certificate(
        domain=gen_domain
    )
    pfx = create_pkc_s12(gen_private_bytes, gen_certificate_bytes, "test")

    key_vault_manager = KeyVaultManager(working_dir)
    private_key, cert, chain, fullchain, domain = key_vault_manager.extract_pfx_data(
        (base64.b64encode(pfx)).decode("ascii")
    )

    assert isinstance(
        serialization.load_pem_private_key(private_key, password=None),
        rsa.RSAPrivateKey,
    )
    assert isinstance(load_pem_x509_certificate(cert), Certificate)
    assert chain == b""
    assert isinstance(load_pem_x509_certificate(fullchain), Certificate)
    assert domain == gen_domain


@patch.object(KeyVaultManager, "__init__", keyvault_manager_init)
def test_pfx_created(
    working_dir, tmp_priv_key_path, tmp_cert_path, cleanup_tmp_privkey_and_cert
):
    gen_domain = "test.net"
    gen_private_bytes, gen_certificate_bytes = create_x509_certificate(
        domain=gen_domain
    )
    gen_priv_dir = tmp_priv_key_path
    gen_cert_dir = tmp_cert_path

    with open(gen_priv_dir, "wb") as file:
        file.write(gen_private_bytes)
    with open(gen_cert_dir, "wb") as file:
        file.write(gen_certificate_bytes)

    key_vault_manager = KeyVaultManager(working_dir)
    pfx_formatted = key_vault_manager.generate_pfx(
        private_key_path=gen_priv_dir, certificate_path=gen_cert_dir
    )

    backend = default_backend()
    pfx_from_module = backend.load_pkcs12(pfx_formatted, None)
    assert isinstance(pfx_from_module, PKCS12KeyAndCertificates)
