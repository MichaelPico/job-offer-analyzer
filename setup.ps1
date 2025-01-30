
$modelsDir = "$PSScriptRoot\llm_models\fasttext"

# FastText
$fasttextModelUrl = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
$fasttextModelPath = Join-Path $modelsDir "lid.176.bin"

##############################################
# Download FastText Language Detection Model #
##############################################

# Create the models directory if it doesn't exist
if (-not (Test-Path $modelsDir)) {
    try {
        New-Item -ItemType Directory -Path $modelsDir -Force
        Write-Host "Created directory: $modelsDir" -ForegroundColor Green
    }
    catch {
        Write-Host "Error creating directory: $_" -ForegroundColor Red
        exit 1
    }
}

# Download the model
try {
    Write-Host "Downloading FastText language detection model..." -ForegroundColor Yellow
    $ProgressPreference = 'SilentlyContinue'  # Makes download faster
    Invoke-WebRequest -Uri $fasttextModelUrl -OutFile $fasttextModelPath
    Write-Host "Successfully downloaded model to: $fasttextModelPath" -ForegroundColor Green
    
    # Verify file exists and show size
    $fileSize = (Get-Item $fasttextModelPath).Length / 1MB
    Write-Host "File size: $($fileSize.ToString('N2')) MB" -ForegroundColor Cyan
}
catch {
    Write-Host "Error downloading model: $_" -ForegroundColor Red
    exit 1
}