#!/usr/bin/env python3
"""
Verify deployment and check strategy status on production VM
"""
import subprocess
import os

def run_ssh_command(command):
    """Run command on production VM"""
    try:
        result = subprocess.run(
            f'gcloud compute ssh ai-quant-trading-vm --zone=us-central1-a --command="{command}"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout, result.stderr
    except Exception as e:
        return None, str(e)

def main():
    print("=" * 80)
    print("VERIFYING DEPLOYMENT ON PRODUCTION VM")
    print("=" * 80)
    print()
    
    # Check service status
    print("1. Checking service status...")
    stdout, stderr = run_ssh_command("sudo systemctl is-active ai_trading.service")
    if stdout and "active" in stdout:
        print("   ✅ Service is running")
    else:
        print("   ❌ Service not running")
        print(f"   Output: {stdout}")
    
    # Check recent logs for strategy loading
    print()
    print("2. Checking strategy loading in logs...")
    stdout, stderr = run_ssh_command(
        "sudo journalctl -u ai_trading.service --since '10 minutes ago' --no-pager | "
        "grep -E '(Loaded strategy|Strategy has|generated.*signals)' | tail -30"
    )
    
    if stdout:
        print("   Recent strategy activity:")
        for line in stdout.strip().split('\n'):
            if line.strip():
                print(f"   {line}")
    else:
        print("   ⚠️  No strategy logs found")
    
    # Check for errors
    print()
    print("3. Checking for errors...")
    stdout, stderr = run_ssh_command(
        "sudo journalctl -u ai_trading.service --since '10 minutes ago' --no-pager | "
        "grep -iE '(error|failed|exception|traceback)' | tail -20"
    )
    
    if stdout and stdout.strip():
        print("   ⚠️  Errors found:")
        for line in stdout.strip().split('\n'):
            if line.strip():
                print(f"   {line}")
    else:
        print("   ✅ No errors found")
    
    # Check which strategies loaded
    print()
    print("4. Strategy loading summary...")
    stdout, stderr = run_ssh_command(
        "sudo journalctl -u ai_trading.service --since '10 minutes ago' --no-pager | "
        "grep 'Loaded strategy' | head -20"
    )
    
    if stdout:
        strategies_loaded = []
        for line in stdout.strip().split('\n'):
            if 'Loaded strategy' in line:
                strategies_loaded.append(line.strip())
        
        print(f"   Found {len(strategies_loaded)} strategy load messages:")
        for line in strategies_loaded[:10]:
            print(f"   {line}")
    else:
        print("   ⚠️  No strategy load messages found")
    
    print()
    print("=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()





