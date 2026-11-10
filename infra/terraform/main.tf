# Microsoft Foundry / Azure ML evaluation pipeline for agentic AIOps triage. WRITTEN, NOT RUN.
# Creates: resource group, Log Analytics, Application Insights, storage (Entra-only), Key Vault (RBAC), an
# Azure ML workspace (the hub type Microsoft Foundry hub-based projects use), a CPU compute cluster that
# scales to zero, and one role assignment so the cluster identity can use the workspace storage. The
# pipeline (infra/aml/pipeline.yml) is submitted by .github/workflows/deploy.yml, which is gated off.

data "azurerm_client_config" "current" {}

locals {
  name = "${var.prefix}-${var.env}"
  flat = "${var.prefix}${var.env}"
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = var.tags
}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-${local.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = var.tags
}

resource "azurerm_application_insights" "appi" {
  name                = "appi-${local.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  workspace_id        = azurerm_log_analytics_workspace.logs.id
  application_type    = "other"
  tags                = var.tags
}

resource "azurerm_storage_account" "st" {
  name                            = "st${local.flat}"
  location                        = azurerm_resource_group.rg.location
  resource_group_name             = azurerm_resource_group.rg.name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  tags                            = var.tags

  blob_properties {
    delete_retention_policy {
      days = 7
    }
    container_delete_retention_policy {
      days = 7
    }
  }

  sas_policy {
    expiration_period = "01.00:00:00"
  }
}

resource "azurerm_key_vault" "kv" {
  name                       = "kv-${local.name}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
  tags                       = var.tags
}

# Azure ML workspace via azapi so storage can stay Entra-only (systemDatastoresAuthMode = identity),
# which the azurerm workspace resource does not expose. Bicep sets the same properties.
resource "azapi_resource" "mlw" {
  type      = "Microsoft.MachineLearningServices/workspaces@2025-06-01"
  name      = "mlw-${local.name}"
  parent_id = azurerm_resource_group.rg.id
  location  = azurerm_resource_group.rg.location
  tags      = var.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    kind = "Default"
    sku  = { name = "Basic", tier = "Basic" }
    properties = {
      friendlyName             = "AIOps triage (${var.env})"
      applicationInsights      = azurerm_application_insights.appi.id
      keyVault                 = azurerm_key_vault.kv.id
      storageAccount           = azurerm_storage_account.st.id
      systemDatastoresAuthMode = "identity"
      hbiWorkspace             = true
      publicNetworkAccess      = "Enabled"
    }
  }
}

# CPU training cluster: scales to zero when idle, no SSH, Entra-only. Runs infra/aml/pipeline.yml.
resource "azapi_resource" "cluster" {
  type      = "Microsoft.MachineLearningServices/workspaces/computes@2025-06-01"
  name      = "cpu-triage"
  parent_id = azapi_resource.mlw.id
  location  = azurerm_resource_group.rg.location
  tags      = var.tags

  identity {
    type = "SystemAssigned"
  }

  body = {
    properties = {
      computeType      = "AmlCompute"
      disableLocalAuth = true
      description      = "CPU cluster that runs the AIOps triage evaluation with a small open model."
      properties = {
        vmSize                      = var.vm_size
        vmPriority                  = "Dedicated"
        remoteLoginPortPublicAccess = "Disabled"
        scaleSettings = {
          minNodeCount                = 0
          maxNodeCount                = var.max_nodes
          nodeIdleTimeBeforeScaleDown = "PT2M"
        }
      }
    }
  }

  response_export_values = ["identity.principalId"]
}

# Least privilege: the cluster reads data and writes results in the workspace storage, nothing else.
resource "azurerm_role_assignment" "cluster_uses_storage" {
  scope                = azurerm_storage_account.st.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azapi_resource.cluster.output.identity.principalId
  principal_type       = "ServicePrincipal"
}

resource "azurerm_monitor_diagnostic_setting" "mlw" {
  name                       = "diag-mlw"
  target_resource_id         = azapi_resource.mlw.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id

  enabled_log {
    category_group = "allLogs"
  }
}

resource "azurerm_monitor_diagnostic_setting" "kv" {
  name                       = "diag-kv"
  target_resource_id         = azurerm_key_vault.kv.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id

  enabled_log {
    category = "AuditEvent"
  }
}
