#!/usr/bin/env python3
"""
Rural Banking Security Framework Startup Script
Lightweight cybersecurity framework for rural banking transactions
"""

import os
import sys
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('banking_app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'flask', 'bcrypt', 'cryptography', 'twilio', 'gtts', 
        'numpy', 'psutil', 'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing required packages: {', '.join(missing_packages)}")
        logger.info("Please install missing packages using:")
        logger.info(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_optional_dependencies():
    """Check optional ML dependencies"""
    optional_packages = ['tensorflow', 'huggingface_hub', 'scikit-learn']
    
    for package in optional_packages:
        try:
            __import__(package)
            logger.info(f"✅ Optional package {package} is available")
        except ImportError:
            logger.warning(f"⚠️ Optional package {package} not found - ML features may be limited")

def initialize_security_framework():
    """Initialize the security framework"""
    try:
        from security.core import security_core, security_audit
        from security.offline_security import offline_manager
        from security.performance import start_performance_monitoring
        
        logger.info("🔐 Initializing security framework...")
        
        # Start offline transaction manager
        offline_manager.start_sync_service()
        logger.info("📱 Offline transaction manager started")
        
        # Start performance monitoring
        start_performance_monitoring()
        logger.info("📊 Performance monitoring started")
        
        # Log initialization
        security_audit.log_security_event(
            'SYSTEM_STARTUP',
            'system',
            {'timestamp': time.time(), 'status': 'success'}
        )
        
        logger.info("✅ Security framework initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize security framework: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['logs', 'temp', 'backups']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"📁 Created directory: {directory}")

def display_banner():
    """Display application banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║        🏦 RURAL BANKING SECURITY FRAMEWORK 🛡️                ║
    ║                                                              ║
    ║        Lightweight Cybersecurity for Rural Banking          ║
    ║        • Advanced Fraud Detection                           ║
    ║        • Multi-Factor Authentication                        ║
    ║        • Offline Transaction Support                        ║
    ║        • Performance Optimized for Low-End Devices         ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def display_system_info():
    """Display system information"""
    try:
        from security.performance import resource_manager
        
        system_info = resource_manager.get_system_info()
        
        logger.info("💻 System Information:")
        logger.info(f"   CPU Cores: {system_info.get('cpu_count', 'Unknown')}")
        logger.info(f"   Total Memory: {system_info.get('total_memory_gb', 0):.1f} GB")
        logger.info(f"   Available Memory: {system_info.get('available_memory_gb', 0):.1f} GB")
        logger.info(f"   Memory Usage: {system_info.get('memory_usage_percent', 0):.1f}%")
        logger.info(f"   Free Disk Space: {system_info.get('free_disk_gb', 0):.1f} GB")
        
    except Exception as e:
        logger.warning(f"Could not get system information: {e}")

def run_security_tests():
    """Run basic security tests"""
    try:
        logger.info("🧪 Running security tests...")
        
        from security.core import security_core
        
        # Test encryption
        test_data = "test_encryption_data"
        encrypted = security_core.encrypt_data(test_data)
        decrypted = security_core.decrypt_data(encrypted)
        
        if decrypted == test_data:
            logger.info("✅ Encryption/Decryption test passed")
        else:
            logger.error("❌ Encryption/Decryption test failed")
            return False
        
        # Test password hashing
        test_password = "test123"
        hash_value, salt = security_core.hash_password(test_password)
        
        if security_core.verify_password(test_password, hash_value, salt):
            logger.info("✅ Password hashing test passed")
        else:
            logger.error("❌ Password hashing test failed")
            return False
        
        logger.info("✅ All security tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Security tests failed: {e}")
        return False

def start_application():
    """Start the Flask application"""
    try:
        from app import app
        
        logger.info("🚀 Starting Rural Banking Application...")
        logger.info("📱 Application will be available at:")
        logger.info("   • Main App: http://127.0.0.1:5000")
        logger.info("   • Security Dashboard: http://127.0.0.1:5000/admin")
        logger.info("   • Fraud Monitor: http://127.0.0.1:5001 (if running fraud.py separately)")
        
        # Start the application
        app.run(
            host='0.0.0.0',  # Allow external connections
            port=5000,
            debug=False,  # Disable debug mode for security
            threaded=True  # Enable threading for better performance
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        return False

def main():
    """Main startup function"""
    display_banner()
    
    logger.info("🔄 Starting Rural Banking Security Framework...")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("❌ Dependency check failed. Please install required packages.")
        sys.exit(1)
    
    check_optional_dependencies()
    
    # Create necessary directories
    create_directories()
    
    # Display system information
    display_system_info()
    
    # Initialize security framework
    if not initialize_security_framework():
        logger.error("❌ Security framework initialization failed.")
        sys.exit(1)
    
    # Run security tests
    if not run_security_tests():
        logger.error("❌ Security tests failed.")
        sys.exit(1)
    
    logger.info("✅ All initialization checks passed")
    logger.info("🎯 Target: 20% fraud reduction for rural banking")
    logger.info("🔒 Enhanced security features enabled")
    logger.info("📱 Optimized for low-end smartphones")
    logger.info("🌐 Offline transaction support available")
    
    # Start the application
    try:
        start_application()
    except KeyboardInterrupt:
        logger.info("🛑 Application stopped by user")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
