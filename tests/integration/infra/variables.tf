variable "location" {
  type        = string
  default     = "westeurope"
  description = "The Azure location for the deployment."
}

variable "resource_group_name" {
  type = string
}

variable "dns_zone" {
  type = object({
    name                = string
    resource_group_name = string
  })
}

variable "key_vault_name" {
  type = string
}

variable "azuread_application_display_name" {
  type = string
}

variable "key_size" {
  type = number
}