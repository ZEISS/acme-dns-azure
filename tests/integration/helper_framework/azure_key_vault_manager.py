import logging
import time

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient, KeyVaultSecret
from azure.keyvault.certificates import (
    CertificatePolicy,
    CertificateClient,
    KeyVaultCertificate,
)


class AzureKeyVaultManager:
    def __init__(self, keyvault_uri):
        self._cert_client = CertificateClient(
            vault_url=keyvault_uri, credential=DefaultAzureCredential()
        )
        self._created_certs: [KeyVaultCertificate] = []

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
        cert = certificate.result(timeout=10)
        self._created_certs.append(cert)

    def list_properties_of_certificate_versions(self, name):
        return self._cert_client.list_properties_of_certificate_versions(name)

    def clean_up_all_resources(self):
        for cert in self._created_certs:
            try:
                logging.info("Deleting certificate %s...", cert.name)
                certificate_poller = self._cert_client.begin_delete_certificate(
                    cert.name
                )
                certificate_poller.wait(timeout=300)
                # self._wait_to_finsih(certificate_poller, iterations=30, seconds=1)
                self._cert_client.purge_deleted_certificate(cert.name)
            except Exception:
                logging.exception(
                    "Failed to delete certificate %s. Manual deletion required", cert
                )

    def _wait_to_finsih(self, poller, iterations=10, seconds=1):
        counter = 0
        while counter < iterations:
            if poller.done():
                return True
            time.sleep(seconds)
            counter = +1
        raise Exception("Operation not finished")
