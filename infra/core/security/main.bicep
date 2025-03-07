param keyVaultName string
param managedIdentityName string
param location string
param vnetId string



module managedIdentity 'managed-identity.bicep' = {
  name: 'managed-identity'
  params: {
    name: managedIdentityName
    location: location
  }
}

module keyVault 'keyvault.bicep' = {
  name: 'keyVault'
  params: {
    location: location
    keyVaultName: keyVaultName
  }
}

module keyVaultpe 'keyvault-pe.bicep' = {
  name: 'keyVaultpe'
  params: {
    location: location
    keyVaultName: keyVaultName
     subnetName: 'servicesSubnet'
      vnetId: vnetId
  }
  dependsOn: [keyVault]
}

module securiyRoles 'security-roles.bicep' = { 
  name:'securiyRoles'
  params: {
    keyVaultName: keyVaultName
    managedIdentityName: managedIdentityName
  }
  dependsOn: [keyVault,managedIdentity]
}


output managedIdentityName string = managedIdentity.outputs.managedIdentityName
output keyVaultID string = keyVault.outputs.keyVaultId
output keyVaultName string = keyVaultName
output keyVaultUri string = keyVault.outputs.keyVaultUri
