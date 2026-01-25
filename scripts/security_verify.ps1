# Security Verification Script
# Run this after applying security patches

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SECURITY VERIFICATION SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorCount = 0
$WarningCount = 0

# Test 1: Check dependency vulnerabilities
Write-Host "[TEST 1] Checking dependency vulnerabilities..." -ForegroundColor Yellow
try {
    $auditResult = pip-audit --desc 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ PASS: No known vulnerabilities found" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ FAIL: Vulnerabilities found" -ForegroundColor Red
        Write-Host $auditResult
        $ErrorCount++
    }
}
catch {
    Write-Host "  ⚠ WARNING: pip-audit not installed" -ForegroundColor Yellow
    $WarningCount++
}

# Test 2: Check CORS configuration
Write-Host "`n[TEST 2] Checking CORS configuration..." -ForegroundColor Yellow
$corsCheck = Select-String -Path "truthkeeper_api.py" -Pattern 'allow_origins=\["\*"\]'
if ($corsCheck) {
    Write-Host "  ✗ FAIL: CORS wildcard still present" -ForegroundColor Red
    $ErrorCount++
}
else {
    Write-Host "  ✓ PASS: CORS wildcard removed" -ForegroundColor Green
}

# Test 3: Test unauthenticated access
Write-Host "`n[TEST 3] Testing unauthenticated access..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/memory/test_user" -Method GET -ErrorAction Stop
    Write-Host "  ✗ FAIL: Unauthenticated access allowed (Status: $($response.StatusCode))" -ForegroundColor Red
    $ErrorCount++
}
catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 401) {
        Write-Host "  ✓ PASS: Unauthenticated access blocked (401)" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠ WARNING: Unexpected status code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Yellow
        $WarningCount++
    }
}

# Test 4: Check for hardcoded secrets
Write-Host "`n[TEST 4] Scanning for hardcoded secrets..." -ForegroundColor Yellow
$secretPatterns = @("sk-[a-zA-Z0-9]{20,}", "api_key\s*=\s*['\"][^'\"]{20,}['\"]")
$secretsFound = $false
foreach ($pattern in $secretPatterns) {
    $matches = Select-String -Path "app\*.py" -Pattern $pattern -Recurse
    if ($matches) {
        Write-Host "  ✗ FAIL: Potential secrets found" -ForegroundColor Red
        $matches | ForEach-Object { Write-Host "    $_" }
        $secretsFound = $true
    }
}
if (-not $secretsFound) {
    Write-Host "  ✓ PASS: No hardcoded secrets found" -ForegroundColor Green
}

# Test 5: Check database CASCADE delete
Write-Host "`n[TEST 5] Checking CASCADE delete constraints..." -ForegroundColor Yellow
$cascadeCheck = Select-String -Path "schema_tmg.sql" -Pattern "ON DELETE CASCADE"
if ($cascadeCheck) {
    Write-Host "  ✓ PASS: CASCADE delete constraints found" -ForegroundColor Green
}
else {
    Write-Host "  ✗ FAIL: CASCADE delete constraints missing" -ForegroundColor Red
    $ErrorCount++
}

# Test 6: Check for exception handler
Write-Host "`n[TEST 6] Checking global exception handler..." -ForegroundColor Yellow
$exceptionHandler = Select-String -Path "truthkeeper_api.py" -Pattern "@app.exception_handler\(Exception\)"
if ($exceptionHandler) {
    Write-Host "  ✓ PASS: Global exception handler found" -ForegroundColor Green
}
else {
    Write-Host "  ⚠ WARNING: Global exception handler not found" -ForegroundColor Yellow
    $WarningCount++
}

# Test 7: Check Python version
Write-Host "`n[TEST 7] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "3\.(9|1[0-9])\.") {
    Write-Host "  ✓ PASS: Python version OK ($pythonVersion)" -ForegroundColor Green
}
else {
    Write-Host "  ⚠ WARNING: Python version may be outdated ($pythonVersion)" -ForegroundColor Yellow
    $WarningCount++
}

# Test 8: Check pip and setuptools versions
Write-Host "`n[TEST 8] Checking pip and setuptools versions..." -ForegroundColor Yellow
$pipVersion = pip list | Select-String "^pip\s+"
$setuptoolsVersion = pip list | Select-String "^setuptools\s+"

if ($pipVersion -match "pip\s+(\d+\.\d+)") {
    $pipVer = [version]$matches[1]
    if ($pipVer -ge [version]"25.3") {
        Write-Host "  ✓ PASS: pip version OK ($pipVersion)" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ FAIL: pip version too old ($pipVersion). Upgrade to >= 25.3" -ForegroundColor Red
        $ErrorCount++
    }
}

if ($setuptoolsVersion -match "setuptools\s+(\d+\.\d+)") {
    $setupVer = [version]$matches[1]
    if ($setupVer -ge [version]"78.1") {
        Write-Host "  ✓ PASS: setuptools version OK ($setuptoolsVersion)" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ FAIL: setuptools version too old ($setuptoolsVersion). Upgrade to >= 78.1.1" -ForegroundColor Red
        $ErrorCount++
    }
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Errors: $ErrorCount" -ForegroundColor $(if ($ErrorCount -eq 0) { "Green" } else { "Red" })
Write-Host "Warnings: $WarningCount" -ForegroundColor $(if ($WarningCount -eq 0) { "Green" } else { "Yellow" })

if ($ErrorCount -eq 0) {
    Write-Host "`n✓ ALL CRITICAL TESTS PASSED" -ForegroundColor Green
    Write-Host "Security posture improved. Review warnings and continue with Phase 2 fixes." -ForegroundColor Green
    exit 0
}
else {
    Write-Host "`n✗ CRITICAL ISSUES FOUND" -ForegroundColor Red
    Write-Host "Fix errors before deploying to production." -ForegroundColor Red
    exit 1
}
