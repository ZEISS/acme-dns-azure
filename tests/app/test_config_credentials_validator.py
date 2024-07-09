import os

import pytest

import acme_dns_azure.config as config_handler

path_to_current_file = os.path.realpath(__file__)
current_directory = os.path.split(path_to_current_file)[0]
resources_dir = current_directory + "/resources/config/"
validation_success_message = "Azure credentials validation successful!"


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
        "sp_client_id": "00000000-0000-0000-0000-000000000000",
        "sp_client_secret": "xyz",
        "managed_identity_id": "00000000-0000-0000-0000-000000000000",
    }
    # Execute logic, save the resulting objects.
    config, result, message = config_handler.validate_azure_credentials_use(config)

    # Calculate the number of True flags in the dict. Convert to list to tolerate strings.
    true_flag_number = list(config.values()).count(True)

    # If the dict has more than one or 0 true flags we expect the validation to fail in this case.
    if true_flag_number > 1 or true_flag_number == 0:
        assert result is False
        # The function should return an error message not a success message.
        assert message != validation_success_message

    # if there is exactly one true flag in the dict the validation should be successful.
    if true_flag_number == 1:
        assert result is True
        # This is checked to make sure the validation of the error message is correct.
        assert message == validation_success_message


@pytest.mark.parametrize("sp_id", [None, ""])
@pytest.mark.parametrize("sp_secret", [None, ""])
@pytest.mark.parametrize("sp_cert_path", [None, ""])
def test_additional_sp_values_completeness_failure_no_values(
    sp_id, sp_secret, sp_cert_path
):
    """
    Test if the check of service principal id and password fails if they are all empty.
    """
    config = {
        "use_provided_service_principal_credentials": True,
        "sp_client_id": sp_id,
        "sp_client_secret": sp_secret,
        "sp_certificate_path": sp_cert_path,
    }

    config, result, message = config_handler.validate_azure_credentials_use(config)

    assert result is False
    assert message != validation_success_message


@pytest.mark.parametrize(
    "sp_id,sp_secret,sp_cert_path",
    [
        ("00000000-0000-0000-0000-000000000000", "xyz", "/path/to/cert.pem"),
        ("00000000-0000-0000-0000-000000000000", None, None),
        (None, "xyz", "/path/to/cert.pem"),
        (None, "xyz", None),
        (None, None, "/path/to/cert.pem"),
    ],
)
def test_additional_sp_values_completeness_failure(sp_id, sp_secret, sp_cert_path):
    """
    Test if the check of service principal id and password fails if some are empty or all present.
    """
    config = {
        "use_provided_service_principal_credentials": True,
        "sp_client_id": sp_id,
        "sp_client_secret": sp_secret,
        "sp_certificate_path": sp_cert_path,
    }

    config, result, message = config_handler.validate_azure_credentials_use(config)

    assert result is False
    assert message != validation_success_message


@pytest.mark.parametrize(
    "sp_id,sp_secret,sp_cert_path",
    [
        ("00000000-0000-0000-0000-000000000000", "xyz", None),
        ("00000000-0000-0000-0000-000000000000", None, "/path/to/cert.pem"),
    ],
)
def test_additional_sp_values_completeness_success(sp_id, sp_secret, sp_cert_path):
    """
    Test if the check of service principal id and password succeeds if a valid pair is present.
    """
    config = {
        "use_provided_service_principal_credentials": True,
        "sp_client_id": sp_id,
        "sp_client_secret": sp_secret,
        "sp_certificate_path": sp_cert_path,
    }

    config, result, message = config_handler.validate_azure_credentials_use(config)

    assert result is True
    assert message == validation_success_message


@pytest.mark.parametrize(
    "mi_id",
    [None, ""],
)
def test_additional_mi_values_completeness_failure(mi_id):
    """
    Test if the check of managed identity id fails if managed identity id is missing.
    Success is checked in test_use_x_credentials_flags_combinations.
    """
    config = {
        "use_managed_identity_credentials": True,
        "managed_identity_id": mi_id,
    }

    config, result, message = config_handler.validate_azure_credentials_use(config)

    assert result is False
    assert message != validation_success_message
