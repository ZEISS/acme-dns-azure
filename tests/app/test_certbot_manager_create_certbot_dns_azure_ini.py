import os
import filecmp

from mock import patch
import pytest
from test_certbot_manager import _dns_validation_challenge_fixture, certbot_manager_init

from acme_dns_azure.certbot_manager import CertbotManager

path_to_current_file = os.path.realpath(__file__)
current_directory = os.path.split(path_to_current_file)[0]
resources_dir = current_directory + "/resources/"


@patch.object(CertbotManager, "__init__", certbot_manager_init)
@pytest.mark.parametrize(
    "input_file,expected_file",
    [
        (
            "config/credential_tests/accepted_azure_cli_credentials.yaml",
            "certbot_init/expected_azure_cli_credentials.ini",
        ),
        (
            "config/credential_tests/accepted_managed_idty_no_flag.yaml",
            "certbot_init/expected_managed_idty.ini",
        ),
        (
            "config/credential_tests/accepted_managed_idty.yaml",
            "certbot_init/expected_managed_idty.ini",
        ),
        (
            "config/credential_tests/accepted_sp_credentials_no_flag.yaml",
            "certbot_init/expected_sp_credentials.ini",
        ),
        (
            "config/credential_tests/accepted_sp_credentials.yaml",
            "certbot_init/expected_sp_credentials.ini",
        ),
        (
            "config/credential_tests/accepted_system_assigned_idty_credentials.yaml",
            "certbot_init/expected_system_assigned_idty_credentials.ini",
        ),
        (
            "config/credential_tests/accepted_workload_idty_credentials.yaml",
            "certbot_init/expected_workload_idty_credentials.ini",
        ),
    ],
)
def test_azure_cli_credentials(
    working_dir,
    cleanup_certbot_init_files,
    cleanup_certbot_config_dir,
    input_file,
    expected_file,
):
    """
    Test to check if the data flow and the logic of _create_certbot_dns_azure_ini function work as intended.

    Args:
        input_file (_type_): yaml file with input config
        expected_file (_type_): output ini file of _create_certbot_dns_azure_ini
    """
    CertbotManager(working_dir=working_dir, config_file=input_file)
    assert filecmp.cmp(
        working_dir + "certbot_dns_azure.ini", resources_dir + expected_file
    )
