import sys
import tempfile

from azure.identity import DefaultAzureCredential

import acme_dns_azure.config as config
from acme_dns_azure.context import Context
from acme_dns_azure.log import setup_custom_logger
from acme_dns_azure.exceptions import ConfigurationError, KeyVaultError
from acme_dns_azure.certbot_manager import CertbotManager
from acme_dns_azure.key_vault_manager import KeyVaultManager

logger = setup_custom_logger(__name__)


class AcmeDnsAzureClient:
    def __init__(
        self, config_yaml: str = "", config_env_var: str = "", config_file: str = ""
    ) -> None:
        self.ctx = Context()
        self._work_dir = tempfile.TemporaryDirectory(prefix="acme_dns_azure")
        logger.info(
            "Setting working directory for certicate renewal: %s", self._work_dir
        )
        self.ctx.work_dir = self._work_dir.name

        if config_yaml != "":
            self.ctx.config = config.load(config_yaml)
        elif config_env_var != "":
            self.ctx.config = config.load_from_base64_env_var(config_env_var)
        elif config_file != "":
            self.ctx.config = config.load_from_file(config_file)
        else:
            raise ConfigurationError("No configuration source defined")

        self.ctx.azure_credentials = DefaultAzureCredential()
        self.ctx.keyvault = KeyVaultManager(self.ctx)
        self.certbot = CertbotManager(self.ctx)

    def __del__(self):
        logger.info("Cleaning up directory %s", self.ctx.work_dir)

    def issue_certificates(self):
        logger.info("Issuing certificates")
        self.certbot.renew_certificates()


if __name__ == "__main__":
    try:
        client = AcmeDnsAzureClient(config_file="config.yaml")
    except ConfigurationError as e:
        logger.error(e)
        sys.exit(1)
    except KeyVaultError as e:
        logger.error(e)
        sys.exit(1)
    except Exception:
        logger.exception("Unable to instanciate AcmeDnsAzureClient")
        sys.exit(1)

    client.issue_certificates()
