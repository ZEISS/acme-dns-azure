import pytest
import os
from tests.integration.helper_framework.acme_config_manager import AcmeConfigManager
from tests.integration.helper_framework.azure_key_vault_manager import (
    AzureKeyVaultManager,
)
from tests.integration.helper_framework.azure_dns_zone_manager import (
    AzureDnsZoneManager,
)
from tests.integration.helper_framework.azure_ad_manager import (
    AzureADManager,
)

path_to_current_file = os.path.realpath(__file__)
current_directory = os.path.split(path_to_current_file)[0]


def pytest_addoption(parser):
    parser.addoption(
        "--dns-zone-id",
        action="store",
        required=True,
        help="Please set DNS Zone resource ID. Test will create RecordSets here.",
    )
    parser.addoption(
        "--dns-zone-name",
        action="store",
        required=True,
        help="Please set DNS Zone name. Test will create RecordSets here.",
    )
    parser.addoption(
        "--dns-zone-resource-group-name",
        action="store",
        required=True,
        help="Please set DNS Zone resource group name. Test will create RecordSets here.",
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
        help="Path for config file for testsuite.",
    )
    parser.addoption(
        "--resource-prefix",
        action="store",
        required=False,
        default=None,
        help="Prefix added to every resource created within the test: Keyvault Certificates and DNS zone record entries.",
    )
    parser.addoption(
        "--resource-name",
        action="store",
        required=False,
        default="testautohappypath",
        help="Name used for every resource created within the test: Keyvault Certificates and DNS zone record entries.",
    )
    parser.addoption(
        "--principal-id",
        action="store",
        required=False,
        help="Principal ID for assigning role assignments for temporarly created DNS records.",
    )


@pytest.fixture(autouse=True)
def print_linebreak():
    print("")


@pytest.fixture(autouse=True)
def resource_name(request):
    prefix = request.config.getoption("--resource-prefix")
    default_name = request.config.getoption("--resource-name")
    if prefix is not None:
        default_name = prefix + default_name
    return default_name


@pytest.fixture(autouse=False)
def dns_zone_name(request):
    return request.config.getoption("--dns-zone-name")


@pytest.fixture(autouse=True)
def config_file_path(request):
    return request.config.getoption("--config-file-path")


@pytest.fixture(autouse=True)
def principal_id(request):
    return request.config.getoption("--principal-id")


@pytest.fixture(autouse=False)
def acme_config_manager(request):
    dns_zone_resource_id = request.config.getoption("--dns-zone-id")
    acme_config_manager = AcmeConfigManager(
        dns_zone_resource_id=dns_zone_resource_id,
    )
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
    azure_dns_zone_manager.clean_up_all_resources()


@pytest.fixture(autouse=False)
def azure_key_vault_manager(request):
    keyvault_uri = request.config.getoption("--keyvault-uri")
    azure_key_vault_manager = AzureKeyVaultManager(keyvault_uri=keyvault_uri)
    yield azure_key_vault_manager
    azure_key_vault_manager.clean_up_all_resources()


@pytest.fixture(autouse=False)
def azure_ad_manager(request):
    subscription_id = request.config.getoption("--subscription-id")
    azure_ad_manager = AzureADManager(subscription_id=subscription_id)
    yield azure_ad_manager
    azure_ad_manager.clean_up_all_resources()
