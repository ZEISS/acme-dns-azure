provider "azurerm" {
  skip_provider_registration = true
  subscription_id            = var.subscription_id
  features {
    key_vault {
      purge_soft_delete_on_destroy               = true
      purge_soft_deleted_certificates_on_destroy = true
      purge_soft_deleted_keys_on_destroy         = true
      purge_soft_deleted_secrets_on_destroy      = true
    }
  }
}

provider "azurerm" {
  skip_provider_registration = true
  alias                      = "dns_zone"
  subscription_id            = var.dns_zone.subscription_id
  features {
  }
}
