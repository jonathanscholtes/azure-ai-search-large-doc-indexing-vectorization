param (
    [string]$Subscription,
    [string]$Location = "eastus2"
)


# Variables
$projectName = "search"
$environmentName = "test"
$templateFile = "main.bicep"
$deploymentName = "search-embedding-test-deployment-$Location"


# Clear account context and configure Azure CLI settings
az account clear
az config set core.enable_broker_on_windows=false
az config set core.login_experience_v2=off

# Login to Azure
az login 
az account set --subscription $Subscription


# Start the deployment
$deploymentOutput = az deployment sub create `
    --name $deploymentName `
    --location $Location `
    --template-file $templateFile `
    --parameters `
        environmentName=$environmentName `
        projectName=$projectName `
        location=$Location `
    --query "properties.outputs"


# Parse the deployment output to get app names and resource group
$deploymentOutputJson = $deploymentOutput | ConvertFrom-Json
$resourceGroupName = $deploymentOutputJson.resourceGroupName.value
$functionAppName = $deploymentOutputJson.functionAppName.value


Start-Sleep -Seconds 300

Set-Location -Path .\scripts


# Deploy Function Application
Write-Output "*****************************************"
Write-Output "Deploying Function Application from scripts"
Write-Output "If timeout occurs, rerun the following command from scripts:"
Write-Output ".\deploy_functionapp.ps1 -functionAppName $functionAppName -resourceGroupName $resourceGroupName"
& .\deploy_functionapp.ps1 -functionAppName $functionAppName -resourceGroupName $resourceGroupName

Write-Output "Deployment Complete"