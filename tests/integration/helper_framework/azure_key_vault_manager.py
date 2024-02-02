import logging
import time
import ssl

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from azure.core.exceptions import ResourceNotFoundError
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

    def get_cn_and_san_from_certificate(self, name):
        cert = self._cert_client.get_certificate(name)
        certificate = cert.cer
        loaded_cert = x509.load_pem_x509_certificate(certificate, default_backend())

        common_name = loaded_cert.subject.get_attributes_for_oid(
            x509.oid.NameOID.COMMON_NAME
        )

        san = loaded_cert.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        )
        san_dns_names = san.value.get_values_for_type(x509.DNSName)
        return common_name, san_dns_names

    def clean_up_all_resources(self):
        for cert in self._created_certs:
            try:
                logging.info("Deleting certificate %s...", cert.name)
                certificate_poller = self._cert_client.begin_delete_certificate(
                    cert.name
                )
                certificate_poller.wait(timeout=60)
                self._cert_client.purge_deleted_certificate(cert.name)

                for _ in range(60):
                    time.sleep(1)
                    try:
                        cert = self._cert_client.get_deleted_certificate(cert.name)
                    except ResourceNotFoundError:
                        break

            except Exception:
                logging.exception(
                    "Failed to delete certificate %s. Manual deletion required", cert
                )
