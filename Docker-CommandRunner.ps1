function Docker-Runner {
    param(
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$Command
    )

    Write-Output "`n----------------------------------------"
    Write-Output "Docker command: $Command"
    Write-Output "----------------------------------------"
    Write-Output "Running..."

    $stdoutFile = [System.IO.Path]::GetTempFileName()
    $stderrFile = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/d", "/s", "/c", $Command `
            -WorkingDirectory (Get-Location) `
            -RedirectStandardOutput $stdoutFile `
            -RedirectStandardError $stderrFile `
            -NoNewWindow -Wait -PassThru

        Get-Content $stdoutFile
        Get-Content $stderrFile
        exit $process.ExitCode
    } catch {
        Write-Error "Failed to execute command: $_"
        exit 1
    } finally {
        Remove-Item $stdoutFile, $stderrFile -ErrorAction SilentlyContinue
    }
}

Docker-Runner -Command $args[0]