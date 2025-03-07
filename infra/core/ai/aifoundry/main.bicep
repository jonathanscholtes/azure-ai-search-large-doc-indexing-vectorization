param location string
param identityName string
param aiHubName string
param aiProjectName string
param aiServicesName string
param keyVaultId string
param customSubdomain string


module aiServices 'azure-ai-services.bicep' = {
  name: 'aiServices'
  params: {
    aiServicesName: aiServicesName
    location: location
    identityName: identityName
    customSubdomain: customSubdomain
  }
}

module aiHub 'ai-hub.bicep' = {
  name: 'aihub'
  params:{
    aiHubName: aiHubName
    aiHubDescription: 'Hub for RAG with AI Search'
    aiServicesId:aiServices.outputs.aiservicesID
    aiServicesTarget: aiServices.outputs.aiservicesTarget
    keyVaultId: keyVaultId
    location: location
    aiHubFriendlyName: 'AI RAG Demo Hub'
  }
}

module aiProject 'ai-project.bicep' = {
  name: 'aiProject'
  params:{
    aiHubResourceId:aiHub.outputs.aiHubID
    location: location
    aiProjectName: aiProjectName
    aiProjectFriendlyName: 'AI RAG Project'
    aiProjectDescription: 'Project Testing RAG with AI Sarch'    
  }
}

module aiModels 'ai-models.bicep' = {
  name:'aiModels'
  params:{
    aiProjectName:aiProjectName
     aiServicesName:aiServicesName
      location: location
  }
  dependsOn:[aiServices,aiProject]
}


output aiservicesTarget string = aiServices.outputs.aiservicesTarget
output OpenAIEndPoint string = aiServices.outputs.OpenAIEndPoint
