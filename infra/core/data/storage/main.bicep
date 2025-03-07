param storageAccountName string
param location string
param identityName string
param vnetId string

module storageAccount 'blob-storage-account.bicep' ={
  name: 'storageAccount'
  params:{
     location: location
     storageAccountName:storageAccountName
     vnetId:vnetId
     subnetName:'dataSubnet'
  }
}

module storageContainers 'blob-storage-containers.bicep' = {
  name: 'storageContainers'
  params: {
    storageAccountName: storageAccountName
  }
  dependsOn:[storageAccount]
}

module storageRoles 'blob-storage-roles.bicep' = {
  name: 'storageRoles'
  params:{
    identityName:identityName
     storageAccountName:storageAccountName
  }
  dependsOn:[storageAccount]
}

module storagePe 'blob-storage-pe.bicep' = { 
  name: 'storagePe'
  params: { 
    location:location
    storageAccountName: storageAccountName
    subnetName:'servicesSubnet'
      vnetId: vnetId
  }
  dependsOn:[storageAccount]
}

output storageAccountBlobEndPoint string = storageAccount.outputs.storageAccountBlobEndPoint

