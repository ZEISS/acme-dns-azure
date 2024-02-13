from datetime import datetime, timezone
from acme_dns_azure.client import AcmeDnsAzureClient
from acme_dns_azure.certbot_manager import (
    RotationResult,
    CertbotResult,
)
from tests.integration.helper_framework.azure_dns_zone_manager import (
    DnsZoneDomainReference,
)


def get_latest_properties_of_certificate_versions(key_vault_certificates):
    now = datetime.now(timezone.utc)
    dates = []
    for version in key_vault_certificates:
        dates.append(version.created_on)
    latest = max(dt for dt in dates if dt < now)
    return key_vault_certificates[dates.index(latest)]


def test_automatic_renewal_for_existing_cert_multiple_domains_skipped(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    config_file_path,
    resource_name,
):
    ## Config
    key_vault_cert_name = dns_zone_record_name = resource_name
    cert_validity_in_month = 1
    acme_config_renew_before_expiry_in_days = 31

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    cname1: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name=dns_zone_record_name + "1",
    )
    cname2: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name=dns_zone_record_name + "2",
    )

    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name,
        subject=f"CN={cname1.name}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[cname1.name],
    )

    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[cname1, cname2],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: [RotationResult] = client.issue_certificates()

    ## Validate
    for result in results:
        assert result.result == CertbotResult.SKIPPED
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={cname1.name}"
    assert san == [cname1.name]


def test_automatic_renewal_for_existing_cert_multiple_domains_overwritten(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    config_file_path,
    resource_name,
):
    ## Config
    key_vault_cert_name = dns_zone_record_name = resource_name
    cert_validity_in_month = 1
    acme_config_renew_before_expiry_in_days = 31
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    acme_config_manager.set_config_param("update_cert_domains", True)

    ## Init

    cname1: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name=dns_zone_record_name + "1",
    )
    cname2: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name=dns_zone_record_name + "2",
    )

    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name,
        subject=f"CN={cname1.name}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[cname1.name],
    )

    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[cname1, cname2],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: [RotationResult] = client.issue_certificates()

    ## Validate
    for result in results:
        assert result.result == CertbotResult.RENEWED
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={cname1.name}"
    assert san == [cname1.name, cname2.name]


def test_create_cert_for_dns_delegation_dedicated_txt_with_minimum_permission_success(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    azure_ad_manager,
    config_file_path,
    resource_name,
    principal_id,
):
    ## Config
    key_vault_cert_name = dns_zone_record_name = resource_name
    config_file_path = config_file_path.replace(
        "config.yaml", "no_permission_config.yaml"
    )
    acme_config_manager.base_config_from_file(file_path=config_file_path)

    ## Init

    txt_record: DnsZoneDomainReference = azure_dns_zone_manager.create_txt_record(
        name="_acme-dedicated", value="-"
    )
    cname: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + dns_zone_record_name,
        value=txt_record.name,
    )

    azure_ad_manager.create_role_assignment(
        scope=txt_record.dns_zone_resource_id,
        principal_id=principal_id,
    )

    delegation_config = DnsZoneDomainReference(
        dns_zone_resource_id=txt_record.dns_zone_resource_id,
        name=cname.name.replace("_acme-challenge.", ""),
    )

    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[delegation_config],
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: [RotationResult] = client.issue_certificates()

    ## Validate
    for result in results:
        assert result.result == CertbotResult.CREATED
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={delegation_config.name}"
    assert san == [delegation_config.name]


def test_create_cert_for_dns_delegation_dedicated_txt_without_minimum_permission_failure(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    azure_ad_manager,
    config_file_path,
    resource_name,
    principal_id,
):
    ## Config
    key_vault_cert_name = dns_zone_record_name = resource_name
    config_file_path = config_file_path.replace(
        "config.yaml", "no_permission_config.yaml"
    )
    acme_config_manager.base_config_from_file(file_path=config_file_path)

    ## Init

    txt_record: DnsZoneDomainReference = azure_dns_zone_manager.create_txt_record(
        name="_acme-dedicated", value="-"
    )
    cname: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + dns_zone_record_name,
        value=txt_record.name,
    )

    delegation_config = DnsZoneDomainReference(
        dns_zone_resource_id=txt_record.dns_zone_resource_id,
        name=cname.name.replace("_acme-challenge.", ""),
    )

    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[delegation_config],
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: [RotationResult] = client.issue_certificates()

    ## Validate
    for result in results:
        assert result.result == CertbotResult.FAILED


def test_create_cert_for_dns_delegation_shared_txt_shared_cert_with_minimum_permission_success(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    azure_ad_manager,
    config_file_path,
    resource_name,
    principal_id,
):
    ## Config
    key_vault_cert_name = dns_zone_record_name = resource_name
    config_file_path = config_file_path.replace(
        "config.yaml", "no_permission_config.yaml"
    )
    acme_config_manager.base_config_from_file(file_path=config_file_path)

    ## Init

    txt_record: DnsZoneDomainReference = azure_dns_zone_manager.create_txt_record(
        name="_acme-shared", value="-"
    )
    cname1: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + dns_zone_record_name + "1",
        value=txt_record.name,
    )
    cname2: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + dns_zone_record_name + "2",
        value=txt_record.name,
    )

    azure_ad_manager.create_role_assignment(
        scope=txt_record.dns_zone_resource_id,
        principal_id=principal_id,
    )

    delegation_config1 = DnsZoneDomainReference(
        dns_zone_resource_id=txt_record.dns_zone_resource_id,
        name=cname1.name.replace("_acme-challenge.", ""),
    )
    delegation_config2 = DnsZoneDomainReference(
        dns_zone_resource_id=txt_record.dns_zone_resource_id,
        name=cname2.name.replace("_acme-challenge.", ""),
    )

    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[delegation_config1, delegation_config2],
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: [RotationResult] = client.issue_certificates()

    ## Validate
    for result in results:
        assert result.result == CertbotResult.CREATED
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={delegation_config1.name}"
    assert san == [delegation_config1.name, delegation_config2.name]


def test_create_cert_for_dns_delegation_shared_txt_single_cert_with_minimum_permission_success(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    azure_ad_manager,
    config_file_path,
    resource_name,
    principal_id,
):
    ## Config
    key_vault_cert_name = dns_zone_record_name = resource_name
    config_file_path = config_file_path.replace(
        "config.yaml", "no_permission_config.yaml"
    )
    acme_config_manager.base_config_from_file(file_path=config_file_path)

    ## Init

    txt_record: DnsZoneDomainReference = azure_dns_zone_manager.create_txt_record(
        name="_acme-shared", value="-", ttl="120"
    )
    cname1: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + dns_zone_record_name + "1",
        value=txt_record.name,
    )
    cname2: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + dns_zone_record_name + "2",
        value=txt_record.name,
    )

    azure_ad_manager.create_role_assignment(
        scope=txt_record.dns_zone_resource_id,
        principal_id=principal_id,
    )

    delegation_config1 = DnsZoneDomainReference(
        dns_zone_resource_id=txt_record.dns_zone_resource_id,
        name=cname1.name.replace("_acme-challenge.", ""),
    )
    delegation_config2 = DnsZoneDomainReference(
        dns_zone_resource_id=txt_record.dns_zone_resource_id,
        name=cname2.name.replace("_acme-challenge.", ""),
    )

    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name + "1",
        domain_references=[delegation_config1],
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name + "2",
        domain_references=[delegation_config2],
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: [RotationResult] = client.issue_certificates()

    ## Validate
    assert results[0].result == CertbotResult.CREATED
    assert results[1].result == CertbotResult.CREATED
    cn1, san1 = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name + "1"
    )
    cn2, san2 = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name + "2"
    )
    assert cn1 == f"CN={delegation_config1.name}"
    assert san1 == [delegation_config1.name]
    assert cn2 == f"CN={delegation_config2.name}"
    assert san2 == [delegation_config2.name]


# TODO: Test should succeed with DNS propagation time = 10s when issue is fixed:
# https://github.com/terrycain/certbot-dns-azure/issues/42
