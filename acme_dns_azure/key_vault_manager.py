import base64
from typing import List
from cryptography.hazmat.primitives.serialization import (
    pkcs12,
    Encoding,
    PrivateFormat,
    NoEncryption,
)
from cryptography.hazmat.primitives import serialization
from cryptography import x509

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.keyvault.secrets import SecretClient, KeyVaultSecret
from azure.keyvault.certificates import CertificateClient, KeyVaultCertificate

from acme_dns_azure.exceptions import KeyVaultError
from acme_dns_azure.context import Context
from acme_dns_azure.log import setup_custom_logger

logger = setup_custom_logger(__name__)


class KeyVaultManager:
    def __init__(
        self,
        ctx: Context,
    ) -> None:
        self._config = ctx.config
        self._work_dir = ctx.work_dir + "/"
        self._azure_credentials = ctx.azure_credentials

        self._secret_client = SecretClient(
            vault_url=self._config["key_vault_id"], credential=self._azure_credentials
        )
        self._certificate_client = CertificateClient(
            vault_url=self._config["key_vault_id"], credential=self._azure_credentials
        )

    def secret_exists(self, name: str):
        try:
            self._secret_client.get_secret(name)
            return True
        except ResourceNotFoundError:
            return False

    def certificate_exists(self, name: str):
        try:
            self._certificate_client.get_certificate(name)
            return True
        except ResourceNotFoundError:
            return False

    def set_secret(self, secret_name: str, data: str) -> KeyVaultSecret:
        try:
            logger.info("Setting keyvault secret %s...", secret_name)
            self._secret_client.set_secret(secret_name, data)
        except HttpResponseError as e:
            raise KeyVaultError(
                "Error while creating secret '%s' in key vault '%s': %s"
                % (secret_name, self._config["key_vault_id"], e)
            ) from e

    def import_certificate(
        self, cert_name: str, cert_bytes: bytes
    ) -> KeyVaultCertificate:
        try:
            logger.info("Uploading cert %s...", cert_name)
            self._certificate_client.import_certificate(cert_name, cert_bytes)
        except HttpResponseError as e:
            logger.exception("Failed to upload cert")
            raise KeyVaultError(
                "Error while importing certificate '%s' in key vault '%s': %s"
                % (cert_name, self._config["key_vault_id"], e)
            ) from e

    def get_secret(self, name: str) -> KeyVaultSecret:
        logger.debug(
            "Retrieving secret '%s' from key vault '%s'"
            % (name, self._config["key_vault_id"])
        )
        try:
            return self._secret_client.get_secret(name)
        except ResourceNotFoundError as e:
            raise KeyVaultError(
                "Secet '%s' not found in key vault '%s'"
                % (name, self._config["key_vault_id"])
            ) from e
        except HttpResponseError as e:
            raise KeyVaultError(
                "Error while reading from key vault '%s': %s"
                % (self._config["key_vault_id"], e)
            ) from e

    def get_certificate(self, name: str) -> KeyVaultSecret:
        return self.get_secret(name)

    def extract_pfx_data(self, pfx_data: str):
        key_and_certs: pkcs12.PKCS12KeyAndCertificates = pkcs12.load_pkcs12(
            base64.b64decode(pfx_data), password=None
        )

        private_key = key_and_certs.key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        cert: pkcs12.PKCS12Certificate = key_and_certs.cert
        additional_certs: List[pkcs12.PKCS12Certificate] = (
            key_and_certs.additional_certs
        )

        domains = []
        try:
            san_information: x509.SubjectAlternativeName = (
                cert.certificate.extensions.get_extension_for_oid(
                    x509.ObjectIdentifier("2.5.29.17")
                )
            )
            for general_name in san_information.value:
                domains.append(general_name.value)
        except x509.extensions.ExtensionNotFound:
            logger.info("No 'subjectAltName' extension present for certificate.")

        chain: bytes = b""
        for ca in additional_certs:
            chain = chain + ca.certificate.public_bytes(
                encoding=serialization.Encoding.PEM
            )
        fullchain: bytes = (
            cert.certificate.public_bytes(encoding=serialization.Encoding.PEM) + chain
        )

        return (
            private_key,
            cert.certificate.public_bytes(encoding=serialization.Encoding.PEM),
            chain,
            fullchain,
            domains,
        )

    def generate_pfx(
        self, private_key_path: str, certificate_path: str, chain_file_path: str = None
    ) -> bytes:
        logger.info("Generating pfx certficate...")
        with open(private_key_path, "rb") as private_key:
            private_key_bytes = private_key.read()
        with open(certificate_path, "rb") as certificate:
            certificate_bytes = certificate.read()
        cas = None
        if chain_file_path is not None:
            with open(chain_file_path, "rb") as chain:
                chain_bytes = chain.read()
            if chain_bytes:
                cas = [x509.load_pem_x509_certificate(chain_bytes)]

        return pkcs12.serialize_key_and_certificates(
            name=None,
            key=serialization.load_pem_private_key(private_key_bytes, password=None),
            cert=x509.load_pem_x509_certificate(certificate_bytes),
            cas=cas,
            encryption_algorithm=serialization.NoEncryption(),
        )
