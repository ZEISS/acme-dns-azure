import base64
import os
import re

from urllib.parse import urlparse
from strictyaml import load as validate

from acme_dns_azure.log import setup_custom_logger
from acme_dns_azure.exceptions import ConfigurationError
from .schema import schema

logger = setup_custom_logger(__name__)


def load(config_yaml: str = ""):
    try:
        config = validate(config_yaml, schema).data
    except Exception as e:
        logger.exception("Unable to parse configuration.")
        raise ConfigurationError("Unable to parse configuration") from e

    if "ARM_CLIENT_ID" in os.environ and "ARM_CLIENT_SECRET" in os.environ:
        config["sp_client_id"] = os.environ["ARM_CLIENT_ID"]
        config["sp_client_secret"] = os.environ["ARM_CLIENT_SECRET"]

    config, result, message = validate_azure_credentials_use(config)

    if result is False:
        raise ConfigurationError(message)

    logger.info(message)

    if config["keyvault_account_secret_name"] == "":
        config["keyvault_account_secret_name"] = "acme-account-%s" % (
            re.sub("[^-a-zA-Z0-9]+", "-", urlparse(config["server"]).netloc)
        )

    return config


def load_from_base64_env_var(env_var: str = None):
    try:
        env_config_b64 = os.environ.get(env_var)
        if env_config_b64:
            logger.debug("Loading config from environment variable '%s'.", env_var)
            return load(base64.b64decode(env_config_b64).decode("utf8"))
        else:
            raise ConfigurationError(
                "Environment variable '%s' has an empty value.", env_var
            )
    except base64.binascii.Error as e:
        raise ConfigurationError(
            "Unable to base64 decode configuration provided in environment variable '%s': %s"
            % (env_var, e)
        )
    except Exception as e:
        raise ConfigurationError("Error while loading configuration: %s" % e)


def load_from_file(filename: str = None):
    try:
        logger.debug("Loading config from file '%s'." % filename)
        with open(filename, "r") as file:
            return load(file.read())
    except FileNotFoundError:
        raise ConfigurationError("Config file not found at '%s'" % filename)
    except OSError as e:
        raise ConfigurationError(
            "Unable to read configuration from '%s': %s" % (filename, e.strerror)
        )
    except Exception as e:
        raise ConfigurationError("Error while loading configuration: %s" % e)


def validate_azure_credentials_use(config: dict):
    """
    Validates config for valid Azure credentials configuration.

    Args:
        config (dict): pre validated config.yaml as dict.

    Returns:
        config (dict): config modified as applicable.
        result (bool): result of the validation, false if validation failed.
        message (string): a string describing the result or why the validation failed.
    """
    # check if only one identity flag is set to true
    credential_flags = 0
    if config.get("use_system_assigned_identity_credentials"):
        credential_flags += 1
    if config.get("use_azure_cli_credentials"):
        credential_flags += 1
    if config.get("use_workload_identity_credentials"):
        credential_flags += 1
    if config.get("use_managed_identity_credentials"):
        credential_flags += 1
    if config.get("use_provided_service_principal_credentials"):
        credential_flags += 1

    # to avoid confusion we only accept one flag to be set to true
    if credential_flags > 1:
        message = f'{credential_flags} "use_*_identity" flags set to true.'
        return config, False, message

    # if no flags are set to true we check if other fields are enough for authentication, this was done for backwards compatibility. The old logic of preferring the sp credentials is preserved here.
    if credential_flags == 0:
        if not (
            config.get("sp_client_id")
            and (config.get("sp_client_secret") or config.get("sp_certificate_path"))
        ):
            if not config.get("managed_identity_id"):
                message = "Azure credentials not specified or incomplete."
                return config, False, message
            else:
                config["use_managed_identity_credentials"] = True
        else:
            config["use_provided_service_principal_credentials"] = True
    # check if the additional values are provided for Service principal and Managed identity use
    if (
        config.get("use_provided_service_principal_credentials")
        and (
            not (
                config.get("sp_client_id")
                and (
                    config.get("sp_client_secret") or config.get("sp_certificate_path")
                )
            )
        )
        or (config.get("sp_certificate_path") and config.get("sp_client_secret"))
    ):
        message = "Service Principal credential set is invalid. Id and either password or certificate path must be provided (not both)."
        return config, False, message

    elif config.get("use_managed_identity_credentials") and not config.get(
        "managed_identity_id"
    ):
        message = "Managed identity id is missing!"
        return config, False, message

    message = "Azure credentials validation successful!"
    return config, True, message
