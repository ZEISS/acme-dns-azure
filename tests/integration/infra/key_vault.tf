resource "azurerm_key_vault" "this" {
  name                          = var.key_vault_name
  location                      = azurerm_resource_group.this.location
  resource_group_name           = azurerm_resource_group.this.name
  enabled_for_disk_encryption   = true
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  purge_protection_enabled      = false
  public_network_access_enabled = true
  soft_delete_retention_days    = 7

  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_role_assignment" "key_vault_current_principal" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_role_assignment" "key_vault_certificates" {
  scope                            = azurerm_key_vault.this.id
  role_definition_name             = "Key Vault Certificates Officer"
  principal_id                     = azuread_service_principal.this.object_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "key_vault_secrets" {
  scope                            = azurerm_key_vault.this.id
  role_definition_name             = "Key Vault Secrets Officer"
  principal_id                     = azuread_service_principal.this.object_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
