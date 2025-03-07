param projectName string
param environmentName string
param resourceToken string
param location string
param identityName string
param keyVaultName string
param vnetId string


var storageAccountName ='sa${projectName}${resourceToken}'

module storage 'storage/main.bicep' = {
name: 'storage'
params:{
  identityName:identityName
   location:location
   storageAccountName:storageAccountName
   vnetId: vnetId
}
}



output storageAccountBlobEndPoint string = storage.outputs.storageAccountBlobEndPoint
output storageAccountName string = storageAccountName
