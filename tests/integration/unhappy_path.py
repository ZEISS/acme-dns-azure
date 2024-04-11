from datetime import datetime, timezone
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


def test_automatic_renewal_for_existing_cert_multiple_domains_skipped(
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
        san_dns_names=[domain_name1],
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
        assert result.result == CertbotResult.SKIPPED
    cn, san = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name
    )
    assert cn == f"CN={domain_name1}"
    assert san == [domain_name1]


def test_automatic_renewal_for_existing_cert_multiple_domains_overwritten(
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
    acme_config_manager.set_config_param("update_cert_domains", True)
    azure_key_vault_manager.create_certificate(
        name=key_vault_cert_name,
        subject=f"CN={domain_name1}",
        validity_in_months=cert_validity_in_month,
        san_dns_names=[domain_name1],
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


def test_create_cert_for_dns_delegation_dedicated_txt_with_minimum_permission_success(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    azure_ad_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
    principal_id,
):
    ## Config
    domain_name = resource_name + "." + dns_zone_name
    key_vault_cert_name = domain_name.replace(".", "")

    ## Init
    config_file_path = config_file_path.replace(
        "config.yaml", "no_permission_config.yaml"
    )
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + resource_name, value="_dedicated." + domain_name + "."
    )
    txt_rrset_id = azure_dns_zone_manager.create_txt_record(
        name="_dedicated." + resource_name, value="-"
    )
    azure_ad_manager.create_role_assignment(
        scope=txt_rrset_id,
        principal_id=principal_id,
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[DnsZoneDomainReference(name=domain_name)],
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


def test_create_cert_for_dns_delegation_dedicated_txt_without_minimum_permission_failure(
    acme_config_manager,
    azure_dns_zone_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
):
    ## Config
    domain_name = resource_name + "." + dns_zone_name
    key_vault_cert_name = domain_name.replace(".", "")

    ## Init
    config_file_path = config_file_path.replace(
        "config.yaml", "no_permission_config.yaml"
    )
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + resource_name, value="_dedicated." + domain_name + "."
    )
    _ = azure_dns_zone_manager.create_txt_record(
        name="_dedicated." + resource_name, value="-"
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[DnsZoneDomainReference(name=domain_name)],
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

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
    dns_zone_name,
    principal_id,
):
    ## Config
    domain_name1 = resource_name + "1." + dns_zone_name
    domain_name2 = resource_name + "2." + dns_zone_name
    key_vault_cert_name = domain_name1.replace(".", "")

    ## Init
    config_file_path = config_file_path.replace(
        "config.yaml", "no_permission_config.yaml"
    )
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + resource_name + "1",
        value="_shared." + resource_name + "." + dns_zone_name + ".",
    )
    azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + resource_name + "2",
        value="_shared." + resource_name + "." + dns_zone_name + ".",
    )
    txt_rrset_id = azure_dns_zone_manager.create_txt_record(
        name="_shared." + resource_name, value="-"
    )
    azure_ad_manager.create_role_assignment(
        scope=txt_rrset_id,
        principal_id=principal_id,
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name,
        domain_references=[
            DnsZoneDomainReference(name=domain_name1),
            DnsZoneDomainReference(name=domain_name2),
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
    assert cn == f"CN={domain_name1}"
    assert san == [domain_name1, domain_name2]


def test_create_cert_for_dns_delegation_shared_txt_single_cert_with_minimum_permission_success(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    azure_ad_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
    principal_id,
):
    ## Config
    domain_name1 = resource_name + "1." + dns_zone_name
    domain_name2 = resource_name + "2." + dns_zone_name
    key_vault_cert_name1 = domain_name1.replace(".", "")
    key_vault_cert_name2 = domain_name2.replace(".", "")

    ## Init
    config_file_path = config_file_path.replace(
        "config.yaml", "no_permission_config.yaml"
    )
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + resource_name + "1",
        value="_shared." + resource_name + "." + dns_zone_name + ".",
    )
    azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + resource_name + "2",
        value="_shared." + resource_name + "." + dns_zone_name + ".",
    )
    txt_rrset_id = azure_dns_zone_manager.create_txt_record(
        name="_shared." + resource_name, value="-"
    )
    azure_ad_manager.create_role_assignment(
        scope=txt_rrset_id,
        principal_id=principal_id,
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name1,
        domain_references=[
            DnsZoneDomainReference(name=domain_name1),
        ],
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name2,
        domain_references=[
            DnsZoneDomainReference(name=domain_name2),
        ],
    )

    ## Test
    client = AcmeDnsAzureClient(acme_config_manager.config)
    results: list[RotationResult] = client.issue_certificates()

    ## Validate
    assert results[0].result == CertbotResult.CREATED
    assert results[1].result == CertbotResult.CREATED
    cn1, san1 = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name1
    )
    cn2, san2 = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name2
    )
    assert cn1 == f"CN={domain_name1}"
    assert san1 == [domain_name1]
    assert cn2 == f"CN={domain_name2}"
    assert san2 == [domain_name2]


def test_parallel_request_dns_delegation_shared_txt_single_cert(
    acme_config_manager,
    azure_key_vault_manager,
    azure_dns_zone_manager,
    azure_ad_manager,
    config_file_path,
    resource_name,
    dns_zone_name,
    principal_id,
):
    ## Config
    domain_name1 = resource_name + "1." + dns_zone_name
    key_vault_cert_name1 = domain_name1.replace(".", "")
    key_vault_cert_name2 = domain_name1.replace(".", "").replace("1", "2")

    ## Init
    config_file_path = config_file_path.replace(
        "config.yaml", "no_permission_config.yaml"
    )
    acme_config_manager.base_config_from_file(file_path=config_file_path)
    azure_dns_zone_manager.create_cname_record(
        name="_acme-challenge." + resource_name + "1",
        value="_shared." + resource_name + "." + dns_zone_name + ".",
    )

    txt_rrset_id = azure_dns_zone_manager.create_txt_record(
        name="_shared." + resource_name, value="-"
    )
    azure_ad_manager.create_role_assignment(
        scope=txt_rrset_id,
        principal_id=principal_id,
    )
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name1,
        domain_references=[
            DnsZoneDomainReference(name=domain_name1),
        ],
    )

    client1 = AcmeDnsAzureClient(acme_config_manager.config)

    acme_config_manager.base_config_from_file(file_path=config_file_path)
    acme_config_manager.add_certificate_to_config(
        cert_name=key_vault_cert_name2,
        domain_references=[
            DnsZoneDomainReference(name=domain_name1),
        ],
    )
    client2 = AcmeDnsAzureClient(acme_config_manager.config)

    ## Test
    from multiprocessing.pool import ThreadPool

    pool1 = ThreadPool(processes=1)
    pool2 = ThreadPool(processes=1)

    async_result1 = pool1.apply_async(client1.issue_certificates)
    async_result2 = pool2.apply_async(client2.issue_certificates)

    results1: list[RotationResult] = async_result1.get()
    results2: list[RotationResult] = async_result2.get()

    ## Validate
    assert results1[0].result == CertbotResult.CREATED
    assert results2[0].result == CertbotResult.CREATED
    cn1, san1 = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name1
    )
    cn2, san2 = azure_key_vault_manager.get_cn_and_san_from_certificate(
        key_vault_cert_name2
    )
    assert cn1 == f"CN={domain_name1}"
    assert san1 == [domain_name1]
    assert cn2 == f"CN={domain_name1}"
    assert san2 == [domain_name1]
