provider "azurerm" {
  resource_provider_registrations = "none"
  subscription_id                 = var.subscription_id

  features {
    key_vault {
      purge_soft_delete_on_destroy               = true
      purge_soft_deleted_certificates_on_destroy = true
      purge_soft_deleted_keys_on_destroy         = true
      purge_soft_deleted_secrets_on_destroy      = true
    }

    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

provider "azurerm" {
  resource_provider_registrations = "none"
  alias                           = "dns_zone"
  subscription_id                 = var.dns_zone.subscription_id

  features {}
}

provider "azuread" {}
