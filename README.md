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

```bash
cd acme-dns-azure
poetry install --all-extras
source .venv/bin/activate
poetry export --without-hashes --format=requirements.txt > targets/function/requirements.txt
```

[Install Azure Function Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=v4%2Clinux%2Cpython%2Cportal%2Cbash#install-the-azure-functions-core-tools) for local development:

```bash
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list'
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4
```

Azurite:

```bash
docker run --rm -d --name azurite-acme-dns-azure \
  -p 10000:10000 -p 10001:10001 -p 10002:10002 \
  mcr.microsoft.com/azure-storage/azurite
```

Make sure the tests pass:

```bash
tox -e py
```

## Test

```bash
# unit test
pytest
# specific target
pytest acme_dns_azure/tests/targets/test_foo.py
```
