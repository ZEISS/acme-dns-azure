locals {
  happy_path_config = {
    sp_client_id     = azuread_service_principal.this.client_id
    sp_client_secret = azuread_application_password.this.value
    server           = "https://acme-staging-v02.api.letsencrypt.org/directory"
    tenant_id        = data.azurerm_client_config.current.tenant_id
    key_vault_id     = azurerm_key_vault.this.vault_uri
    eab = {
      enabled = false
    }
    "certbot.ini" = <<EOT
key-type = rsa
rsa-key-size = ${var.key_size}
break-my-certs = ${true}
email = ${var.email}
dns-azure-propagation-seconds = 10
    EOT
  }
  unhappy_path_config = {
    sp_client_id     = azuread_service_principal.no_permission.client_id
    sp_client_secret = azuread_application_password.no_permission.value
    server           = "https://acme-staging-v02.api.letsencrypt.org/directory"
    tenant_id        = data.azurerm_client_config.current.tenant_id
    key_vault_id     = azurerm_key_vault.this.vault_uri
    eab = {
      enabled = false
    }
    "certbot.ini" = <<EOT
key-type = rsa
rsa-key-size = ${var.key_size}
email = ${var.email}
# Let's Encrypt uses cached DNS (60s) during validation. Relevant for DNS delegation testing
dns-azure-propagation-seconds = 60
    EOT
  }
}

output "integration_test_params" {
  value     = "--dns-zone-name ${data.azurerm_dns_zone.this.name} --dns-zone-resource-group-name ${data.azurerm_dns_zone.this.resource_group_name} --subscription-id ${data.azurerm_subscription.current.subscription_id} --keyvault-uri ${azurerm_key_vault.this.vault_uri} --principal-id ${azuread_service_principal.no_permission.object_id}"
  sensitive = false
}

resource "local_file" "base_config" {
  content  = yamlencode(local.happy_path_config)
  filename = "config.yaml"
}

resource "local_file" "no_permission_config" {
  content  = yamlencode(local.unhappy_path_config)
  filename = "no_permission_config.yaml"
}
