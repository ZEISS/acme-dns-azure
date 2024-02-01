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
