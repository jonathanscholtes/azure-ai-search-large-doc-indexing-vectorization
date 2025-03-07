param vnetName string
param location string

module vNet 'vnet.bicep' = { 
  name: 'vNet'
  params: { 
     vnetLocation:location
     vnetName:vnetName
  }
}

output vnetId string = vNet.outputs.vnetId
