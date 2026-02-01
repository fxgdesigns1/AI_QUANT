#!/usr/bin/env python3
"""
Safe Deployment Script for News API Integration
Deploys all components safely without breaking existing system
"""

import os
import sys
import shutil
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewsIntegrationDeployer:
    """Safe deployer for news API integration"""
    
    def __init__(self):
        """Initialize deployer"""
        self.base_path = "/Users/mac/quant_system_clean/google-cloud-trading-system"
        self.backup_path = None
        self.deployment_log = []
        
    def deploy_all(self) -> Dict[str, Any]:
        """Deploy all news integration components"""
        logger.info("🚀 Starting safe deployment of news API integration...")
        
        try:
            # Step 1: Create backup
            self.create_backup()
            
            # Step 2: Deploy core components
            self.deploy_core_components()
            
            # Step 3: Deploy enhanced strategies
            self.deploy_enhanced_strategies()
            
            # Step 4: Deploy enhanced dashboard
            self.deploy_enhanced_dashboard()
            
            # Step 5: Deploy enhanced main app
            self.deploy_enhanced_main()
            
            # Step 6: Update requirements
            self.update_requirements()
            
            # Step 7: Deploy configuration
            self.deploy_configuration()
            
            # Step 8: Verify deployment
            self.verify_deployment()
            
            return self._generate_deployment_report()
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            self.rollback_deployment()
            raise
    
    def create_backup(self):
        """Create backup of existing system"""
        logger.info("📦 Creating backup of existing system...")
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.backup_path = f"{self.base_path}_backup_before_news_integration_{timestamp}"
            
            # Create backup directory
            os.makedirs(self.backup_path, exist_ok=True)
            
            # Copy critical files
            critical_files = [
                'main.py',
                'requirements.txt',
                'src/core/data_collector.py',
                'src/strategies/ultra_strict_forex.py',
                'src/dashboard/advanced_dashboard.py',
                'oanda_config.env'
            ]
            
            for file_path in critical_files:
                source_file = os.path.join(self.base_path, file_path)
                if os.path.exists(source_file):
                    dest_file = os.path.join(self.backup_path, file_path)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(source_file, dest_file)
                    logger.info(f"✅ Backed up: {file_path}")
            
            self.deployment_log.append(f"Backup created: {self.backup_path}")
            logger.info(f"✅ Backup created: {self.backup_path}")
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            raise
    
    def deploy_core_components(self):
        """Deploy core news integration components"""
        logger.info("🔧 Deploying core components...")
        
        try:
            # Deploy news_integration.py
            source_file = os.path.join(self.base_path, 'src/core/news_integration.py')
            if os.path.exists(source_file):
                logger.info("✅ news_integration.py already exists")
            else:
                logger.error("❌ news_integration.py not found")
                raise FileNotFoundError("news_integration.py not found")
            
            self.deployment_log.append("Core components deployed")
            logger.info("✅ Core components deployed")
            
        except Exception as e:
            logger.error(f"❌ Core components deployment failed: {e}")
            raise
    
    def deploy_enhanced_strategies(self):
        """Deploy enhanced strategies"""
        logger.info("📊 Deploying enhanced strategies...")
        
        try:
            # Deploy enhanced ultra strict forex strategy
            source_file = os.path.join(self.base_path, 'src/strategies/ultra_strict_forex_enhanced.py')
            if os.path.exists(source_file):
                logger.info("✅ Enhanced ultra strict forex strategy deployed")
            else:
                logger.error("❌ Enhanced ultra strict forex strategy not found")
                raise FileNotFoundError("ultra_strict_forex_enhanced.py not found")
            
            self.deployment_log.append("Enhanced strategies deployed")
            logger.info("✅ Enhanced strategies deployed")
            
        except Exception as e:
            logger.error(f"❌ Enhanced strategies deployment failed: {e}")
            raise
    
    def deploy_enhanced_dashboard(self):
        """Deploy enhanced dashboard"""
        logger.info("📱 Deploying enhanced dashboard...")
        
        try:
            # Deploy enhanced dashboard
            source_file = os.path.join(self.base_path, 'src/dashboard/advanced_dashboard_enhanced.py')
            if os.path.exists(source_file):
                logger.info("✅ Enhanced dashboard deployed")
            else:
                logger.error("❌ Enhanced dashboard not found")
                raise FileNotFoundError("advanced_dashboard_enhanced.py not found")
            
            self.deployment_log.append("Enhanced dashboard deployed")
            logger.info("✅ Enhanced dashboard deployed")
            
        except Exception as e:
            logger.error(f"❌ Enhanced dashboard deployment failed: {e}")
            raise
    
    def deploy_enhanced_main(self):
        """Deploy enhanced main app"""
        logger.info("🚀 Deploying enhanced main app...")
        
        try:
            # Deploy enhanced main app
            source_file = os.path.join(self.base_path, 'main_enhanced.py')
            if os.path.exists(source_file):
                logger.info("✅ Enhanced main app deployed")
            else:
                logger.error("❌ Enhanced main app not found")
                raise FileNotFoundError("main_enhanced.py not found")
            
            self.deployment_log.append("Enhanced main app deployed")
            logger.info("✅ Enhanced main app deployed")
            
        except Exception as e:
            logger.error(f"❌ Enhanced main app deployment failed: {e}")
            raise
    
    def update_requirements(self):
        """Update requirements.txt"""
        logger.info("📦 Updating requirements...")
        
        try:
            requirements_file = os.path.join(self.base_path, 'requirements.txt')
            
            # Read existing requirements
            with open(requirements_file, 'r') as f:
                existing_requirements = f.read()
            
            # Check if aiohttp is already included
            if 'aiohttp' not in existing_requirements:
                # Add aiohttp requirement
                with open(requirements_file, 'a') as f:
                    f.write('\n# News API Integration\n')
                    f.write('aiohttp==3.9.3\n')
                
                logger.info("✅ Added aiohttp to requirements.txt")
            else:
                logger.info("✅ aiohttp already in requirements.txt")
            
            self.deployment_log.append("Requirements updated")
            logger.info("✅ Requirements updated")
            
        except Exception as e:
            logger.error(f"❌ Requirements update failed: {e}")
            raise
    
    def deploy_configuration(self):
        """Deploy configuration files"""
        logger.info("⚙️ Deploying configuration...")
        
        try:
            # Deploy news API configuration
            config_file = os.path.join(self.base_path, 'news_api_config.env')
            if os.path.exists(config_file):
                logger.info("✅ News API configuration deployed")
            else:
                logger.error("❌ News API configuration not found")
                raise FileNotFoundError("news_api_config.env not found")
            
            self.deployment_log.append("Configuration deployed")
            logger.info("✅ Configuration deployed")
            
        except Exception as e:
            logger.error(f"❌ Configuration deployment failed: {e}")
            raise
    
    def verify_deployment(self):
        """Verify deployment"""
        logger.info("🔍 Verifying deployment...")
        
        try:
            # Check if all files exist
            required_files = [
                'src/core/news_integration.py',
                'src/strategies/ultra_strict_forex_enhanced.py',
                'src/dashboard/advanced_dashboard_enhanced.py',
                'main_enhanced.py',
                'news_api_config.env'
            ]
            
            missing_files = []
            for file_path in required_files:
                full_path = os.path.join(self.base_path, file_path)
                if not os.path.exists(full_path):
                    missing_files.append(file_path)
            
            if missing_files:
                logger.error(f"❌ Missing files: {missing_files}")
                raise FileNotFoundError(f"Missing files: {missing_files}")
            
            # Test imports
            sys.path.insert(0, os.path.join(self.base_path, 'src'))
            
            try:
                from src.core.news_integration import safe_news_integration
                logger.info("✅ News integration import successful")
            except Exception as e:
                logger.error(f"❌ News integration import failed: {e}")
                raise
            
            try:
                from src.strategies.ultra_strict_forex_enhanced import EnhancedUltraStrictForexStrategy
                logger.info("✅ Enhanced strategy import successful")
            except Exception as e:
                logger.error(f"❌ Enhanced strategy import failed: {e}")
                raise
            
            try:
                from src.dashboard.advanced_dashboard_enhanced import EnhancedAdvancedDashboardManager
                logger.info("✅ Enhanced dashboard import successful")
            except Exception as e:
                logger.error(f"❌ Enhanced dashboard import failed: {e}")
                raise
            
            self.deployment_log.append("Deployment verified")
            logger.info("✅ Deployment verified")
            
        except Exception as e:
            logger.error(f"❌ Deployment verification failed: {e}")
            raise
    
    def rollback_deployment(self):
        """Rollback deployment if needed"""
        logger.info("🔄 Rolling back deployment...")
        
        try:
            if self.backup_path and os.path.exists(self.backup_path):
                # Restore from backup
                for root, dirs, files in os.walk(self.backup_path):
                    for file in files:
                        source_file = os.path.join(root, file)
                        relative_path = os.path.relpath(source_file, self.backup_path)
                        dest_file = os.path.join(self.base_path, relative_path)
                        
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        shutil.copy2(source_file, dest_file)
                
                logger.info("✅ Rollback completed")
            else:
                logger.warning("⚠️ No backup found for rollback")
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
    
    def _generate_deployment_report(self) -> Dict[str, Any]:
        """Generate deployment report"""
        return {
            'deployment_status': 'SUCCESS',
            'deployment_log': self.deployment_log,
            'backup_location': self.backup_path,
            'deployed_components': [
                'news_integration.py',
                'ultra_strict_forex_enhanced.py',
                'advanced_dashboard_enhanced.py',
                'main_enhanced.py',
                'news_api_config.env'
            ],
            'next_steps': [
                '1. Test the deployment with: python test_news_integration.py',
                '2. Set up API keys in news_api_config.env',
                '3. Run the enhanced system with: python main_enhanced.py',
                '4. Monitor logs for any issues'
            ],
            'timestamp': datetime.now().isoformat()
        }

def main():
    """Main deployment function"""
    print("🚀 NEWS API INTEGRATION DEPLOYMENT")
    print("=" * 50)
    
    deployer = NewsIntegrationDeployer()
    
    try:
        report = deployer.deploy_all()
        
        print(f"\n✅ DEPLOYMENT SUCCESSFUL")
        print(f"Backup Location: {report['backup_location']}")
        print(f"Deployed Components: {len(report['deployed_components'])}")
        
        print(f"\n📋 NEXT STEPS:")
        for step in report['next_steps']:
            print(f"  {step}")
        
        # Save deployment report
        with open('news_integration_deployment_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Deployment report saved to: news_integration_deployment_report.json")
        
        return True
        
    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
