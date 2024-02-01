# Integration test

For integration test one must first set up the base infrastructure, which will be reused my all integration tests. This base infrastructure includes:

- azure key vault
- Service Principal
- DNS Zone reference with required role assignments

The actual test run will:

- create&delete DNS record set entries within this DNS zone
- create&delete Certificates and secrets within the Key Vault

## Run integration test

1. Init base infrastructure

````bash
terraform -chdir="infra" init
# define variable file or overwrite with according information, e.g. -var azuread_application_display_name="my-name"
terraform -chdir="infra" apply -var-file=./default.tfvars
```

2. Run integration test

```bash
params=$(terraform -chdir="infra" output -json | jq -r .integration_test_params.value)
pytest happy_path.py $params -s -v --log-cli-level=INFO
````

3. Teardown base infrastructure

````bash
terraform -chdir="infra" destroy
```
````
