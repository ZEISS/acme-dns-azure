data "azurerm_dns_zone" "this" {
  provider            = azurerm.dns_zone
  name                = var.dns_zone.name
  resource_group_name = var.dns_zone.resource_group_name
}

resource "azurerm_role_assignment" "dns_contributor" {
  scope                = data.azurerm_dns_zone.this.id
  role_definition_name = "DNS Zone Contributor"
  principal_id         = azuread_service_principal.this.object_id
}
