function Generate-Command {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Prompt
    )

    $RawOutput = ollama run docker-bot "$Prompt"
    $RawCmd = ($RawOutput -join "`n").Trim()
    $CleanCmd = $RawCmd -replace '^`+', '' -replace '`+$', ''

    return $CleanCmd
}

function Docker-Runner {
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Prompt
    )

    $FullPrompt = $args ? "$Prompt ($args -join ' ')" : $Prompt

    $Cmd = Generate-Command -Prompt $FullPrompt

    while ([string]::IsNullOrWhiteSpace($Cmd)) {
        Write-Host "Received empty response from AI, retrying..." -ForegroundColor Gray
        $Cmd = Generate-Command -Prompt $FullPrompt
    }

    Write-Host "`n----------------------------------------" -ForegroundColor Cyan
    Write-Host "Docker command: $Cmd" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Cyan

    $Confirmation = Read-Host "Execute this command? [(Y)es/(N)o]"
    if ($Confirmation -match '^[Yy]') {
        Write-Host "Running..." -ForegroundColor Green
        try {
            Invoke-Expression $Cmd
        } catch {
            Write-Error "Failed to execute command: \$_"
        }
    }
    else {
        Write-Host "Execution canceled." -ForegroundColor Red
    }
}
