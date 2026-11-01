import time
from datetime import datetime, timedelta, timezone

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.certificates import (
    CertificateClient,
    CertificatePolicy,
    KeyVaultCertificate,
)
from azure.keyvault.secrets import SecretClient
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID

from acme_dns_azure.log import setup_custom_logger

logger = setup_custom_logger(__name__)


class CertificateAuthority:
    def __init__(self):
        self._private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=4096
        )
        subject = x509.Name.from_rfc4514_string("CN=acme-dns-azure integration CA")
        now = datetime.now(timezone.utc)
        self._certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(self._private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .sign(self._private_key, hashes.SHA256())
        )

    def issue_certificate(
        self,
        name: str,
        subject: str,
        san_dns_names: list[str],
        validity_in_months: int,
        key_size: int,
    ) -> bytes:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        now = datetime.now(timezone.utc)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(x509.Name.from_rfc4514_string(subject))
            .issuer_name(self._certificate.subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=30 * validity_in_months))
            .add_extension(
                x509.SubjectAlternativeName(
                    [x509.DNSName(domain) for domain in san_dns_names]
                ),
                critical=False,
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None), critical=True
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
            .sign(self._private_key, hashes.SHA256())
        )
        return pkcs12.serialize_key_and_certificates(
            name=name.encode(),
            key=private_key,
            cert=certificate,
            cas=[self._certificate],
            encryption_algorithm=serialization.NoEncryption(),
        )


class AzureKeyVaultManager:
    def __init__(self, keyvault_uri, certificate_authority: CertificateAuthority):
        self._cert_client = CertificateClient(
            vault_url=keyvault_uri, credential=DefaultAzureCredential()
        )
        self._secret_client = SecretClient(
            vault_url=keyvault_uri, credential=DefaultAzureCredential()
        )
        self._created_certs: list[KeyVaultCertificate] = []
        self._expected_secrets: list[str] = [
            "acme-account-acme-staging-v02-api-letsencrypt-org"
        ]
        self._certificate_authority = certificate_authority

    def create_certificate(
        self,
        name,
        subject,
        san_dns_names,
        validity_in_months: int,
        key_size=4096,
        key_type="RSA",
    ):
        if key_type != "RSA":
            raise ValueError("Integration test certificates only support RSA keys")
        certificate_bytes = self._certificate_authority.issue_certificate(
            name=name,
            subject=subject,
            san_dns_names=san_dns_names,
            validity_in_months=validity_in_months,
            key_size=key_size,
        )
        certificate = self._cert_client.import_certificate(
            certificate_name=name, certificate_bytes=certificate_bytes
        )
        self._created_certs.append(certificate)

    def create_self_signed_certificate(
        self,
        name,
        subject,
        san_dns_names,
        validity_in_months: int,
        key_size=4096,
        key_type="RSA",
    ):
        policy = CertificatePolicy(
            issuer_name="self",
            subject=subject,
            san_dns_names=san_dns_names,
            key_size=key_size,
            key_type=key_type,
            validity_in_months=validity_in_months,
        )
        certificate = self._cert_client.begin_create_certificate(
            certificate_name=name, policy=policy
        )
        certificate.wait(timeout=30)
        self._created_certs.append(certificate.result())

    def list_properties_of_certificate_versions(self, name):
        return self._cert_client.list_properties_of_certificate_versions(name)

    def get_cn_and_san_from_certificate(self, name):
        policy = self._cert_client.get_certificate_policy(name)
        return policy.subject, policy.san_dns_names

    def _wait_until_secret_is_deleted(self, secret_name: str):
        t_end = time.time() + 60
        self._secret_client.begin_delete_secret(secret_name).wait()
        while time.time() < t_end:
            try:
                self._secret_client.get_secret(secret_name)
                time.sleep(1)
            except Exception:
                pass
        t_end = time.time() + 60
        self._secret_client.purge_deleted_secret(secret_name)
        while time.time() < t_end:
            try:
                self._secret_client.get_deleted_secret(secret_name)
                time.sleep(1)
            except Exception:
                pass
        return

    def _wait_until_cert_is_deleted(self, cert_name: str):
        t_end = time.time() + 60
        self._cert_client.begin_delete_certificate(cert_name).wait()
        while time.time() < t_end:
            try:
                self._cert_client.get_certificate(cert_name)
                time.sleep(1)
            except Exception:
                pass
        self._cert_client.purge_deleted_certificate(cert_name)
        t_end = time.time() + 60
        while time.time() < t_end:
            try:
                self._cert_client.get_deleted_certificate(cert_name)
                time.sleep(1)
            except Exception:
                pass
        return

    def clean_up_all_resources(self):
        for cert in self._created_certs:
            self._wait_until_cert_is_deleted(cert.name)
        if not self._created_certs:
            logger.debug("Cleaning up all certificates stored in key vault.")
            certs = self._cert_client.list_properties_of_certificates()
            for cert in certs:
                self._wait_until_cert_is_deleted(cert.name)
        secrets = self._secret_client.list_properties_of_secrets()
        for secret in secrets:
            if secret.name in self._expected_secrets:
                self._wait_until_secret_is_deleted(secret.name)
