from dataclasses import dataclass
from enum import Enum
from typing import List


@dataclass
class DomainReference:
    """Dataclass holding Domain name - DNS zone record resource ID reference.

    params:
    dns_zone_resource_id -- resource ID of DNS Zone record
    domain_name -- domain name
    """

    dns_zone_resource_id: str
    domain_name: str


@dataclass
class RotationCertificate:
    """Dataclass holding certificate rotation information.

    params:
    key_vault_cert_name -- Name of keyvault certificate to be created/updated
    certbot_cert_name -- Certificate name of certbot
    domains -- Domain references of this certificate
    renew_before_expiry -- Number in days before expiration when this certificate will be renewed.
    """

    key_vault_cert_name: str
    certbot_cert_name: str
    domains: List[DomainReference]
    renew_before_expiry: int = None


class CertbotResult(Enum):
    """Certbot renewal result."""

    CREATED = 1
    """
    New certificate has been created.
    """
    RENEWED = 2
    """
    Existing certificate has been renewed.
    """
    STILL_VALID = 3
    """
    Existing certificate is still valid. No action taken.
    """
    FAILED = 4
    """
    Certbot creation or renewal of certificate has failed.
    """
    SKIPPED = 5
    """
    Existing certificate has been skipped due to mismatch of domain information of provided config.
    """


@dataclass
class RotationResult:
    """Dataclass holding certificate rotation result information.

    params:
    certificate -- Rotation certificate reference
    result -- Result of rotation action
    message -- Message with additional information to result
    """

    certificate: RotationCertificate
    result: CertbotResult
    message: str = None
