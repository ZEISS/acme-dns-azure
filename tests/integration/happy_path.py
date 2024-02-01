import logging
from datetime import datetime, timedelta, timezone
from acme_dns_azure.client import AcmeDnsAzureClient
from tests.integration.helper_framework.azure_dns_zone_manager import (
    DnsZoneDomainReference,
)


def test_automatic_renewal_for_existing_cert(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    config_file_path,
    resource_prefix,
):
    ## Config
    key_vault_cert_name = "testautohappypath"
    cert_validity_in_month = 1
    dns_zone_record_name = "testautohappypath"
    acme_config_renew_before_expiry_in_days = 31
    if resource_prefix is not None:
        key_vault_cert_name = resource_prefix + key_vault_cert_name
        dns_zone_record_name = resource_prefix + dns_zone_record_name

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    cname: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name=dns_zone_record_name,
    )

    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name,
        subject=f"CN={cname.name}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[cname.name],
    )

    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[cname],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    client.issue_certificates()

    ## Validate
    cert_versions = list(
        azure_key_vault_manager.list_properties_of_certificate_versions(
            name=key_vault_cert_name
        )
    )
    assert len(cert_versions) is 2
    assert cert_versions[1].enabled
    assert (
        cert_versions[1].expires_on
        >= datetime.now(timezone.utc) + timedelta(days=89)
        <= datetime.now(timezone.utc) + timedelta(days=91)
    )

    ## cleanup (automatically)
