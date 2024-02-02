import logging
from datetime import datetime, timedelta, timezone
from acme_dns_azure.client import AcmeDnsAzureClient
from acme_dns_azure.certbot_manager import (
    RotationResult,
    CertbotResult,
    RotationCertificate,
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


def test_automatic_renewal_for_existing_cert(
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
    results: [RotationResult] = client.issue_certificates()

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
    azure_dns_zone_manager,
    config_file_path,
    resource_name,
):
    ## Config
    key_vault_cert_name = dns_zone_record_name = resource_name
    cert_validity_in_month = 3
    acme_config_renew_before_expiry_in_days = 30

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
    results: [RotationResult] = client.issue_certificates()

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
    first_results: [RotationResult] = client.issue_certificates()

    # new instance for using different tmp dir
    client2 = AcmeDnsAzureClient(acme_config_manager.config)
    second_results: [RotationResult] = client2.issue_certificates()

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
        san_dns_names=[cname1.name, cname2.name],
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
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={cname1.name}"
    assert san == [cname1.name, cname2.name]
    for result in results:
        assert result.result == CertbotResult.RENEWED


# def test_automatic_renewal_for_existing_cert_multiple_domains_conflict_renewal_skipped():
#     pass


# def test_automatic_renewal_for_existing_cert_multiple_domains_conflict_renewal_overwrite():
#     pass


# def test_create_new_cert_when_not_present_in_vault(
#     acme_config_manager,
#     azure_key_vault_manager,
#     azure_dns_zone_manager,
#     config_file_path,
#     resource_name,
# ):
#     # Config
#     key_vault_cert_name = dns_zone_record_name = resource_name
#     acme_config_manager.base_config_from_file(file_path=config_file_path)

#     certbot_ini = """
#         key-type = rsa
#         rsa-key-size = 4096
#         break-my-certs  = false
# #     """
#     acme_config_manager.certbot_ini(certbot_ini)

#     # Init

#     cname: DnsZoneDomainReference = azure_dns_zone_manager.create_cname_record(
#         name=dns_zone_record_name,
#     )

#     acme_config_manager.add_certificate_to_config(
#         cert_name=key_vault_cert_name,
#         domain_references=[cname],
#     )

#     # Test
#     client = AcmeDnsAzureClient(acme_config_manager.config)
#     results: [RotationResult] = client.issue_certificates()

#     # Validate
#     cert_versions = list(
#         azure_key_vault_manager.list_properties_of_certificate_versions(
#             name=key_vault_cert_name
#         )
#     )
#     assert len(cert_versions) is 1
#     cert = get_latest_properties_of_certificate_versions(cert_versions)
#     assert cert.enabled
#     assert (
#         cert.expires_on
#         >= datetime.now(timezone.utc) + timedelta(days=89)
#         <= datetime.now(timezone.utc) + timedelta(days=91)
#     )
#     for result in results:
#         assert result.result == CertbotResult.CREATED


##CREATE
# implement/use TODO --renew-with-new-domains


##Skip
