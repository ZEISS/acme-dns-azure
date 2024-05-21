from datetime import datetime, timedelta, timezone
from acme_dns_azure.client import AcmeDnsAzureClient
from acme_dns_azure.data import (
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


def test_automatic_renewal_for_existing_cert_single_domain(
    acme_config_manager,
    azure_key_vault_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name = resource_name + "." + dns_zone_name
    key_vault_cert_name = domain_name.replace(".", "")
    cert_validity_in_month = 1
    acme_config_renew_before_expiry_in_days = 31

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name,
        subject=f"CN={domain_name}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[domain_name],
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[DnsZoneDomainReference(name=domain_name)],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

    ## Validate
    cert_versions = list(
        azure_key_vault_manager.list_properties_of_certificate_versions(
            name=key_vault_cert_name
        )
    )
    assert len(cert_versions) is 2
    cert = get_latest_properties_of_certificate_versions(cert_versions)
    assert cert.enabled
    assert (
        cert.expires_on
        >= datetime.now(timezone.utc) + timedelta(days=89)
        <= datetime.now(timezone.utc) + timedelta(days=91)
    )
    for result in results:
        assert result.result == CertbotResult.RENEWED


def test_skip_for_valid_existing_cert(
    acme_config_manager,
    azure_key_vault_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name = resource_name + "." + dns_zone_name
    key_vault_cert_name = domain_name.replace(".", "")
    cert_validity_in_month = 3
    acme_config_renew_before_expiry_in_days = 30

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name,
        subject=f"CN={domain_name}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[domain_name],
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[DnsZoneDomainReference(name=domain_name)],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

    ## Validate
    cert_versions = list(
        azure_key_vault_manager.list_properties_of_certificate_versions(
            name=key_vault_cert_name
        )
    )
    assert len(cert_versions) is 1
    for result in results:
        assert result.result == CertbotResult.STILL_VALID


def test_automatic_renewal_for_existing_cert_only_once_then_skipped(
    acme_config_manager,
    azure_key_vault_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name = resource_name + "." + dns_zone_name
    key_vault_cert_name = domain_name.replace(".", "")
    cert_validity_in_month = 1
    acme_config_renew_before_expiry_in_days = 31

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name,
        subject=f"CN={domain_name}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[domain_name],
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[DnsZoneDomainReference(name=domain_name)],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    first_results: list[RotationResult] = client.issue_certificates()

    # new instance for using different tmp dir
    client2 = AcmeDnsAzureClient(acme_config_manager.config)
    second_results: list[RotationResult] = client2.issue_certificates()

    ## Validate
    cert_versions = list(
        azure_key_vault_manager.list_properties_of_certificate_versions(
            name=key_vault_cert_name
        )
    )
    assert len(cert_versions) is 2
    cert = get_latest_properties_of_certificate_versions(cert_versions)
    assert cert.enabled
    assert (
        cert.expires_on
        >= datetime.now(timezone.utc) + timedelta(days=89)
        <= datetime.now(timezone.utc) + timedelta(days=91)
    )
    for result in first_results:
        assert result.result == CertbotResult.RENEWED
    for result in second_results:
        assert result.result == CertbotResult.STILL_VALID


def test_automatic_renewal_for_existing_cert_multiple_domains(
    acme_config_manager,
    azure_key_vault_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name1 = resource_name + "1." + dns_zone_name
    domain_name2 = resource_name + "2." + dns_zone_name
    key_vault_cert_name = domain_name1.replace(".", "")
    cert_validity_in_month = 1
    acme_config_renew_before_expiry_in_days = 31

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name,
        subject=f"CN={domain_name1}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[domain_name1, domain_name2],
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[
            DnsZoneDomainReference(name=domain_name1),
            DnsZoneDomainReference(name=domain_name2),
        ],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

    ## Validate
    for result in results:
        assert result.result == CertbotResult.RENEWED
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={domain_name1}"
    assert san == [domain_name1, domain_name2]


def test_handle_two_certificates_create_and_renew(
    acme_config_manager,
    azure_key_vault_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name1 = resource_name + "1." + dns_zone_name
    domain_name2 = resource_name + "2." + dns_zone_name
    key_vault_cert_name1 = domain_name1.replace(".", "")
    key_vault_cert_name2 = domain_name2.replace(".", "")
    cert_validity_in_month = 1
    acme_config_renew_before_expiry_in_days = 31

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name1,
        subject=f"CN={domain_name1}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[domain_name1],
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name1,
        domain_references=[
            DnsZoneDomainReference(name=domain_name1),
        ],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name2,
        domain_references=[
            DnsZoneDomainReference(name=domain_name2),
        ],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

    ## Validate
    cert_versions1 = list(
        azure_key_vault_manager.list_properties_of_certificate_versions(
            name=key_vault_cert_name1
        )
    )
    cert_versions2 = list(
        azure_key_vault_manager.list_properties_of_certificate_versions(
            name=key_vault_cert_name2
        )
    )
    assert len(cert_versions1) is 2
    assert len(cert_versions2) is 1


def test_create_new_cert_when_not_present_in_vault(
    acme_config_manager,
    azure_key_vault_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name = resource_name + "." + dns_zone_name
    key_vault_cert_name = domain_name.replace(".", "")

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[
            DnsZoneDomainReference(name=domain_name),
        ],
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

    ## Validate
    cert_versions = list(
        azure_key_vault_manager.list_properties_of_certificate_versions(
            name=key_vault_cert_name
        )
    )
    assert len(cert_versions) is 1
    cert = get_latest_properties_of_certificate_versions(cert_versions)
    assert cert.enabled
    assert (
        cert.expires_on
        >= datetime.now(timezone.utc) + timedelta(days=89)
        <= datetime.now(timezone.utc) + timedelta(days=91)
    )
    for result in results:
        assert result.result == CertbotResult.CREATED


def test_wildcard_create_new_cert(
    acme_config_manager,
    azure_key_vault_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name = "*." + resource_name + "." + dns_zone_name
    key_vault_cert_name = domain_name.removeprefix("*.").replace(".", "")

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[
            DnsZoneDomainReference(name=domain_name),
        ],
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

    ## Validate
    for result in results:
        assert result.result == CertbotResult.CREATED
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={domain_name}"
    assert san == [domain_name]


def test_automatic_renewal_for_wildcard_cert(
    acme_config_manager,
    azure_key_vault_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name = "*." + resource_name + "." + dns_zone_name
    key_vault_cert_name = domain_name.removeprefix("*.").replace(".", "")
    cert_validity_in_month = 1
    acme_config_renew_before_expiry_in_days = 31

    ## Init
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name,
        subject=f"CN={domain_name}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[domain_name],
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[
            DnsZoneDomainReference(name=domain_name),
        ],
        renew_before_expiry=acme_config_renew_before_expiry_in_days,
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

    ## Validate
    cert_versions = list(
        azure_key_vault_manager.list_properties_of_certificate_versions(
            name=key_vault_cert_name
        )
    )
    assert len(cert_versions) is 2
    cert = get_latest_properties_of_certificate_versions(cert_versions)
    assert cert.enabled
    assert (
        cert.expires_on
        >= datetime.now(timezone.utc) + timedelta(days=89)
        <= datetime.now(timezone.utc) + timedelta(days=91)
    )
    for result in results:
        assert result.result == CertbotResult.RENEWED
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={domain_name}"
    assert san == [domain_name]


def test_create_cert_for_txt_record_without_existing_cname_txt_not_deleted_success(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name = resource_name + "." + dns_zone_name
    key_vault_cert_name = domain_name.replace(".", "")

    acme_config_manager.base_config_from_file(file_path=config_file_path)

    azure_dns_zone_manager.create_txt_record(
        name="_acme-challenge." + resource_name, value="-"
    )
    import time

    time.sleep(1)

    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[
            DnsZoneDomainReference(name=domain_name),
        ],
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

    ## Validate
    assert results[0].result == CertbotResult.CREATED
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={domain_name}"
    assert san == [domain_name]

    assert azure_dns_zone_manager.record_exists(name="_acme-challenge." + resource_name)
