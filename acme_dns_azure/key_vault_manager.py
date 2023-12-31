import base64

from OpenSSL import crypto
from cryptography.hazmat.primitives.serialization import pkcs12
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

    def set_secret(self, secret_name: str, data: str) -> KeyVaultSecret:
        try:
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
            self._certificate_client.import_certificate(cert_name, cert_bytes)
        except HttpResponseError as e:
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
        # https://github.com/Azure/azure-cli/issues/7489
        # For retrieving Certs, one shall also use the secret get API. Cert API does not support getting private key
        return self.get_secret(name)

    def extract_pfx_data(self, pfx_data: str):
        (
            private_key,
            certificate,
            additional_certificates,
        ) = pkcs12.load_key_and_certificates(base64.b64decode(pfx_data), password=None)

        p12 = crypto.PKCS12()
        p12.set_privatekey(crypto.PKey.from_cryptography_key(private_key))
        p12.set_certificate(crypto.X509.from_cryptography(certificate))

        addtional_ca = []
        for cert in additional_certificates:
            addtional_ca.append(crypto.X509.from_cryptography(cert))
        p12.set_ca_certificates(addtional_ca)

        domain = ""
        ext_count = p12.get_certificate().get_extension_count()
        for i in range(0, ext_count):
            ext = p12.get_certificate().get_extension(i)
            if "subjectAltName" in str(ext.get_short_name()):
                san = ext.__str__()
                logger.info(san)
                if "DNS:" in san:
                    domain = san.replace("DNS:", "")

        private_key = crypto.dump_privatekey(crypto.FILETYPE_PEM, p12.get_privatekey())
        cert = crypto.dump_certificate(crypto.FILETYPE_PEM, p12.get_certificate())

        ca_certificates = p12.get_ca_certificates()
        chain: bytes = b""

        for ca in ca_certificates:
            chain = chain + crypto.dump_certificate(crypto.FILETYPE_PEM, ca)
        fullchain: bytes = cert + chain

        return private_key, cert, chain, fullchain, domain

    def generate_pfx(
        self, private_key_path: str, certificate_path: str, chain_file_path: str = None
    ) -> bytes:
        with open(private_key_path, "rb") as private_key:
            private_key_bytes = private_key.read()
        with open(certificate_path, "rb") as certificate:
            certificate_bytes = certificate.read()
        cas = None
        if chain_file_path is not None:
            with open(chain_file_path, "rb") as chain:
                chain_bytes = chain.read()
            cas = [x509.load_pem_x509_certificate(chain_bytes)]

        return pkcs12.serialize_key_and_certificates(
            name=None,
            key=serialization.load_pem_private_key(private_key_bytes, password=None),
            cert=x509.load_pem_x509_certificate(certificate_bytes),
            cas=cas,
            encryption_algorithm=serialization.NoEncryption(),
        )
