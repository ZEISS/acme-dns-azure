## Running library within a container

Following find a base setup to run _acme-dns-azure_ within a container.

The _package_ uses [DefaultAzureCredential](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme?view=azure-python) for authentication. Please refer to related documentation about the available options to provide credentials.
Following find a simple example using Service Principal secrets.

The image can also be pulled from [GitHub registry](https://github.com/ZEISS/acme-dns-azure/pkgs/container/acme-dns-azure)

```bash
docker build .
docker run -e ACME_DNS_CONFIG={BASE64_ENCODED_ACME_CONFIG} -e AZURE_CLIENT_ID={AZURE_CLIENT_ID}  -e AZURE_CLIENT_SECRET={AZURE_CLIENT_SECRET} -e AZURE_TENANT_ID={AZURE_TENANT_ID}  {IMAGE_ID}
```
