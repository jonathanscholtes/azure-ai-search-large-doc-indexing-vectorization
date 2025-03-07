param storageAccountName string
param location string
param vnetId string
param subnetName string

resource storageAcct 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: true
    publicNetworkAccess: 'Enabled'
    allowBlobPublicAccess: true
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
      virtualNetworkRules: [
        {
          id: '${vnetId}/subnets/${subnetName}'
        }
      ]
    }
  }
}

output storageAccountBlobEndPoint string = 'https://${storageAcct.name}.blob.core.windows.net/'
