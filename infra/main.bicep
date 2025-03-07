targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name which is used to generate a short unique hash for each resource')
param environmentName string

@minLength(1)
@maxLength(64)
@description('Name which is used to generate a short unique hash for each resource')
param projectName string

@minLength(1)
@description('Primary location for all resources')
param location string


var resourceToken = uniqueString(environmentName,projectName,location,az.subscription().subscriptionId)

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${projectName}-${environmentName}-${location}-${resourceToken}'
  location: location
}

module networking 'core/networking/main.bicep' = {
  name: 'networking'
  scope: resourceGroup 
  params: { 
     location: location
     vnetName: 'vnet-${projectName}-${environmentName}-${resourceToken}'
  }
}

module security 'core/security/main.bicep' = {
  name: 'security'
  scope: resourceGroup
  params:{
    keyVaultName: 'kv${projectName}${resourceToken}'
    managedIdentityName: 'id-${projectName}-${environmentName}'
    location: location
    vnetId: networking.outputs.vnetId
  }
}

module data 'core/data/main.bicep' = {
  name: 'data'
  scope: resourceGroup
  params:{
    projectName:projectName
    environmentName:environmentName
    resourceToken:resourceToken
    location: location
    identityName:security.outputs.managedIdentityName
    keyVaultName: security.outputs.keyVaultName
    vnetId: networking.outputs.vnetId
  }
}


module azureai 'core/ai/main.bicep' = {
  name: 'azure-ai'
  scope: resourceGroup
  params: {
    projectName:projectName
    environmentName:environmentName
    resourceToken:resourceToken
    location: location
    keyVaultId: security.outputs.keyVaultID
    identityName:security.outputs.managedIdentityName
    searchServicename: 'srch-${projectName}-${environmentName}-${resourceToken}'
  }

}


output resourceGroupName string = resourceGroup.name
