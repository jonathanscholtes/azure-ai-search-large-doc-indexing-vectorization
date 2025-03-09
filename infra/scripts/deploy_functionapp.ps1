# Params
param (
    [string]$functionAppName,
    [string]$resourceGroupName
)

$pythonAppPath = "..\..\src\DocumentProcessingFunction"
$tempDir = "artifacts\loader\temp"
$zipFilePath = "artifacts\loader\app.zip"

# Construct the argument list
$args = "$pythonAppPath $zipFilePath $tempDir --exclude_dirs venv  --exclude_files local.settings.json .env *.md"

# Execute the Python script
Start-Process "python" -ArgumentList "directory_zipper.py $args" -NoNewWindow -Wait

az functionapp deployment source config-zip --resource-group $resourceGroupName --name $functionAppName --src $zipFilePath --timeout 3000 --build-remote true 
