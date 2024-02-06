import logging
from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.dns.models import RecordSet, TxtRecord, CnameRecord
from azure.identity import DefaultAzureCredential
from dataclasses import dataclass


@dataclass
class DnsZoneDomainReference:
    dns_zone_resource_id: str
    name: str


class AzureDnsZoneManager:
    def __init__(self, subscription_id, resource_group_name, zone_name):
        self._resource_group_name = resource_group_name
        self._zone_name = zone_name
        self._client = DnsManagementClient(DefaultAzureCredential(), subscription_id)
        self._created_record_sets: [RecordSet] = []

    def clean_up_all_resources(self):
        for record in self._created_record_sets:
            logging.info("Deleting record %s...", record.name)
            try:
                self._client.record_sets.delete(
                    resource_group_name=self._resource_group_name,
                    zone_name=self._zone_name,
                    relative_record_set_name=record.name,
                    record_type=record.type.rsplit("/", 1)[
                        1
                    ],  #'Microsoft.Network/dnszones/CNAME' not accepted
                )
            except Exception:
                logging.exception("Please manually delete record %s", record)

    def create_cname_record(
        self, name, value: str = None, ttl: int = 3600
    ) -> DnsZoneDomainReference:
        logging.info("Creating record %s", name)
        record_set: RecordSet = self._client.record_sets.create_or_update(
            resource_group_name=self._resource_group_name,
            zone_name=self._zone_name,
            relative_record_set_name=name,
            record_type="CNAME",
            parameters={"ttl": ttl, "cname_record": CnameRecord(cname=value)},
        )
        self._created_record_sets.append(record_set)
        logging.info("Created record %s", record_set)
        return DnsZoneDomainReference(
            dns_zone_resource_id=record_set.id, name=record_set.fqdn[:-1]
        )

    def create_txt_record(
        self, name, value: str = None, ttl: int = 3600
    ) -> DnsZoneDomainReference:
        logging.info("Creating record %s", name)
        record_set: RecordSet = self._client.record_sets.create_or_update(
            resource_group_name=self._resource_group_name,
            zone_name=self._zone_name,
            relative_record_set_name=name,
            record_type="TXT",
            parameters={"ttl": ttl, "txt_records": [TxtRecord(value=[value])]},
        )
        self._created_record_sets.append(record_set)
        logging.info("Created record %s", record_set)
        return DnsZoneDomainReference(
            dns_zone_resource_id=record_set.id, name=record_set.fqdn[:-1]
        )
