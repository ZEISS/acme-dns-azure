"""Certbot DNS Azure wrapper exceptions module"""


class CertbotDNSAzureWrapperError(Exception):
    """
    Base Class for the Certbot DNS Azure wrapper Exception hierarchy
    """


class AuthenticationError(CertbotDNSAzureWrapperError):
    """
    Authentication to ... failed, likely ... mismatch
    """


class ConfigurationError(CertbotDNSAzureWrapperError):
    """
    Configuration of the Certbot DNS Azure wrapper invalid
    """