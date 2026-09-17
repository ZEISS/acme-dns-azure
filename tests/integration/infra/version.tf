terraform {
  required_version = "~> 1.15"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.5"
    }

    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.9"
    }

    local = {
      source  = "hashicorp/local"
      version = "~> 2.9"
    }
  }
}
