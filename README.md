# Introduction

This repository aims to leverage the automatic renewal of SSL certficates within Azure Cloud in a secure manner.

A wrapper library is provided to automatically renew certifactes based on the [ACME DNS-01 challenge](https://letsencrypt.org/docs/challenge-types/#:~:text=all%20of%20them.-,DNS%2D01%20challenge,-This%20challenge%20asks) by using [certbot](https://certbot.eff.org/).

The library supports the usage of best practices for securely handling certificates by:

- using certbot
- removing the need of a file system for storing certificates
- Azure Key Vault for central and only storage of secrets and certificates
- enabling easy and flexible automation

# Installing acme-dns-azure

acme-dns-azure is available on PyPi:

```bash
python -m pip install acme-dns-azure
```

For usage exampless please refer to [examples](examples)

## Scope

Based on the provided configuration and trigger, the wrapper library supports following flow.

![architecture](https://github.com/ZEISS/acme-dns-azure/blob/main/docs/architecture_concept.png?raw=true)

1. Receive certificates, receive EAB & ACME credentials (if configured), receive ACME account information (if already present) from KeyVault. Resolve DNS and setup certbot related configuration.
2. Certbot: Init renewal process to certificate authority
3. Certbot: DNS Challenge - create TXT record
4. Certbot: Renew certificates
5. Certbot: DNS Challenge - delete TXT record
6. Upload renewed certificates, create/update ACME account information as secret within KeyVault.

Note: When using [DNS delegation](https://docs.certbot-dns-azure.co.uk/en/latest/#:~:text=management.microsoftazure.de/-,DNS%20delegation,%C2%B6,-DNS%20delegation%2C%20also) step _3._ and _5._ differ as the TXT record won´t be deleted.

### Features

The library handles following use cases:

- Create new certificates
- Update domain references in existing certificates
- Renew existing certificates

Auth is possible by using:

- Service Principal
- User Assigned Identity

### Integration

The library can be used by:

- running as script
- Python package within your app

Within [examples](examples) you can find example implementations for running the python package:

- Azure function
- Container

![usage](https://github.com/ZEISS/acme-dns-azure/blob/main/docs/wrapper_usage.png?raw=true)

# Contribute

Fork, then clone the repo:

```bash
git clone https://github.com/ZEISS/acme-dns-azure
```

Install Poetry if you not have it already:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Configure the virtual environment with full example support and activate it:

## Install dependencies

```bash
poetry install --all-extras
source .venv/bin/activate
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

## Run integration tests

See [How to run integration tests](tests/integration/README.md)

## Release

For releasing a new version, create a PR with one of following labels:

- minor
- major
- patch
- prepatch
- preminor
- premajor
- prerelease

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

The other placeholders are specified separately.

See [examples](examples/README.md) for configuration examples.

```yml
# Azure credentials choice section. Only one of the following flags should be set to true to indicate which credentials to use. Otherwise an exception would be raised by the validator. 
# These values are translated into ini file as specified here: https://docs.certbot-dns-azure.co.uk/en/latest/index.html#certbot-azure-workload-identity-ini
# If no flag is provided the program will try to use sp_client_* values to use service principal credentials first. If those are not both present it will try to use managed_identity_id.
[use_system_assigned_identity_credentials: <boolean>]
[use_azure_cli_credentials: <boolean>]
[use_workload_identity_credentials: <boolean>]
[use_managed_identity_credentials: <boolean>]
[use_provided_service_principal_credentials: <boolean>]

# Client ID of managed identity. Must be provided if use_managed_identity_credentials is true. Will be used even if all use_*_credentials flags are set to false, but only if sp_client_* values are not all provided.
[managed_identity_id: <string>]

# sp_client_* values must be provided if use_provided_service_principal_credentials is true. Will be used even if all use_*_credentials flags are set to false. User must specify id and either secret or certificate path. If both values (id and pwd/cert path) are provided and none of the flags is set to true it has precedence over the use of provided managed_identity_id.
[sp_client_id: <string>]
[sp_client_secret: <secret>]
[sp_certificate_path: <string>]
# End of Azure credentials choice section.

[azure_environment: <string> | default = "AzurePublicCloud"]

# Flag if existing certificates containing multiple domains should be renewed and updated based on the definition of the config file. If not set, mismatching certificates will be skipped.
[update_cert_domains: <boolean> | default = False]

# key vault uri for renewal of certifcate
key_vault_id : <string>

# ACME Certificate Authority
server : <string>

# Secret name within key vault for storing ACME Certificate authority account information
[keyvault_account_secret_name: <regex> | default "acme-account-$(network location of server)"]
# when server=https://example.com/something, then keyvault_account_secret_name="acme-account-example-com"

# config file content for certbot client
[certbot.ini : <string> | default = ""]
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
  [kid_secret_name : <string> | default="acme-eab-kid"]
  [hmac_key_secret_name : <secret> default="acme-eab-hmac-key"]
```

```yml
certificates:
  - <certificate>
```

### `<certificate>`

```yml
# Certbot certficate name. The name will also be used for Azure keyvault certificate name.
name: <string>
# Azure dns zone resource ID used for ACME DNS01 challenge
dns_zone_resource_id: <string>
# renewal in days before expiry for certificate to be renewed. Default is 30
[renew_before_expiry: <int>]
domains:
  - <domain>
```

### `<domain>`

```yml
# domain name this certificate is valid for. Wildcard supported.
name: <string>
# Azure dns zone resource ID used for ACME DNS01 challenge
[dns_zone_resource_id: <string>]
```

## Manual running the library

For running the module as script 'sp_client_id' and 'sp_client_secret' are required. 'managed_identity_id' is not supported.

```bash
# from config file
python acme_dns_azure/client.py --config-file-path $CONFIG_File_PATH
# from env
python acme_dns_azure/client.py --config-env-var $ENV_VAR_NAME_CONTAINING_CONFIG
```

## Permission Handling

Best follow [security recommendations from Azure](https://docs.certbot-dns-azure.co.uk/en/latest/#:~:text=Example%3A%20Delegation%20%2B%20more,%C2%B6).

When working with shared DNS Zones, one can work with DNS delegation with limited permissions:

Example:

| Record | Name                         | Value                  | Permission           |
| ------ | ---------------------------- | ---------------------- | -------------------- |
| TXT    | \_acme-dedicated             | -                      | DNS Zone Contributor |
| CNAME  | \_acme-challenge.mysubdomain | \_acme-dedicated.fqdn. | None                 |

The CNAME and TXT record must be created upfront to enable users to use certbot. The permissions are required on the identity triggering certbot.

With this setup, a DNS Zone owner can limit permissions and enable Users to Create/Renew certificates for their subdomain and ensuring that users cannot aquire certificates for other domains or interfer with existsing records.
