from strictyaml import Map, Str, Seq, Bool, Optional, Regex

schema = Map(
    {
        Optional("managed_identity_id"): Regex(
            r"^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$"
        ),
        # TODO regex
        Optional("azure_environment", default="AzurePublicCloud"): Str(),
        Optional("sp_client_id"): Str(),
        Optional("sp_client_secret"): Str(),
        "server": Str(),
        "tenant_id": Str(),
        # TODO 'server': Regex(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)'),
        "email": Regex(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
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
                    "domains": Seq(
                        Map(
                            {
                                "name": Regex(
                                    r"(?=^.{4,253}$)(^((?!-)[*a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)"
                                ),
                                "dns_zone_resource_id": Str(),
                            }
                        )
                    ),
                }
            )
        ),
    }
)
