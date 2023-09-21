"""ACME DNS Azure exceptions module"""


class AcmeDnsAzureClientError(Exception):
    """
    Base Class for the Certbot DNS Azure wrapper Exception hierarchy
    """

class AuthenticationError(AcmeDnsAzureClientError):
    """
    Authentication to ... failed, likely ... mismatch
    """

class KeyVaultError(AcmeDnsAzureClientError):
    """
    Authentication to ... failed, likely ... mismatch
    """

class ConfigurationError(AcmeDnsAzureClientError):
    """
    Configuration of the Certbot DNS Azure wrapper invalid
    """