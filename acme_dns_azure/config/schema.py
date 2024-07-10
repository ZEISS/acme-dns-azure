from strictyaml import Map, Str, Seq, Bool, Optional, Regex, Int

schema = Map(
    {
        # Azure identity choice section. Choose credentials to be used to interact with Azure, we only accept one value to be true from this set, for reference see: https://docs.certbot-dns-azure.co.uk/en/latest/index.html#certbot-azure-workload-identity-ini
        Optional("use_system_assigned_identity_credentials"): Bool(),
        Optional("use_azure_cli_credentials"): Bool(),
        Optional("use_workload_identity_credentials"): Bool(),
        # added to support validation logic when choosing credentials to be used
        Optional("use_managed_identity_credentials"): Bool(),
        # added to support validation logic when choosing credentials to be used
        Optional("use_provided_service_principal_credentials"): Bool(),
        # managed_identity_id must be provided if use_managed_identity_credentials is true
        Optional("managed_identity_id"): Regex(
            r"^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$"
        ),
        # sp_client* values must be provided if use_provided_service_principal_credentials is true, user can provide password or certificate path
        Optional("sp_client_id"): Str(),
        Optional("sp_client_secret"): Str(),
        Optional("sp_certificate_path"): Str(),
        # End of Azure identity choice section
        Optional("azure_environment", default="AzurePublicCloud"): Regex(
            "AzurePublicCloud|AzureUSGovernmentCloud|AzureChinaCloud|AzureGermanCloud"
        ),
        "tenant_id": Regex(
            r"^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$"
        ),
        Optional("update_cert_domains", default=False): Bool(),
        "server": Regex(
            r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
        ),
        "key_vault_id": Regex(r"^https://[-a-zA-Z0-9]{3,24}\.vault\.azure\.net/$"),
        Optional("keyvault_account_secret_name", default=""): Regex(
            "^[-a-zA-Z0-9]{1,127}$|"
        ),  # optional / default: acme-account-${acme_server} #if non-existing or empty, certbot register will be executed, account directory will be stored as base64 tar.gz file
        Optional("eab", default={"enabled": False}): Map(
            {
                Optional("enabled", default=False): Bool(),
                Optional("kid_secret_name", default="acme-eab-kid"): Regex(
                    "^[-a-zA-Z0-9]{1,127}$"
                ),  # must be created upfront with information from CIT
                Optional("hmac_key_secret_name", default="acme-eab-hmac-key"): Regex(
                    "^[-a-zA-Z0-9]{1,127}$"
                ),  # must be created upfront with information from CIT
            }
        ),
        Optional("certbot.ini", default=""): Str(),
        "certificates": Seq(
            Map(
                {
                    "name": Regex("^[-a-zA-Z0-9]{1,127}$"),
                    "dns_zone_resource_id": Str(),
                    Optional("renew_before_expiry"): Int(),
                    "domains": Seq(
                        Map(
                            {
                                # TODO: Check regex Regex(r"(?=^.{4,253}$)(^((?!-)[*a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)")
                                "name": Str(),
                                Optional("dns_zone_resource_id", default=""): Str(),
                            }
                        )
                    ),
                }
            )
        ),
    }
)
