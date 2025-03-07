param projectName string
param environmentName string
param resourceToken string
param location string
param identityName string
param searchServicename string


@description('Resource ID of the key vault resource for storing connection strings')
param keyVaultId string


var aiServicesName  = 'ais-${projectName}-${environmentName}-${resourceToken}'
var aiProjectName  = 'prj-${projectName}-${environmentName}-${resourceToken}'
var aiHubName = 'hub-${projectName}-${environmentName}-${resourceToken}'
var customSubdomain = 'openai-app-${resourceToken}'


module aiFoundry 'aifoundry/main.bicep' = { 
  name: 'aiFoundry'
  params: { 
    location:location
    identityName: identityName
    keyVaultId:keyVaultId
    aiHubName: aiHubName 
    aiProjectName: aiProjectName 
    aiServicesName: aiServicesName 
    customSubdomain: customSubdomain
  }
}

module search 'search/main.bicep' = { 
  name: 'search'
  params: {
  location:location
  identityName: identityName
  searchServicename: searchServicename
  }
}

output aiservicesTarget string = aiFoundry.outputs.aiservicesTarget
output OpenAIEndPoint string = aiFoundry.outputs.OpenAIEndPoint
output searchServiceEndpoint string = search.outputs.searchServiceEndpoint
