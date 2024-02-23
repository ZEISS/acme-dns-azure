"""ACME DNS Azure exceptions module"""


class AcmeDnsAzureClientError(Exception):
    """
    Base Class for the Certbot DNS Azure wrapper Exception hierarchy
    """


class KeyVaultError(AcmeDnsAzureClientError):
    """
    Keyvault interaction failed
    """


class ConfigurationError(AcmeDnsAzureClientError):
    """
    Configuration of the Certbot DNS Azure wrapper invalid
    """
