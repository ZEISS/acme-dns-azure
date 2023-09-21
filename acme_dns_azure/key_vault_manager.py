from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.keyvault.secrets import SecretClient
from azure.keyvault.certificates import CertificateClient, KeyVaultCertificate

from acme_dns_azure.exceptions import KeyVaultError
from acme_dns_azure.context import Context
from acme_dns_azure.log import setup_custom_logger

logger = setup_custom_logger(__name__)

class KeyVaultManager():
    def __init__(self, ctx: Context, ) -> None:
        self._config = ctx.config
        self._work_dir = ctx.work_dir + '/'
        self._azure_credentials = ctx.azure_credentials

        self._secret_client = SecretClient(vault_url = self._config['key_vault_id'], credential = self._azure_credentials)
        self._certificate_client = CertificateClient(vault_url = self._config['key_vault_id'], credential = self._azure_credentials)

    def get_secret(self, name: str):
        logger.debug("Retrieving secret '%s' from key vault '%s'" % (name, self._config['key_vault_id']))
        try:
            return self._secret_client.get_secret(name)
        except ResourceNotFoundError:
            raise KeyVaultError("Secet '%s' not found in key vault '%s'" % (name, self._config['key_vault_id']))
        except HttpResponseError as e:
            raise KeyVaultError("Error while reading from key vault '%s': %s" % (self._config['key_vault_id'], e))

    def get_certificate(self, name: str):
        logger.debug("Retrieving certificate '%s' from key vault '%s'" % (name, self._config['key_vault_id']))
        try:
            return self._certificate_client.get_certificate(name)
        except ResourceNotFoundError:
            raise KeyVaultError("Secet '%s' not found in key vault '%s'" % (name, self._config['key_vault_id']))
        except HttpResponseError as e:
            raise KeyVaultError("Error while reading from key vault '%s': %s" % (self._config['key_vault_id'], e))
