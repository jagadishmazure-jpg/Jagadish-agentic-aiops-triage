// Microsoft Foundry / Azure ML evaluation pipeline for agentic AIOps triage. WRITTEN, NOT RUN.
// Same resources and settings as infra/terraform (parity is checked by tests/test_iac.py).
targetScope = 'resourceGroup'

@allowed(['dev', 'prod'])
param env string
param location string = resourceGroup().location
@minLength(3)
@maxLength(10)
param prefix string = 'aiops'
param logRetentionDays int = 30
param vmSize string = 'Standard_D8s_v5'
@minValue(1)
@maxValue(2)
param maxNodes int = 1
param tags object = {
  workload: 'aiops-triage'
  owner: 'ops-platform'
  data: 'synthetic'
}

var name = '${prefix}-${env}'
var flat = '${prefix}${env}'

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${name}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: logRetentionDays
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${name}'
  location: location
  tags: tags
  kind: 'other'
  properties: {
    Application_Type: 'other'
    WorkspaceResourceId: logs.id
  }
}

resource st 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'st${flat}'
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: false
    allowBlobPublicAccess: false
    sasPolicy: { sasExpirationPeriod: '01.00:00:00', expirationAction: 'Log' }
  }
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${name}'
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 7
  }
}

resource mlw 'Microsoft.MachineLearningServices/workspaces@2025-06-01' = {
  name: 'mlw-${name}'
  location: location
  tags: tags
  kind: 'Default'
  sku: { name: 'Basic', tier: 'Basic' }
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: 'AIOps triage (${env})'
    applicationInsights: appi.id
    keyVault: kv.id
    storageAccount: st.id
    systemDatastoresAuthMode: 'identity'
    hbiWorkspace: true
    publicNetworkAccess: 'Enabled'
  }
}

// CPU training cluster: scales to zero when idle, no SSH, Entra-only. Runs infra/aml/pipeline.yml.
resource cluster 'Microsoft.MachineLearningServices/workspaces/computes@2025-06-01' = {
  parent: mlw
  name: 'cpu-triage'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    computeType: 'AmlCompute'
    disableLocalAuth: true
    description: 'CPU cluster that runs the AIOps triage evaluation with a small open model.'
    properties: {
      vmSize: vmSize
      vmPriority: 'Dedicated'
      remoteLoginPortPublicAccess: 'Disabled'
      scaleSettings: {
        minNodeCount: 0
        maxNodeCount: maxNodes
        nodeIdleTimeBeforeScaleDown: 'PT2M'
      }
    }
  }
}

// Least privilege: the cluster reads data and writes results in the workspace storage (Storage Blob Data Contributor).
resource clusterUsesStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(st.id, cluster.id, 'storage-blob-data-contributor')
  scope: st
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: cluster.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource diagMlw 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-mlw'
  scope: mlw
  properties: {
    workspaceId: logs.id
    logs: [{ categoryGroup: 'allLogs', enabled: true }]
  }
}

resource diagKv 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'diag-kv'
  scope: kv
  properties: {
    workspaceId: logs.id
    logs: [{ category: 'AuditEvent', enabled: true }]
  }
}

output resourceGroup string = resourceGroup().name
output workspaceName string = mlw.name
output clusterName string = cluster.name
output keyVaultName string = kv.name
