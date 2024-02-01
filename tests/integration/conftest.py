import pytest
import os
from tests.integration.helper_framework.acme_config_manager import AcmeConfigManager
from tests.integration.helper_framework.azure_key_vault_manager import (
    AzureKeyVaultManager,
)
from tests.integration.helper_framework.azure_dns_zone_manager import (
    AzureDnsZoneManager,
)

path_to_current_file = os.path.realpath(__file__)
current_directory = os.path.split(path_to_current_file)[0]


def pytest_addoption(parser):
    parser.addoption(
        "--dns-zone-name",
        action="store",
        required=True,
        help="Please set DNS Zone reference. Test will create RecordSets here.",
    )
    parser.addoption(
        "--dns-zone-resource-group-name",
        action="store",
        required=True,
        help="Please set DNS Zone reference. Test will create RecordSets here.",
    )
    parser.addoption(
        "--subscription-id",
        action="store",
        required=True,
        help="Please set subsciption ID.",
    )
    parser.addoption(
        "--keyvault-uri",
        action="store",
        required=True,
        help="Please set Key Vault Uri.",
    )
    parser.addoption(
        "--config-file-path",
        action="store",
        required=False,
        default=current_directory + "/infra/config.yaml",
        help="Path for config file for testsuite 'happy path'.",
    )
    parser.addoption(
        "--resource-prefix",
        action="store",
        required=False,
        default=None,
        help="Prefix added to every resource created within the test: Keyvault Certificates and DNS zone record entries.",
    )


@pytest.fixture(autouse=True)
def resource_prefix(request):
    return request.config.getoption("--resource-prefix")


@pytest.fixture(autouse=True)
def config_file_path(request):
    return request.config.getoption("--config-file-path")


@pytest.fixture(autouse=False)
def acme_config_manager():
    acme_config_manager = AcmeConfigManager()
    yield acme_config_manager


@pytest.fixture(autouse=False)
def azure_dns_zone_manager(request):
    subscription_id = request.config.getoption("--subscription-id")
    dns_zone_name = request.config.getoption("--dns-zone-name")
    dns_zone_resource_group_name = request.config.getoption(
        "--dns-zone-resource-group-name"
    )
    azure_dns_zone_manager = AzureDnsZoneManager(
        subscription_id=subscription_id,
        resource_group_name=dns_zone_resource_group_name,
        zone_name=dns_zone_name,
    )
    yield azure_dns_zone_manager
    print("\nTeardown DNS resources...\n")
    azure_dns_zone_manager.clean_up_all_resources()


@pytest.fixture(autouse=False)
def azure_key_vault_manager(request):
    keyvault_uri = request.config.getoption("--keyvault-uri")
    azure_key_vault_manager = AzureKeyVaultManager(keyvault_uri=keyvault_uri)
    yield azure_key_vault_manager
    print("\nTeardown KeyVault resources...\n")
    azure_key_vault_manager.clean_up_all_resources()
