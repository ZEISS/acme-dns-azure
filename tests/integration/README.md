## Run integration test

1. Init base infrastructure

````bash
terraform -chdir="infra" init
terraform -chdir="infra" apply -var-file=./default.tfvars
```

2. Run integration test

```bash
params=$(terraform -chdir="infra" output -json | jq -r .integration_test_params.value)
pytest happy_path.py $params -s -v --log-cli-level=DEBUG
````
