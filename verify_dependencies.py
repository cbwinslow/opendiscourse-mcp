#!/usr/bin/env python3
"""
Verify dependencies installation for OpenDiscourse
"""

import os
import sys
import subprocess
import importlib
import pkg_resources

def check_python_package(package_name, import_name=None, version_attribute=None):
    """Check if a Python package is installed and get version"""
    if import_name is None:
        import_name = package_name
    
    try:
        # Try to import the package
        module = importlib.import_module(import_name)
        
        # Get version if possible
        version = "Unknown"
        if version_attribute and hasattr(module, version_attribute):
            version = getattr(module, version_attribute)
        elif hasattr(module, '__version__'):
            version = module.__version__
        elif hasattr(module, 'version'):
            version = module.version
        else:
            # Try pkg_resources
            try:
                version = pkg_resources.get_distribution(package_name).version
            except:
                pass
        
        return True, version
        
    except ImportError:
        return False, "Not installed"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_system_command(command):
    """Check if a system command is available"""
    try:
        result = subprocess.run(
            ['which', command], 
            capture_output=True, 
            text=True
        )
        return result.returncode == 0
    except:
        return False

def get_system_command_version(command, version_flag="--version"):
    """Get version of a system command"""
    try:
        result = subprocess.run(
            [command, version_flag], 
            capture_output=True, 
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip() or result.stderr.strip()
        else:
            return "Version check failed"
    except:
        return "Unknown"

def verify_dependencies():
    """Comprehensive dependency verification"""
    print("🔍 DEPENDENCY VERIFICATION FOR OPENDISCOURSE")
    print("=" * 60)
    
    # Check Python version
    print("\n🐍 Python Environment:")
    python_version = sys.version
    print(f"  Python Version: {python_version}")
    print(f"  Python Path: {sys.executable}")
    
    # Check critical Python packages
    print("\n📦 Critical Python Packages:")
    
    critical_packages = [
        ("psycopg2-binary", "psycopg2", None),
        ("sqlalchemy", "sqlalchemy", "__version__"),
        ("pandas", "pandas", "__version__"),
        ("requests", "requests", "__version__"),
        ("python-dotenv", "dotenv", "__version__"),
        ("beautifulsoup4", "bs4", "__version__"),
        ("lxml", "lxml", "__version__"),
    ]
    
    missing_critical = []
    for package, import_name, version_attr in critical_packages:
        installed, version = check_python_package(package, import_name, version_attr)
        status = "✅" if installed else "❌"
        print(f"  {status} {package:20} {version}")
        if not installed:
            missing_critical.append(package)
    
    # Check optional Python packages
    print("\n📦 Optional Python Packages:")
    
    optional_packages = [
        ("numpy", "numpy", "__version__"),
        ("matplotlib", "matplotlib", "__version__"),
        ("seaborn", "seaborn", "__version__"),
        ("jupyter", "jupyter", "__version__"),
        ("pytest", "pytest", "__version__"),
        ("black", "black", "__version__"),
        ("flake8", "flake8", "__version__"),
    ]
    
    missing_optional = []
    for package, import_name, version_attr in optional_packages:
        installed, version = check_python_package(package, import_name, version_attr)
        status = "✅" if installed else "⚠️"
        print(f"  {status} {package:20} {version}")
        if not installed:
            missing_optional.append(package)
    
    # Check system dependencies
    print("\n🖥️  System Dependencies:")
    
    system_commands = [
        ("postgresql", "psql"),
        ("git", "git"),
        ("curl", "curl"),
        ("wget", "wget"),
        ("python3-pip", "pip3"),
    ]
    
    missing_system = []
    for name, command in system_commands:
        available = check_system_command(command)
        if available:
            version = get_system_command_version(command)
            print(f"  ✅ {command:15} {version}")
        else:
            print(f"  ❌ {command:15} Not found")
            missing_system.append(name)
    
    # Check database connectivity
    print("\n🗄️  Database Connectivity:")
    try:
        source_env_file()
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            import psycopg2
            conn = psycopg2.connect(db_url)
            conn.close()
            print("  ✅ PostgreSQL connection working")
        else:
            print("  ❌ DATABASE_URL not set")
            missing_critical.append("DATABASE_URL")
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        missing_critical.append("Database connection")
    
    # Check project structure
    print("\n📁 Project Structure:")
    
    required_dirs = [
        "/home/cbwinslow/opendiscourse/mcp_server",
        "/home/cbwinslow/opendiscourse/mcp_server/clients", 
        "/home/cbwinslow/opendiscourse/mcp_server/scripts",
        "/home/cbwinslow/opendiscourse/mcp_server/sql",
        "/home/cbwinslow/opendiscourse/tests",
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"  ✅ {dir_path}")
        else:
            print(f"  ❌ {dir_path}")
            missing_dirs.append(dir_path)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DEPENDENCY VERIFICATION SUMMARY:")
    
    # Critical issues
    critical_issues = len(missing_critical) + len(missing_system) + len(missing_dirs)
    
    if critical_issues == 0:
        print("🎉 ALL CRITICAL DEPENDENCIES INSTALLED!")
        print("✅ System is ready for production use")
    else:
        print("⚠️  CRITICAL ISSUES FOUND:")
        
        if missing_critical:
            print(f"\n  Missing Python Packages:")
            for pkg in missing_critical:
                print(f"    - {pkg}")
        
        if missing_system:
            print(f"\n  Missing System Packages:")
            for pkg in missing_system:
                print(f"    - {pkg}")
        
        if missing_dirs:
            print(f"\n  Missing Directories:")
            for dir_path in missing_dirs:
                print(f"    - {dir_path}")
    
    # Optional packages
    if missing_optional:
        print(f"\n📝 Optional Packages Not Installed:")
        for pkg in missing_optional:
            print(f"    - {pkg}")
        print("  (These are optional but recommended for development)")
    
    # Installation commands
    if missing_critical or missing_system:
        print(f"\n🔧 INSTALLATION COMMANDS:")
        
        if missing_critical:
            print("  Python Packages:")
            print("    pip install psycopg2-binary sqlalchemy pandas requests")
            print("    pip install python-dotenv beautifulsoup4 lxml")
        
        if missing_system:
            print("  System Packages (Ubuntu/Debian):")
            print("    sudo apt update")
            print("    sudo apt install postgresql postgresql-contrib")
            print("    sudo apt install git curl wget python3-pip")
    
    # Overall status
    print(f"\n🎯 OVERALL STATUS:")
    total_critical = len(critical_packages) + len(system_commands) + len(required_dirs)
    installed_critical = total_critical - critical_issues
    completion_rate = (installed_critical / total_critical) * 100
    
    print(f"  Critical Dependencies: {installed_critical}/{total_critical} ({completion_rate:.1f}%)")
    print(f"  Optional Packages: {len(optional_packages) - len(missing_optional)}/{len(optional_packages)}")
    
    if completion_rate >= 95:
        print("  🎉 EXCELLENT - Fully operational!")
        return 0
    elif completion_rate >= 80:
        print("  ✅ GOOD - Mostly functional")
        return 0
    else:
        print("  ❌ NEEDS WORK - Install missing dependencies")
        return 1

def source_env_file():
    """Source .env file"""
    env_file = "/home/cbwinslow/opendiscourse/mcp_server/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.startswith('export '):
                        key = key[7:]
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value

if __name__ == "__main__":
    sys.exit(verify_dependencies())