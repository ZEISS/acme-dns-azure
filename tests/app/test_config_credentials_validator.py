import os

import pytest

import acme_dns_azure.config as config_handler

path_to_current_file = os.path.realpath(__file__)
current_directory = os.path.split(path_to_current_file)[0]
resources_dir = current_directory + "/resources/config/"


def test_no_credential_flags_with_manged_identity_id_provided():
    """
    Test that checks if "use_managed_identity_credentials" flag is true if "managed_identity_id" is provided in config yaml.
    """
    config = config_handler.load_from_file(resources_dir + "accepted.yaml")
    assert config["use_managed_identity_credentials"] is True


@pytest.mark.parametrize("usaic", [True, False])
@pytest.mark.parametrize("uacc", [True, False])
@pytest.mark.parametrize("uwic", [True, False])
@pytest.mark.parametrize("umic", [True, False])
@pytest.mark.parametrize("upspc", [True, False])
def test_use_x_credentials_flags_combinations(
    usaic: bool, uacc: bool, uwic: bool, umic: bool, upspc: bool
):
    """
    Test for asserting if all credential flag combinations are checked correctly.
    """
    # Initialize a config dict to work on, translation of yaml into config is tested separately.
    config = {
        "use_system_assigned_identity_credentials": usaic,
        "use_azure_cli_credentials": uacc,
        "use_workload_identity_credentials": uwic,
        "use_managed_identity_credentials": umic,
        "use_provided_service_principal_credentials": upspc,
    }
    # Execute logic, save the resulting objects.
    config, result, message = config_handler.validate_azure_credentials_use(config)

    # Calculate the number of True flags in the dict.
    true_flag_number = sum(config.values())

    # If the dict has more than one or 0 true flags we expect the validation to fail in this case.
    if true_flag_number > 1 or true_flag_number == 0:
        assert result is False
        # The function should return an error message not a success message.
        assert message != "Azure credentials validation successful!"

    # if there is exactly one true flag in the dict the validation should be successful.
    if true_flag_number == 1:
        assert result is True
        # This is checked to make sure the validation of the error message is correct.
        assert message == "Azure credentials validation successful!"
