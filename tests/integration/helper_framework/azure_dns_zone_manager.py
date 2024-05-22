import logging
import time
from dataclasses import dataclass

from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.dns.models import RecordSet, TxtRecord, CnameRecord
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceNotFoundError
from acme_dns_azure.dns_validation import DNSChallenge

@dataclass
class DnsZoneDomainReference:
    name: str
    dns_zone_resource_id: str = None


class AzureDnsZoneManager:
    def __init__(self, subscription_id, resource_group_name, zone_name):
        self._resource_group_name = resource_group_name
        self._zone_name = zone_name
        self._client = DnsManagementClient(DefaultAzureCredential(), subscription_id)
        self._created_record_sets: list[RecordSet] = []
        self._additonal_records: list[str] = []

    def clean_up_all_resources(self):
        for record in self._created_record_sets:
            logging.info("Deleting record %s...", record.name)
            try:
                self._delete_record(
                    name=record.name,
                    record_type=record.type.rsplit("/", 1)[
                        1
                    ],  #'Microsoft.Network/dnszones/CNAME' not accepted
                )
            except Exception:
                logging.exception("Please manually delete record %s", record)
        for name in self._additonal_records:
            try:
                self._delete_record(name=name)
            except Exception:
                logging.exception("Please manually delete record %s", name)

    def record_exists(self, name: str, record_type: str = "TXT"):
        try:
            self._client.record_sets.get(
                resource_group_name=self._resource_group_name,
                zone_name=self._zone_name,
                relative_record_set_name=name,
                record_type=record_type,
            )
            return True
        except ResourceNotFoundError:
            return False

    def _delete_record(self, name: str, record_type: str = "TXT"):
        self._client.record_sets.delete(
            resource_group_name=self._resource_group_name,
            zone_name=self._zone_name,
            relative_record_set_name=name,
            record_type=record_type,
        )

    def delete_addtional_txt_record_when_cleanup(self, name):
        self._additonal_records.append(name)

    def create_cname_record(self, name, value, ttl: int = 120) -> None:
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
        self._wait_until_record_is_propagated(name, "CNAME", value)

    def create_txt_record(self, name, value: str = None, ttl: int = 120) -> str:
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
        self._wait_until_record_is_propagated(name, "TXT", value)
        return record_set.id

    def _wait_until_record_is_propagated(self, name: str, type: str, value: str) -> bool:
        t_end = time.time() + 60
        dns = DNSChallenge()
        while time.time() < t_end:
            zone = dns._zone_for_name(name)
            nameservers = dns._nameservers(zone)
            record_set = dns._resolve(name, type, nameservers)
            if record_set:
                for value in record_set:
                    if value.to_text().strip("'\"") == value:
                        logging.info("Propagated record %s", record_set.qname.to_text(True))
                        return True
            time.sleep(1)
        return False
