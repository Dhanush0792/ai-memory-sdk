# File Cleanup Script
# Removes duplicate, obsolete, and unnecessary files

Write-Host "🧹 AI Memory SDK - File Cleanup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "c:\Users\Desktop\Projects\memory"
Set-Location $projectRoot

# Files to delete (based on system audit)
$filesToDelete = @(
    # Duplicate SDKs (keep temporal_sdk.py only)
    "app\memory\sdk.py",
    
    # Old schemas (keep schema_tmg.sql only)
    "schema.sql",
    "schema_auth.sql",
    "schema_encryption.sql",
    "schema_encryption_fix.sql",
    
    # Duplicate landing pages (keep index.html)
    "landing_page.html",
    
    # Duplicate/obsolete documentation (consolidate into main docs)
    "ACTION_CHECKLIST.md",
    "AUTHENTICATION_COMPLETE.md",
    "AUTHENTICATION_IMPLEMENTATION.md",
    "BACKUPS_IMPLEMENTED.md",
    "BUG_FIXES_COMPLETE.md",
    "BUSINESS_STRATEGY.md",
    "COMPREHENSIVE_QA_REPORT.md",
    "DEPLOY_ALTERNATIVES.md",
    "DEPLOY_FINAL.md",
    "DEPLOY_NOW.md",
    "DEPLOY_TOMORROW.md",
    "ENCRYPTION_IMPLEMENTATION.md",
    "ESSENTIAL_FEATURES_COMPLETE.md",
    "FEATURES_COMPLETE.md",
    "GETTING_STARTED.md",
    "IMMEDIATE_ACTIONS_COMPLETE.md",
    "IMPLEMENT_CRITICAL_FEATURES.md",
    "INDEX.md",
    "NETLIFY_FIX.md",
    "QA_TEST_REPORT.md",
    "READY_TO_DEPLOY.md",
    "SUCCESS_REPORT.md",
    "SUMMARY.md",
    "TMG_README.md",
    "TODAY_COMPLETE.md",
    "VERCEL_DEPLOYMENT.md",
    
    # Keep these core docs:
    # - README.md (main)
    # - ARCHITECTURE.md
    # - DEPLOYMENT.md
    # - VERIFICATION.md
    # - SECURITY_AUDIT.md
    # - SECURITY_RUNBOOK.md
    # - SECURITY_SUMMARY.md
    # - INNOVATION_SUMMARY.md
    # - QUICKSTART.md
    # - CURL_TESTS.md
    # - PROJECT_STRUCTURE.md
    # - PRODUCTION_DEPLOYMENT.md
    # - PRODUCTION_READY.md
    # - REMAINING_WORK.md
    # - FINAL_STATUS.md
    # - ENTERPRISE_SYSTEM_REPORT.md
    # - ENTERPRISE_TRANSFORMATION_COMPLETE.md
    
    # Temporary/backup files
    "app\config.py"  # Replaced by app\config\settings.py
)

$deletedCount = 0
$notFoundCount = 0
$errors = @()

Write-Host "Files to delete:" -ForegroundColor Yellow
foreach ($file in $filesToDelete) {
    Write-Host "  - $file"
}
Write-Host ""

Write-Host "Proceeding with deletion..." -ForegroundColor Yellow
Write-Host ""

foreach ($file in $filesToDelete) {
    $fullPath = Join-Path $projectRoot $file
    
    if (Test-Path $fullPath) {
        try {
            Remove-Item $fullPath -Force
            Write-Host "✓ Deleted: $file" -ForegroundColor Green
            $deletedCount++
        }
        catch {
            Write-Host "✗ Error deleting $file : $_" -ForegroundColor Red
            $errors += $file
        }
    }
    else {
        Write-Host "⊘ Not found: $file" -ForegroundColor Gray
        $notFoundCount++
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Cleanup Summary:" -ForegroundColor Cyan
Write-Host "  Deleted: $deletedCount files" -ForegroundColor Green
Write-Host "  Not found: $notFoundCount files" -ForegroundColor Gray
if ($errors.Count -gt 0) {
    Write-Host "  Errors: $($errors.Count) files" -ForegroundColor Red
}
Write-Host ""

# Show remaining documentation files
Write-Host "Remaining core documentation:" -ForegroundColor Cyan
Get-ChildItem -Path $projectRoot -Filter "*.md" -File | Select-Object Name | Format-Table -AutoSize

Write-Host "✅ Cleanup complete!" -ForegroundColor Green
