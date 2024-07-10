import os

import pytest

import acme_dns_azure.config as config_handler
from acme_dns_azure.exceptions import ConfigurationError

path_to_current_file = os.path.realpath(__file__)
current_directory = os.path.split(path_to_current_file)[0]
resources_dir = current_directory + "/resources/config/"


def test_schema_validation_success_basic_config():
    config_handler.load_from_file(resources_dir + "accepted.yaml")


def test_schema_validation_success_additional_certbot_params():
    config_handler.load_from_file(
        resources_dir + "accepted_additional_certbot_ini_params.yaml"
    )


def test_schema_validation_raises_exception_unspported_value():
    with pytest.raises(ConfigurationError):
        config_handler.load_from_file(
            resources_dir + "not_accepted_additional_param.yaml"
        )


def test_schema_validation_raises_exception_incorrect_web_reference():
    with pytest.raises(ConfigurationError):
        config_handler.load_from_file(resources_dir + "not_accepted_wrong_web_ref.yaml")


def test_schema_validation_raises_exception_cert_empty_domain():
    with pytest.raises(ConfigurationError):
        config_handler.load_from_file(
            resources_dir + "not_accepted_cert_empty_domain.yaml"
        )


def test_service_principal_os_environ_import():
    """
    Test that checks if values are correctly imported from environment variables into config. Also checks if sp credentials are preferred if "managed_identity_id" is provided in the input yaml.
    """
    os.environ["ARM_CLIENT_ID"] = "xxx"
    os.environ["ARM_CLIENT_SECRET"] = "yyy"

    config = config_handler.load_from_file(resources_dir + "accepted.yaml")
    # cleanup
    os.environ.pop("ARM_CLIENT_ID")
    os.environ.pop("ARM_CLIENT_SECRET")

    assert config["sp_client_id"] == "xxx"
    assert config["sp_client_secret"] == "yyy"
    assert config["use_provided_service_principal_credentials"] is True


def test_schema_validation_raises_exception_multiple_credential_flags():
    """
    Test that check if providing multiple "use_*_credentials" set to true raises an error.
    """
    with pytest.raises(ConfigurationError):
        config_handler.load_from_file(
            resources_dir
            + "credential_tests/not_accepted_multiple_credential_flags.yaml"
        )


@pytest.mark.parametrize(
    "input_file",
    [
        ("credential_tests/not_accepted_no_credentials.yaml"),
        ("credential_tests/not_accepted_incomplete_sp_credentials_pwd.yaml"),
        ("credential_tests/not_accepted_incomplete_sp_credentials_id.yaml"),
        ("credential_tests/not_accepted_incomplete_sp_credentials_cert.yaml"),
        ("credential_tests/not_accepted_invalid_sp_credentials.yaml"),
    ],
)
def test_schema_validation_raises_exception_azure_credentials_not_present_or_incomplete(
    input_file,
):
    """
    Test that check if providing no or incomplete Azure credentials raises an error.
    """
    with pytest.raises(ConfigurationError):
        config_handler.load_from_file(resources_dir + input_file)
