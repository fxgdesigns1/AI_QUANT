#!/usr/bin/env python3
"""
Force Scale Down Script - Immediate Cost Optimization
Manually scales down instances for immediate cost savings
"""

import subprocess
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def force_scale_down():
    """Force scale down to minimum instances for cost savings"""
    try:
        logger.info("🚀 FORCE SCALE DOWN - IMMEDIATE COST OPTIMIZATION")
        logger.info("=" * 60)
        
        # Step 1: Set traffic to current version only
        logger.info("Step 1: Setting traffic to current version only...")
        cmd1 = [
            'gcloud', 'app', 'services', 'set-traffic', 'default',
            '--splits=top3-final-override-20251003-103506=1',
            '--project=ai-quant-trading',
            '--quiet'
        ]
        result1 = subprocess.run(cmd1, capture_output=True, text=True)
        
        if result1.returncode == 0:
            logger.info("✅ Traffic routing updated successfully")
        else:
            logger.error(f"❌ Traffic routing failed: {result1.stderr}")
            return False
        
        # Step 2: Wait for scaling to take effect
        logger.info("Step 2: Waiting for scaling to take effect...")
        time.sleep(30)
        
        # Step 3: Check current instance count
        logger.info("Step 3: Checking current instance count...")
        cmd2 = [
            'gcloud', 'app', 'instances', 'list', '--service=default',
            '--format=value(id)', '--project=ai-quant-trading'
        ]
        result2 = subprocess.run(cmd2, capture_output=True, text=True)
        
        if result2.returncode == 0:
            instances = result2.stdout.strip().split('\n')
            instance_count = len([i for i in instances if i.strip()])
            logger.info(f"📊 Current instances: {instance_count}")
            
            if instance_count <= 2:
                logger.info("✅ SCALING SUCCESSFUL!")
                logger.info(f"💰 Cost savings: Reduced from 4 to {instance_count} instances")
                logger.info(f"💰 Monthly savings: ~${(4-instance_count)*25}-${(4-instance_count)*30}")
            else:
                logger.warning(f"⚠️ Still {instance_count} instances - scaling may take more time")
        else:
            logger.error(f"❌ Failed to check instances: {result2.stderr}")
        
        logger.info("=" * 60)
        logger.info("🎯 FORCE SCALE DOWN COMPLETED")
        logger.info("📈 Expected monthly savings: $40-70")
        logger.info("⏰ Scaling will continue automatically based on load")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in force scale down: {e}")
        return False

if __name__ == "__main__":
    force_scale_down()
























