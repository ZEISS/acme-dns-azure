# Introduction

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

## Build

```bash
poetry export --without-hashes --format=requirements.txt > targets/function/requirements.txt
```

### Manual testing

Prerequisite:

- config.yaml with according configuration within "/acme_dns_azure" (Note: 'sp_client_id' and 'sp_client_secret' are required. 'managed_identity_id' is not allowed)

- Azure keyvault with required secrets

```bash
python client.py
```
