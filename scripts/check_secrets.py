#!/usr/bin/env python3
"""
Secret Scanner - Detects exposed API keys and sensitive data
Part of Security Hardening Phase
"""

import re
import sys
import os
from pathlib import Path
from typing import List, Tuple

# Patterns to detect
SECRET_PATTERNS = {
    "Gemini API Key": r"AIza[0-9A-Za-z\-_]{35}",
    "OpenAI API Key": r"sk-[a-zA-Z0-9]{20,}",
    "Anthropic API Key": r"sk-ant-[a-zA-Z0-9\-_]{95,}",
    "Generic API Key": r"(?i)(api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*['\"]?[a-zA-Z0-9\-_]{20,}['\"]?",
    "AWS Access Key": r"AKIA[0-9A-Z]{16}",
    "GitHub Token": r"ghp_[0-9a-zA-Z]{36}",
    "Private Key": r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
    "Database URL with Password": r"postgresql://[^:]+:[^@]+@",
}

# Files/directories to exclude
EXCLUDE_PATTERNS = [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".env.example",  # Example files are OK
    "check_secrets.py",  # This script itself
]

# File extensions to scan
SCAN_EXTENSIONS = [
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
    ".yml", ".yaml", ".json", ".md", ".txt", ".sh",
    ".dockerfile", ".env", ".toml", ".ini", ".cfg"
]


def should_scan_file(file_path: Path) -> bool:
    """Determine if file should be scanned."""
    # Check if in excluded directory
    for exclude in EXCLUDE_PATTERNS:
        if exclude in str(file_path):
            return False
    
    # Check extension
    if file_path.suffix.lower() in SCAN_EXTENSIONS or file_path.name in ["Dockerfile", "docker-compose.yml"]:
        return True
    
    return False


def scan_file(file_path: Path) -> List[Tuple[str, int, str, str]]:
    """
    Scan a file for secrets.
    Returns list of (pattern_name, line_number, line_content, matched_text)
    """
    findings = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                for pattern_name, pattern in SECRET_PATTERNS.items():
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        findings.append((
                            pattern_name,
                            line_num,
                            line.strip(),
                            match.group(0)
                        ))
    except Exception as e:
        print(f"Warning: Could not scan {file_path}: {e}", file=sys.stderr)
    
    return findings


def scan_directory(root_dir: Path) -> dict:
    """Scan entire directory tree."""
    all_findings = {}
    
    for file_path in root_dir.rglob("*"):
        if file_path.is_file() and should_scan_file(file_path):
            findings = scan_file(file_path)
            if findings:
                all_findings[str(file_path.relative_to(root_dir))] = findings
    
    return all_findings


def print_findings(findings: dict) -> int:
    """Print findings in a readable format. Returns number of critical findings."""
    if not findings:
        print("✅ No secrets detected!")
        return 0
    
    print("🚨 SECURITY ALERT: Secrets detected!\n")
    
    critical_count = 0
    for file_path, file_findings in findings.items():
        print(f"\n📄 {file_path}")
        for pattern_name, line_num, line_content, matched_text in file_findings:
            critical_count += 1
            # Redact the actual secret
            redacted = matched_text[:8] + "..." + matched_text[-4:] if len(matched_text) > 12 else "***REDACTED***"
            print(f"  Line {line_num}: {pattern_name}")
            print(f"    Pattern: {redacted}")
            print(f"    Context: {line_content[:80]}...")
    
    print(f"\n❌ Total findings: {critical_count}")
    return critical_count


def main():
    """Main entry point."""
    # Get repository root (parent of scripts directory)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    print(f"🔍 Scanning repository: {repo_root}")
    print(f"📋 Scanning {len(SCAN_EXTENSIONS)} file types")
    print(f"🚫 Excluding: {', '.join(EXCLUDE_PATTERNS)}\n")
    
    findings = scan_directory(repo_root)
    critical_count = print_findings(findings)
    
    if critical_count > 0:
        print("\n⚠️  ACTION REQUIRED:")
        print("  1. Remove all secrets from tracked files")
        print("  2. Move secrets to .env file")
        print("  3. Ensure .env is in .gitignore")
        print("  4. If secrets were committed, revoke and rotate them immediately")
        sys.exit(1)
    else:
        print("\n✅ Repository is clean - no secrets detected")
        sys.exit(0)


if __name__ == "__main__":
    main()
