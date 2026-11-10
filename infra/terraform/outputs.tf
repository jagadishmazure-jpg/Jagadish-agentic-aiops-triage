output "resource_group" {
  description = "Resource group name."
  value       = azurerm_resource_group.rg.name
}

output "workspace_name" {
  description = "Azure ML workspace name."
  value       = azapi_resource.mlw.name
}

output "cluster_name" {
  description = "CPU compute cluster name."
  value       = azapi_resource.cluster.name
}

output "key_vault_name" {
  description = "Key Vault name."
  value       = azurerm_key_vault.kv.name
}
