import time
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.certificates import (
    CertificatePolicy,
    CertificateClient,
    KeyVaultCertificate,
)
from azure.keyvault.secrets import SecretClient
from acme_dns_azure.log import setup_custom_logger

logger = setup_custom_logger(__name__)


class AzureKeyVaultManager:
    def __init__(self, keyvault_uri):
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

    def create_certificate(
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
        cert = certificate.result()
        self._created_certs.append(cert)

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
