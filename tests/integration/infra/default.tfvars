location                         = "westeurope"
resource_group_name              = "pd-fb01-acme"
key_vault_name                   = "pfb01acmetestvault"
azuread_application_display_name = "ACME integration test"
key_size                         = 4096
dns_zone = {
  name                = "hdp-cicd.zeiss.com"
  resource_group_name = "czm78-dog-dev-euw-dns"
}
