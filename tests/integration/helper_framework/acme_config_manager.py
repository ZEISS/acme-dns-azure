import yaml
from strictyaml import load
from tests.integration.helper_framework.azure_dns_zone_manager import (
    DnsZoneDomainReference,
)


class AcmeConfigManager:
    def __init__(self):
        self._config = ""

    def base_config_from_file(self, file_path):
        with open(file_path, "r") as file:
            self._config = load(file.read()).data

    def add_certificate_to_config(
        self,
        cert_name,
        domain_references: [DnsZoneDomainReference],
        renew_before_expiry: int = None,
    ):
        if self._config == "":
            raise Exception("Base config not loaded!")
        if "certificates" not in self._config:
            self._config["certificates"] = []

        domains = []
        for domain in domain_references:
            domains.append(
                {
                    "dns_zone_resource_id": domain.dns_zone_resource_id,
                    "name": domain.name,
                }
            )
        config_cert = {"name": cert_name, "domains": domains}
        if renew_before_expiry is not None:
            config_cert["renew_before_expiry"] = renew_before_expiry

        self._config["certificates"].append(config_cert)

    @property
    def config(self):
        return yaml.dump(self._config)