from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

from acme_dns_azure.exceptions import KeyVaultError
from acme_dns_azure.context import Context
from acme_dns_azure.log import setup_custom_logger
from acme_dns_azure.os_manager import FileManager

logger = setup_custom_logger(__name__)

class KeyVaultManager():
    def __init__(self, ctx: Context, ) -> None:
        self._config = ctx.config
        self._work_dir = ctx.work_dir + '/'

        self._secret_client = SecretClient(vault_url = self._config['key_vault_id'], credential = DefaultAzureCredential())

    def get_secret(self, name: str):
        logger.debug("Retrieving secret '%s' from key vault '%s'" % (name, self._config['key_vault_id']))
        try:
            return self._secret_client.get_secret(name).value
        except ResourceNotFoundError:
            raise KeyVaultError("Secet '%s' not found in key vault '%s'" % (name, self._config['key_vault_id']))
        except HttpResponseError as e:
            raise KeyVaultError("Error while reading from key vault '%s': %s" % (self._config['key_vault_id'], e))
