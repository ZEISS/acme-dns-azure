# Integration test

For integration test one must first set up the base infrastructure, which will be reused by all integration tests. This base infrastructure includes:

- azure key vault
- Service Principal
- DNS Zone reference with required role assignments

The actual test run will:

- create&delete DNS record set entries within this DNS zone
- create&delete Certificates and secrets within the Key Vault
- create&delete role assignments on temporarly created DNS Zone entries

Required permissions:

- Contributor

As the DNS Zone is part of a seperate subscription, additonally permissions on DNS Zone level are required:
- DNS Zone Contributor
- Role Based Access Control Administrator

## Run integration test

1. Init base infrastructure

```bash
cd "tests/integration"
terraform -chdir="infra" init

# Create and define terraform variables
cp "./infra/terraform.tfvars.example" "./infra/terraform.tfvars"

terraform -chdir="infra" apply
```

2. Run integration test

```bash
pytest --help
# check 'Custom options' section for input values
```

```bash
params=$(terraform -chdir="infra" output -json | jq -r .integration_test_params.value)
pytest happy_path.py $params  --resource-prefix pd-XX01
pytest unhappy_path.py $params  --resource-prefix pd-XX01

# increase log level
ACME_DNS_AZURE_LOG_LEVEL=INFO pytest happy_path.py $params  -s -v --log-cli-level=INFO --show-capture=log
# only run specific tests with pattern
pytest unhappy_path.py $params  -k "test_automatic_renewal_for_existing_cert_multiple_domains_overwritten"
```

3. Teardown base infrastructure

```bash
terraform -chdir="infra" destroy
```
