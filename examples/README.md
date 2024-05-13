## Following find an example configuration with detailed information

```yaml
managed_identity_id: 00000000-0000-0000-0000-000000000000
server: https://acme-staging-v02.api.letsencrypt.org/directory

tenant_id: 00000000-0000-0000-0000-000000000000

key_vault_id: https://my12keyvaultdev.vault.azure.net/
keyvault_account_secret_name: my-name
eab:
  enabled: false

update_cert_domains: false

certbot.ini: |
  key-type = rsa
  rsa-key-size = 2048
  email = max.musterman@example.com
  dns-azure-propagation-seconds = 15

certificates:
  - name: tls-xyz-example-org
    dns_zone_resource_id: /subscriptions/2709c03e-5888-11ee-8c99-0242ac120002/resourceGroups/rg123-my-rg/providers/Microsoft.Network/dnszones/example.org
    domains:
      - name: xyz.example.org
      - name: zyx.example.org
        dns_zone_resource_id: /subscriptions/2709c03e-5888-11ee-8c99-0242ac120002/resourceGroups/rg123-my-rg/providers/Microsoft.Network/dnszones/my-dev.domain.com

  - name: tls-wildcard-abc-example-org
    renew_before_expiry: 40
    dns_zone_resource_id: /subscriptions/2709c03e-5888-11ee-8c99-0242ac120002/resourceGroups/rg123-my-rg/providers/Microsoft.Network/dnszones/my-dev.domain.com
    domains:
      - name: "*.abc.example.org"
```

This configuration will create following certbot config files:

```yaml
#certbot.ini
key-type = rsa
rsa-key-size = 2048
email = max.musterman@example.com
dns-azure-propagation-seconds = 15
config-dir = /tmp/acme_dns_azure$RANDOM_STRING/config
work-dir = /tmp/acme_dns_azure$RANDOM_STRING/work
logs-dir = /tmp/acme_dns_azure$RANDOM_STRING/logs
preferred-challenges = dns
authenticator = dns-azure
agree-tos = true
server = https://acme-staging-v02.api.letsencrypt.org/directory
```

```yaml
#certbot_dns_azure.ini
dns_azure_msi_client_id = 00000000-0000-0000-0000-000000000000
dns_azure_tenant_id = 00000000-0000-0000-0000-000000000000
dns_azure_environment = AzurePublicCloud
dns_azure_zone1 = xyz.example.org:/subscriptions/2709c03e-5888-11ee-8c99-0242ac120002/resourceGroups/rg123-my-rg/providers/Microsoft.Network/dnszones/example.org
dns_azure_zone2 = zyx.example.org:/subscriptions/2709c03e-5888-11ee-8c99-0242ac120002/resourceGroups/rg123-my-rg/providers/Microsoft.Network/dnszones/my-dev.domain.com
dns_azure_zone3 = abc.example.org:/subscriptions/2709c03e-5888-11ee-8c99-0242ac120002/resourceGroups/rg123-my-rg/providers/Microsoft.Network/dnszones/my-dev.domain.com
```

The library will:

- create temporary dir _/tmp/acme_dns_azure$RANDOM_STRING_
- Receive secret _my-name_ from keyvault containing Certificate Provider Account informataion. If not present yet, this secret will be created after renewal actions have been finished.
- attempt to create (or renew if already existing) key vault certificates _tls-xyz-example-org_ and _tls-wildcard-abc-example-org_
- renew certificate _tls-xyz-example-org_ 30 days before expiry (default value)
- renew certificate _tls-wildcard-abc-example-org_ 40 days before expiry
- create/renew certificates for a valid period of 90 days
- since **update_cert_domains** is _false_: Every certificate already existing within the keyvault, but containing different subject alternative names as specified within the config file, will be skipped.
