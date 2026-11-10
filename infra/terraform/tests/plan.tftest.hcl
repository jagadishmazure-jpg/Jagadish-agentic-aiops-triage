# Offline plan tests: mocked providers, no Azure credentials, nothing created.
#   terraform init -backend=false && terraform test
mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = {
      tenant_id       = "00000000-0000-0000-0000-000000000001"
      subscription_id = "00000000-0000-0000-0000-000000000002"
      object_id       = "00000000-0000-0000-0000-000000000003"
    }
  }
  mock_resource "azurerm_key_vault" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000002/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/kv"
    }
  }
  mock_resource "azurerm_storage_account" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000002/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/st"
    }
  }
  mock_resource "azurerm_application_insights" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000002/resourceGroups/rg/providers/Microsoft.Insights/components/appi"
    }
  }
  mock_resource "azurerm_log_analytics_workspace" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000002/resourceGroups/rg/providers/Microsoft.OperationalInsights/workspaces/log"
    }
  }
}

mock_provider "azapi" {
  mock_resource "azapi_resource" {
    defaults = {
      id     = "/subscriptions/00000000-0000-0000-0000-000000000002/resourceGroups/rg/providers/Microsoft.MachineLearningServices/workspaces/mlw"
      output = { identity = { principalId = "00000000-0000-0000-0000-000000000004" } }
    }
  }
}

run "dev_plan" {
  command = plan
  variables {
    env = "dev"
  }
  assert {
    condition     = azurerm_storage_account.st.shared_access_key_enabled == false
    error_message = "storage must be Entra-only"
  }
  assert {
    condition     = azapi_resource.cluster.body.properties.properties.scaleSettings.minNodeCount == 0
    error_message = "the cluster must scale to zero when idle"
  }
  assert {
    condition     = azapi_resource.cluster.body.properties.disableLocalAuth == true
    error_message = "the cluster must not accept local auth"
  }
  assert {
    condition     = azapi_resource.mlw.body.properties.systemDatastoresAuthMode == "identity"
    error_message = "workspace must reach storage with its identity"
  }
  assert {
    condition     = azurerm_role_assignment.cluster_uses_storage.role_definition_name == "Storage Blob Data Contributor"
    error_message = "the cluster only gets data access to the workspace storage"
  }
  assert {
    condition     = azurerm_resource_group.rg.name == "rg-aiops-dev"
    error_message = "names follow rg-<prefix>-<env>"
  }
  assert {
    condition     = azurerm_key_vault.kv.rbac_authorization_enabled && azurerm_key_vault.kv.purge_protection_enabled
    error_message = "Key Vault must use RBAC and purge protection"
  }
}

run "too_many_nodes_rejected" {
  command = plan
  variables {
    env       = "dev"
    max_nodes = 8
  }
  expect_failures = [var.max_nodes]
}

run "bad_prefix_rejected" {
  command = plan
  variables {
    env    = "dev"
    prefix = "IT_Desk"
  }
  expect_failures = [var.prefix]
}

run "bad_env_rejected" {
  command = plan
  variables {
    env = "staging"
  }
  expect_failures = [var.env]
}
