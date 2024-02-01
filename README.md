# Introduction

TODO

# Contribute

Fork, then clone the repo:

```bash
git clone https://github.com/ZEISS/acme-dns-azure
```

Install Poetry if you not have it already:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Configure the virtual environment with full targets support and activate it:

## Install dependencies

```bash
source .venv/bin/activate
poetry install --all-extras
```

## Lint

```bash
poetry run black .
```

## Run unit tests

```bash
poetry run coverage run
poetry run coverage report
```

## Integration test

See [tests/integration](tests/integration/README.md)

# Usage

## Config

The config is written in [YAML format](http://en.wikipedia.org/wiki/YAML), defined by the scheme described below.
Brackets indicate that a parameter is optional.
For non-list parameters the value is set to the specified default.

Generic placeholders are defined as follows:

- `<boolean>`: a boolean that can take the values `true` or `false`
- `<int>`: a regular integer
- `<string>`: a regular string
- `<secret>`: a regular string that is a secret, such as a password
- `<regex>`: a regular expression

The other placeholders are specified separately.

See [example](example/config.yaml) for configuration examples.

```yml
[managed_identity_id: <string>]

[sp_client_id: <string>]
[sp_client_secret: <secret>]

[azure_environment: <regex> | default = "AzurePublicCloud"]

# key vault uri for renewal of certifcate
key_vault_id : <regex>

# ACME Certificate Authority
server : <regex>

# Secret name within key vault for storing ACME Certificate authority account information
[keyvault_account_secret_name: <regex> | default "acme-account-$(network location of server)"]
# when server=https://example.com/something, then keyvault_account_secret_name="acme-account-example-com"

# config file content for certbot client
[certbot.ini : <string> | default = ""]
#
```

NOTE: Either **managed_identity_id** or **sp_client_id** and **sp_client_secret** must be specified.

NOTE: **certbot.ini** represents the [CERTBOT configuration file](https://eff-certbot.readthedocs.io/en/latest/using.html#configuration-file) and will be passed into certbot by the _acme_dns_azure_ library as defined. Misconfiguration will lead to failures of certbot and therefore of the renewal process.

Following values will be added to the configurataion file by the _acme_dns_azure_ library per default:

```yml
preferred-challenges: dns
authenticator: dns-azure
agree-tos: true
```

### `[<eab>]`

```yml

  # External account binding configuration for ACME, with key ID and base64encoded HMAC key
  [enabled: <boolean> |  default = false]
  [kid_secret_name : <regex> | default="acme-eab-kid"]
  [hmac_key_secret_name : <secret> default="acme-eab-hmac-key"]
```

```yml
certificates:
  - <certificate>
```

### `<certificate>`

```yml
# name of key vault certificate
name: <regex>
# renewal in days before expiry for certificate to be renewed
[renew_before_expiry: <int>]
domains:
  - <domain>
```

### `<domain>`

```yml
# domain name this certificate is valid for. Wildcard supported.
name: <regex>
# Azure resource ID to according record set within DNS Zone
dns_zone_resource_id: <string>
```

## Manual running the library

For local testing 'sp_client_id' and 'sp_client_secret' are required. 'managed_identity_id' is not supported.

```bash
touch config.yaml
# define configuration as described above
python acme_dns_azure/client.py
```
