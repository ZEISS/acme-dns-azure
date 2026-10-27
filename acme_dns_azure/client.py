import os
import sys
import tempfile
from typing import List

from azure.identity import DefaultAzureCredential

from acme_dns_azure import config
from acme_dns_azure.certbot_manager import CertbotManager
from acme_dns_azure.context import Context
from acme_dns_azure.log import setup_custom_logger
from acme_dns_azure.exceptions import ConfigurationError, KeyVaultError
from acme_dns_azure.key_vault_manager import KeyVaultManager
from acme_dns_azure.data import CertbotResult, RotationResult

logger = setup_custom_logger(__name__)


def _has_failed_certificates(results: List[RotationResult]) -> bool:
    return any(result.result == CertbotResult.FAILED for result in results)


class AcmeDnsAzureClient:
    """Client for auto renewal of certificates. One of possible config params must be set.


    Keyword arguments:

    config_yaml -- Config based on schema as yaml string

    config_env_var -- Env var name containing base64 encoded config based on schema as yaml

    config_file -- Config path reference based on schema to yaml file

    file_path_prefix -- Path prefix for creating working dir witin /tmp dir. (default acme_dns_azure)

    work_dir -- Persistent library working directory. Existing state is retained;
                the caller owns cleanup. Defaults to a temporary directory.
    """

    def __init__(
        self,
        config_yaml: str = None,
        config_env_var: str = None,
        config_file: str = None,
        file_path_prefix: str = "acme_dns_azure",
        work_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        self.ctx = Context()
        self._work_dir = None
        self.ctx.preserve_work_dir = work_dir is not None
        if work_dir is None:
            self._work_dir = tempfile.TemporaryDirectory(prefix=file_path_prefix)
            self.ctx.work_dir = self._work_dir.name
        else:
            self.ctx.work_dir = os.path.abspath(work_dir)
            os.makedirs(self.ctx.work_dir, exist_ok=True)
        logger.info(
            "Setting working directory for certicate renewal: %s", self.ctx.work_dir
        )

        if config_yaml is not None:
            self.ctx.config = config.load(config_yaml)
        elif config_env_var is not None:
            self.ctx.config = config.load_from_base64_env_var(config_env_var)
        elif config_file is not None:
            self.ctx.config = config.load_from_file(config_file)
        else:
            raise ConfigurationError("No configuration source defined")

        self.ctx.azure_credentials = DefaultAzureCredential()
        self.ctx.keyvault = KeyVaultManager(self.ctx)
        self.certbot = CertbotManager(self.ctx)

    def __del__(self):
        if getattr(self, "_work_dir", None) is not None:
            logger.info("Cleaning up directory %s", self.ctx.work_dir)

    def issue_certificates(self) -> List[RotationResult]:
        """Create/rotate all certificates based on initial client configuration."""
        logger.info("Issuing certificates...")
        results = self.certbot.renew_certificates()
        renewed_count = sum(
            result.result in (CertbotResult.CREATED, CertbotResult.RENEWED)
            for result in results
        )
        failed_count = sum(result.result == CertbotResult.FAILED for result in results)
        if failed_count:
            logger.info(
                "Certificate renewal finished: %d renewed, %d failed",
                renewed_count,
                failed_count,
            )
        else:
            logger.info(
                "Certificate renewal finished: %d renewed",
                renewed_count,
            )
        return results


if __name__ == "__main__":
    import argparse

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--config-file-path",
            dest="file",
            metavar="path",
            required=False,
            help="Path to config file.",
        )
        parser.add_argument(
            "--config-env-var",
            dest="env",
            metavar="path",
            required=False,
            help="Name of environment variable containing config.",
        )
        parser.add_argument(
            "--work-dir",
            metavar="path",
            help="Persistent library working directory (not deleted on exit).",
        )
        args = parser.parse_args()
        work_dir_options = (
            {"work_dir": args.work_dir} if args.work_dir is not None else {}
        )
        client = AcmeDnsAzureClient(
            config_file=args.file, config_env_var=args.env, **work_dir_options
        )
    except ConfigurationError as e:
        logger.error(e)
        sys.exit(1)
    except KeyVaultError as e:
        logger.error(e)
        sys.exit(1)
    except Exception:
        logger.exception("Unable to instanciate AcmeDnsAzureClient")
        sys.exit(1)

    results = client.issue_certificates()
    if _has_failed_certificates(results):
        sys.exit(2)
