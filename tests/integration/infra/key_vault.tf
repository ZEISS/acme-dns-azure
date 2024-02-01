resource "azurerm_key_vault" "this" {
  name                          = var.key_vault_name
  location                      = azurerm_resource_group.this.location
  resource_group_name           = azurerm_resource_group.this.name
  enabled_for_disk_encryption   = true
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  purge_protection_enabled      = false
  public_network_access_enabled = true

  sku_name = "standard"

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id
    certificate_permissions = [
      "Create",
      "Delete",
      "Get",
      "Import",
      "List",
      "Recover",
      "Update",
      "Purge",
    ]
    key_permissions = [
      "Create",
      "Delete",
      "Get",
      "Import",
      "List",
      "Recover",
      "Update",
    ]
    secret_permissions = [
      "Delete",
      "Get",
      "List",
      "Recover",
      "Set",
      "Purge",
      "Backup",
      "Restore",
    ]
  }
  access_policy {
    tenant_id      = data.azurerm_client_config.current.tenant_id
    object_id      = azuread_service_principal.this.object_id
    application_id = azuread_application.this.client_id
    certificate_permissions = [
      "Create",
      "Delete",
      "Get",
      "Import",
      "List",
      "Recover",
      "Update",
    ]
    key_permissions = [
      "Create",
      "Delete",
      "Get",
      "Import",
      "List",
      "Recover",
      "Update",
    ]
    secret_permissions = [
      "Delete",
      "Get",
      "List",
      "Recover",
      "Set",
    ]
  }
  lifecycle {
    ignore_changes = [tags]
  }
}
