resource "azuread_application" "this" {
  display_name = var.azuread_application_display_name
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_application_password" "this" {
  application_id = azuread_application.this.id
}

resource "azuread_service_principal" "this" {
  client_id = azuread_application.this.client_id
  owners    = [data.azuread_client_config.current.object_id]
}

resource "azuread_application" "no_permission" {
  display_name = var.azuread_application_display_name
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_application_password" "no_permission" {
  application_id = azuread_application.no_permission.id
}

resource "azuread_service_principal" "no_permission" {
  client_id = azuread_application.no_permission.client_id
  owners    = [data.azuread_client_config.current.object_id]
}
