param(
    [switch]$SkipBuild,
    [switch]$SkipFailover
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$apiUrl = "http://127.0.0.1:8081/checkout"
$executorServices = @("order_executor_1", "order_executor_2", "order_executor_3")
$logServices = @(
    "orchestrator",
    "transaction_verification",
    "fraud_detection",
    "suggestions",
    "order_queue"
) + $executorServices
$pythonFiles = @(
    "orchestrator/src/app.py",
    "transaction_verification/src/app.py",
    "fraud_detection/src/app.py",
    "suggestions/src/app.py",
    "order_queue/src/app.py",
    "order_executor/src/app.py"
)
$results = [System.Collections.Generic.List[object]]::new()
$script:CurrentFailureList = $null

function Write-Section {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message =="
}

function Add-CheckResult {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Details
    )

    $results.Add([pscustomobject]@{
        Name = $Name
        Passed = $Passed
        Details = $Details
    })

    $status = if ($Passed) { "PASS" } else { "FAIL" }
    Write-Host ("[{0}] {1} - {2}" -f $status, $Name, $Details)
}

function Run-Compose {
    param([string[]]$ComposeArgs)

    $output = & docker compose @ComposeArgs 2>&1
    $exitCode = $LASTEXITCODE

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = ($output | Out-String).TrimEnd()
    }
}

function Get-ComposeLogs {
    param(
        [string[]]$Services,
        [int]$Tail = 400,
        [string]$Since
    )

    $args = @("logs", "--no-color")
    if ($Since) {
        $args += @("--since", $Since)
    }
    $args += "--tail=$Tail"
    $args += $Services

    $result = Run-Compose $args
    if ($result.ExitCode -ne 0) {
        throw "docker compose logs failed.`n$($result.Output)"
    }

    return $result.Output
}

function Invoke-Checkout {
    param([string]$FilePath)

    $body = Get-Content $FilePath -Raw
    $response = Invoke-WebRequest `
        -Uri $apiUrl `
        -Method POST `
        -ContentType "application/json" `
        -Body $body

    return [pscustomobject]@{
        StatusCode = [int]$response.StatusCode
        Json = ($response.Content | ConvertFrom-Json)
        Raw = $response.Content
    }
}

function Wait-ForOrchestrator {
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $response = Invoke-WebRequest `
                -Uri "http://127.0.0.1:8081/" `
                -Method GET
            if ([int]$response.StatusCode -eq 200) {
                return
            }
        }
        catch {
        }

        Start-Sleep -Seconds 2
    }

    throw "Orchestrator did not become ready on http://127.0.0.1:8081/."
}

function Assert-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        if ($null -eq $script:CurrentFailureList) {
            throw "Current failure list is not initialized."
        }
        $script:CurrentFailureList.Add($Message)
    }
}

function Get-OrderLogLines {
    param(
        [string]$Logs,
        [string]$OrderId
    )

    $normalizedOrderId = $OrderId.Trim()

    return @(
        ($Logs -split "\r?\n") | Where-Object { $_ -like "*$normalizedOrderId*" }
    )
}

function Get-CurrentLeaderId {
    $logs = Get-ComposeLogs -Services (@("order_queue") + $executorServices) -Tail 800 -Since "30m"
    $dequeueMatch = [regex]::Matches($logs, "action=dequeue .* executor=(\d+)")
    if ($dequeueMatch.Count -gt 0) {
        return [int]$dequeueMatch[$dequeueMatch.Count - 1].Groups[1].Value
    }

    $executionMatch = [regex]::Matches($logs, "\[EXEC-(\d+)\] leader=\d+ executing order=")
    if ($executionMatch.Count -gt 0) {
        return [int]$executionMatch[$executionMatch.Count - 1].Groups[1].Value
    }

    $leaderMatch = [regex]::Matches($logs, "\[EXEC-(\d+)\] became leader")
    if ($leaderMatch.Count -gt 0) {
        return [int]$leaderMatch[$leaderMatch.Count - 1].Groups[1].Value
    }

    $leaderAnnouncement = [regex]::Matches($logs, "new leader is (\d+)")
    if ($leaderAnnouncement.Count -gt 0) {
        return [int]$leaderAnnouncement[$leaderAnnouncement.Count - 1].Groups[1].Value
    }

    throw "Could not determine the current leader from executor logs."
}

function Wait-ForOrderLogs {
    param(
        [string]$OrderId,
        [bool]$ShouldQueue,
        [bool]$ShouldExecute,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $latestLogs = ""

    while ((Get-Date) -lt $deadline) {
        $latestLogs = Get-ComposeLogs -Services $logServices -Tail 1200 -Since "30m"
        $orderLines = Get-OrderLogLines -Logs $latestLogs -OrderId $OrderId

        $hasTvClear = @($orderLines | Where-Object { $_ -match "\[TV\]" -and $_ -match "event=ClearOrder" -and $_ -match "success=True" }).Count -ge 1
        $hasFdClear = @($orderLines | Where-Object { $_ -match "\[FD\]" -and $_ -match "event=ClearOrder" -and $_ -match "success=True" }).Count -ge 1
        $hasSugClear = @($orderLines | Where-Object { $_ -match "\[SUG\]" -and $_ -match "event=ClearOrder" -and $_ -match "success=True" }).Count -ge 1
        $hasOrchClear = @($orderLines | Where-Object { $_ -match "\[ORCH\]" -and $_ -match "clear_broadcast_sent" }).Count -ge 1
        $hasQueueEnqueue = @($orderLines | Where-Object { $_ -match "\[QUEUE\]" -and $_ -match "action=enqueue" }).Count -ge 1
        $hasQueueDequeue = @($orderLines | Where-Object { $_ -match "\[QUEUE\]" -and $_ -match "action=dequeue" }).Count -ge 1
        $hasExecution = @($orderLines | Where-Object { $_ -match "\[EXEC-" -and $_ -match "executing order=" }).Count -ge 1

        $ready = $hasTvClear -and $hasFdClear -and $hasSugClear -and $hasOrchClear
        if ($ShouldQueue) {
            $ready = $ready -and $hasQueueEnqueue -and $hasQueueDequeue
        }
        if ($ShouldExecute) {
            $ready = $ready -and $hasExecution
        }

        if ($ready) {
            return $latestLogs
        }

        Start-Sleep -Seconds 2
    }

    return $latestLogs
}

function Test-CheckoutCase {
    param(
        [string]$Name,
        [string]$FilePath,
        [string]$ExpectedStatus,
        [string]$ExpectedReason,
        [bool]$ShouldQueue,
        [bool]$ShouldExecute,
        [bool]$RequireAllEventLogs
    )

    $failures = [System.Collections.Generic.List[string]]::new()
    $script:CurrentFailureList = $failures
    $response = Invoke-Checkout -FilePath $FilePath

    $orderId = ([string]$response.Json.orderId).Trim()
    $logs = Wait-ForOrderLogs `
        -OrderId $orderId `
        -ShouldQueue $ShouldQueue `
        -ShouldExecute $ShouldExecute
    $orderLines = Get-OrderLogLines -Logs $logs -OrderId $orderId
    $tvClear = @($orderLines | Where-Object { $_ -match "\[TV\]" -and $_ -match "event=ClearOrder" -and $_ -match "success=True" })
    $fdClear = @($orderLines | Where-Object { $_ -match "\[FD\]" -and $_ -match "event=ClearOrder" -and $_ -match "success=True" })
    $sugClear = @($orderLines | Where-Object { $_ -match "\[SUG\]" -and $_ -match "event=ClearOrder" -and $_ -match "success=True" })
    $queueEnqueue = @($orderLines | Where-Object { $_ -match "\[QUEUE\]" -and $_ -match "action=enqueue" })
    $queueDequeue = @($orderLines | Where-Object { $_ -match "\[QUEUE\]" -and $_ -match "action=dequeue" })
    $executionLines = @($orderLines | Where-Object { $_ -match "\[EXEC-" -and $_ -match "executing order=" })
    $warningLines = @($orderLines | Where-Object { $_ -match "clear_broadcast_warning" })

    Assert-Condition ($response.StatusCode -eq 200) "Expected HTTP 200 but got $($response.StatusCode)."
    Assert-Condition ($ExpectedStatus -eq [string]$response.Json.status) "Expected status '$ExpectedStatus' but got '$($response.Json.status)'."
    Assert-Condition ([string]::IsNullOrEmpty($orderId) -eq $false) "Response did not include an orderId."
    Assert-Condition ($warningLines.Count -eq 0) "Found clear_broadcast_warning log lines for order $orderId."
    Assert-Condition ($tvClear.Count -ge 1) "Transaction verification did not clear order $orderId successfully."
    Assert-Condition ($fdClear.Count -ge 1) "Fraud detection did not clear order $orderId successfully."
    Assert-Condition ($sugClear.Count -ge 1) "Suggestions did not clear order $orderId successfully."
    Assert-Condition (@($orderLines | Where-Object { $_ -match "\[ORCH\]" -and $_ -match "initialization_complete" }).Count -ge 1) "Orchestrator initialization log is missing for order $orderId."
    Assert-Condition (@($orderLines | Where-Object { $_ -match "\[ORCH\]" -and $_ -match "clear_broadcast_sent" }).Count -ge 1) "Clear broadcast log is missing for order $orderId."

    if ($ExpectedReason) {
        Assert-Condition ($ExpectedReason -eq [string]$response.Json.reason) "Expected reason '$ExpectedReason' but got '$($response.Json.reason)'."
    }

    if ($ShouldQueue) {
        Assert-Condition ($queueEnqueue.Count -ge 1) "Queue enqueue log is missing for order $orderId."
        Assert-Condition ($queueDequeue.Count -ge 1) "Queue dequeue log is missing for order $orderId."
    }
    else {
        Assert-Condition ($queueEnqueue.Count -eq 0) "Order $orderId should not have been enqueued."
        Assert-Condition ($queueDequeue.Count -eq 0) "Order $orderId should not have been dequeued."
    }

    if ($ShouldExecute) {
        Assert-Condition ($executionLines.Count -ge 1) "No executor executed order $orderId."
    }
    else {
        Assert-Condition ($executionLines.Count -eq 0) "A replica executed rejected order $orderId."
    }

    if ($RequireAllEventLogs) {
        Assert-Condition (@($orderLines | Where-Object { $_ -match "\[TV\]" -and $_ -match "event=ValidateItems" -and $_ -match "vc=\[" }).Count -ge 1) "ValidateItems VC log is missing for order $orderId."
        Assert-Condition (@($orderLines | Where-Object { $_ -match "\[TV\]" -and $_ -match "event=ValidateUserData" -and $_ -match "vc=\[" }).Count -ge 1) "ValidateUserData VC log is missing for order $orderId."
        Assert-Condition (@($orderLines | Where-Object { $_ -match "\[TV\]" -and $_ -match "event=ValidateCardFormat" -and $_ -match "vc=\[" }).Count -ge 1) "ValidateCardFormat VC log is missing for order $orderId."
        Assert-Condition (@($orderLines | Where-Object { $_ -match "\[FD\]" -and $_ -match "event=CheckUserFraud" -and $_ -match "vc=\[" }).Count -ge 1) "CheckUserFraud VC log is missing for order $orderId."
        Assert-Condition (@($orderLines | Where-Object { $_ -match "\[FD\]" -and $_ -match "event=CheckCardFraud" -and $_ -match "vc=\[" }).Count -ge 1) "CheckCardFraud VC log is missing for order $orderId."
        Assert-Condition (@($orderLines | Where-Object { $_ -match "\[SUG\]" -and $_ -match "event=PrecomputeSuggestions" -and $_ -match "vc=\[" }).Count -ge 1) "PrecomputeSuggestions VC log is missing for order $orderId."
        Assert-Condition (@($orderLines | Where-Object { $_ -match "\[SUG\]" -and $_ -match "event=FinalizeSuggestions" -and $_ -match "vc=\[" }).Count -ge 1) "FinalizeSuggestions VC log is missing for order $orderId."
        Assert-Condition (@($orderLines | Where-Object { $_ -match "\[ORCH\]" -and $_ -match "final_status=APPROVED" }).Count -ge 1) "Final approval log is missing for order $orderId."
    }

    $passed = $failures.Count -eq 0
    $details = if ($passed) {
        "orderId=$orderId status=$($response.Json.status)"
    }
    else {
        ($failures -join " ")
    }

    Add-CheckResult -Name "checkout:$Name" -Passed $passed -Details $details
    $script:CurrentFailureList = $null

    return [pscustomobject]@{
        Passed = $passed
        OrderId = $orderId
        Response = $response
    }
}

function Test-LeaderFailover {
    $failures = [System.Collections.Generic.List[string]]::new()
    $script:CurrentFailureList = $failures
    $leaderId = Get-CurrentLeaderId
    $leaderService = "order_executor_$leaderId"

    Write-Host "Stopping current leader service $leaderService to test failover..."

    try {
        $stopResult = Run-Compose @("stop", $leaderService)
        if ($stopResult.ExitCode -ne 0) {
            throw "Failed to stop $leaderService.`n$($stopResult.Output)"
        }

        Start-Sleep -Seconds 8
        $failoverLogs = Get-ComposeLogs -Services $executorServices -Tail 250 -Since "30s"
        Assert-Condition ($failoverLogs -match "leader timeout detected") "No leader timeout was detected after stopping $leaderService."
        Assert-Condition ($failoverLogs -match "became leader") "No replacement leader was elected after stopping $leaderService."

        $response = Invoke-Checkout -FilePath "test_checkout.json"

        $orderId = ([string]$response.Json.orderId).Trim()
        $logs = Wait-ForOrderLogs `
            -OrderId $orderId `
            -ShouldQueue $true `
            -ShouldExecute $true `
            -TimeoutSeconds 25
        $orderLines = Get-OrderLogLines -Logs $logs -OrderId $orderId
        $executionLines = @($orderLines | Where-Object { $_ -match "\[EXEC-" -and $_ -match "executing order=" })
        $dequeueLines = @($orderLines | Where-Object { $_ -match "\[QUEUE\]" -and $_ -match "action=dequeue" })
        $stoppedExecutorExecution = @($executionLines | Where-Object { $_ -match "\[EXEC-$leaderId\]" })
        $stoppedExecutorDequeue = @($dequeueLines | Where-Object { $_ -match "executor=$leaderId" })

        Assert-Condition ($response.StatusCode -eq 200) "Failover checkout returned HTTP $($response.StatusCode)."
        Assert-Condition ("Order Approved" -eq [string]$response.Json.status) "Failover checkout was not approved."
        Assert-Condition ($executionLines.Count -ge 1) "No executor executed the failover test order $orderId."
        Assert-Condition ($dequeueLines.Count -ge 1) "Queue did not dequeue the failover test order $orderId."
        Assert-Condition ($stoppedExecutorExecution.Count -eq 0) "Stopped leader executor $leaderId executed order $orderId."
        Assert-Condition ($stoppedExecutorDequeue.Count -eq 0) "Stopped leader executor $leaderId dequeued order $orderId."
    }
    finally {
        Write-Host "Restoring $leaderService..."
        $restoreResult = Run-Compose @("up", "-d", $leaderService)
        if ($restoreResult.ExitCode -ne 0) {
            Add-CheckResult -Name "failover:restore" -Passed $false -Details $restoreResult.Output
        }
        else {
            Start-Sleep -Seconds 4
        }
    }

    $passed = $failures.Count -eq 0
    $details = if ($passed) {
        "Failover succeeded after stopping $leaderService."
    }
    else {
        ($failures -join " ")
    }

    Add-CheckResult -Name "leader-failover" -Passed $passed -Details $details
    $script:CurrentFailureList = $null
}

Write-Section "Environment"

$dockerVersion = & docker --version
Add-CheckResult -Name "docker" -Passed ($LASTEXITCODE -eq 0) -Details $dockerVersion

$composeVersion = & docker compose version
Add-CheckResult -Name "docker-compose" -Passed ($LASTEXITCODE -eq 0) -Details $composeVersion

$configResult = Run-Compose @("config")
Add-CheckResult -Name "compose-config" -Passed ($configResult.ExitCode -eq 0) -Details "docker compose config exited with code $($configResult.ExitCode)."

Write-Section "Startup"

if ($SkipBuild) {
    $upResult = Run-Compose @("up", "-d")
    Add-CheckResult -Name "compose-up" -Passed ($upResult.ExitCode -eq 0) -Details "Started stack without rebuild."
}
else {
    $upResult = Run-Compose @("up", "--build", "-d")
    Add-CheckResult -Name "compose-up" -Passed ($upResult.ExitCode -eq 0) -Details "Started stack with rebuild."
}

Wait-ForOrchestrator
Add-CheckResult -Name "orchestrator-ready" -Passed $true -Details "HTTP endpoint is reachable."

$psResult = Run-Compose @("ps")
Add-CheckResult -Name "compose-ps" -Passed ($psResult.ExitCode -eq 0) -Details "docker compose ps completed."

Write-Section "Syntax"

foreach ($path in $pythonFiles) {
    python -m py_compile $path
    Add-CheckResult -Name "py-compile:$path" -Passed ($LASTEXITCODE -eq 0) -Details "Syntax OK."
}

Write-Section "Checkout Scenarios"

Test-CheckoutCase `
    -Name "valid" `
    -FilePath "test_checkout.json" `
    -ExpectedStatus "Order Approved" `
    -ExpectedReason "" `
    -ShouldQueue $true `
    -ShouldExecute $true `
    -RequireAllEventLogs $true | Out-Null

Test-CheckoutCase `
    -Name "fraud" `
    -FilePath "test_checkout_fraud.json" `
    -ExpectedStatus "Order Rejected" `
    -ExpectedReason "Suspicious card number pattern." `
    -ShouldQueue $false `
    -ShouldExecute $false `
    -RequireAllEventLogs $false | Out-Null

Test-CheckoutCase `
    -Name "empty-items" `
    -FilePath "test_checkout_empty_items.json" `
    -ExpectedStatus "Order Rejected" `
    -ExpectedReason "No items in order." `
    -ShouldQueue $false `
    -ShouldExecute $false `
    -RequireAllEventLogs $false | Out-Null

Test-CheckoutCase `
    -Name "terms-false" `
    -FilePath "test_checkout_terms_false.json" `
    -ExpectedStatus "Order Rejected" `
    -ExpectedReason "Terms and conditions not accepted." `
    -ShouldQueue $false `
    -ShouldExecute $false `
    -RequireAllEventLogs $false | Out-Null

if (-not $SkipFailover) {
    Write-Section "Failover"
    Test-LeaderFailover
}

Write-Section "Summary"

$passedCount = @($results | Where-Object { $_.Passed }).Count
$failedCount = @($results | Where-Object { -not $_.Passed }).Count

foreach ($result in $results) {
    $status = if ($result.Passed) { "PASS" } else { "FAIL" }
    Write-Host ("{0} {1}" -f $status, $result.Name)
}

Write-Host ""
Write-Host ("Passed: {0}" -f $passedCount)
Write-Host ("Failed: {0}" -f $failedCount)

if ($failedCount -gt 0) {
    exit 1
}

exit 0
