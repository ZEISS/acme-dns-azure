locals {
  owner = concat(var.azure_ad_owner, [data.azuread_client_config.current.object_id])
}
resource "azuread_application" "this" {
  display_name = var.azuread_application_display_name
  owners       = local.owner
}

resource "azuread_application_password" "this" {
  application_id = azuread_application.this.id
  # Manually setting order to ensure first deletion to fix https://github.com/hashicorp/terraform-provider-azuread/issues/661
  depends_on = [azuread_application.this]
}

resource "azuread_service_principal" "this" {
  client_id = azuread_application.this.client_id
  owners    = local.owner
}

resource "azuread_application" "no_permission" {
  display_name = var.azuread_application_display_name
  owners       = local.owner
}

resource "azuread_application_password" "no_permission" {
  application_id = azuread_application.no_permission.id
  # Manually setting order to ensure first deletion to fix https://github.com/hashicorp/terraform-provider-azuread/issues/661
  depends_on = [azuread_application.no_permission]
}

resource "azuread_service_principal" "no_permission" {
  client_id = azuread_application.no_permission.client_id
  owners    = local.owner
}
