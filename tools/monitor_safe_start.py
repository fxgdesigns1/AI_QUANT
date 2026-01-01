#!/usr/bin/env python3
"""
Single-instance monitor launcher for monitor_until.py.
"""
import os
import time
import subprocess
import fcntl
import logging

LOG_PATH = "/tmp/monitor_safe_start.log"
LOCK_PATH = "/tmp/monitor_once.lock"
MONITOR_PATH = "/opt/quant_system_clean/google-cloud-trading-system/tools/monitor_until.py"

def acquire_lock():
    try:
        lock_file = open(LOCK_PATH, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except BlockingIOError:
        return None

def is_monitor_running():
    try:
        output = subprocess.check_output(["ps","-eo","pid,cmd"], text=True)
        for line in output.splitlines():
            if "monitor_until.py" in line and "grep" not in line:
                return True
        return False
    except Exception:
        return False

def start_monitor():
    cmd = f"nohup python3 {MONITOR_PATH} >/tmp/monitor_until.log 2>&1 &"
    subprocess.Popen(cmd, shell=True)

def main():
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    lock = acquire_lock()
    if lock is None:
        logger.info("Another monitor instance is already running. Exiting.")
        return 0
    try:
        if not is_monitor_running():
            logger.info("Starting monitor_once: launching monitor_until.py")
            start_monitor()
            time.sleep(2)
        else:
            logger.info("monitor_until.py already running.")
    finally:
        # The lock will be released when the process ends; here we keep the lock until exit
        pass

if __name__ == "__main__":
    main()






























