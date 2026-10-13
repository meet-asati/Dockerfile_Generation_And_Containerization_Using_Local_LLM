function Docker-Runner {
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Command
    )

    Write-Output "`n----------------------------------------"
    Write-Output "Docker command: $Command"
    Write-Output "----------------------------------------"
    Write-Output "Running..."

    try {
        Invoke-Expression $Command | Out-String
    } catch {
        Write-Error "Failed to execute command: $_"
    }
}

Docker-Runner -Command $args[0]