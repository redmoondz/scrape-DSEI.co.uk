#!/usr/bin/env python3
"""
Setup and run script for DSEI Company Scraper
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def run_verification():
    """Run the verification script"""
    print("\n🔍 Running verification tests...")
    try:
        result = subprocess.run([sys.executable, "verify_scraper.py"], 
                              capture_output=True, text=True, timeout=60)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Verification timed out")
        return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def run_test():
    """Run a quick test"""
    print("\n🧪 Running quick test (1 page)...")
    try:
        result = subprocess.run([sys.executable, "test_scraper.py"], 
                              capture_output=True, text=True, timeout=120)
        
        print(result.stdout)
        if result.stderr:
            print("Warnings/Errors:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def run_full_scraper():
    """Run the full scraper"""
    print("\n🚀 Starting full scraper...")
    print("This will collect all companies from DSEI.co.uk")
    print("Press Ctrl+C to stop at any time")
    
    try:
        subprocess.run([sys.executable, "dsei_scraper.py"])
        print("✅ Scraping completed!")
        
        # Check if CSV was created
        if os.path.exists("dsei_companies.csv"):
            print("📄 Output file created: dsei_companies.csv")
        
        return True
    except KeyboardInterrupt:
        print("\n⏹️ Scraping stopped by user")
        return False
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return False

def main():
    """Main setup and run function"""
    print("DSEI Company Scraper Setup")
    print("=" * 30)
    
    # Check if we're in the right directory
    if not os.path.exists("dsei_scraper.py"):
        print("❌ Error: dsei_scraper.py not found in current directory")
        print("Please make sure you're in the correct project directory")
        return
    
    print("Choose an option:")
    print("1. Install requirements only")
    print("2. Install requirements + run verification")
    print("3. Install requirements + run quick test")
    print("4. Install requirements + run full scraper")
    print("5. Just run verification (requirements must be installed)")
    print("6. Just run quick test (requirements must be installed)")
    print("7. Just run full scraper (requirements must be installed)")
    
    choice = input("\nEnter your choice (1-7): ").strip()
    
    if choice == "1":
        install_requirements()
    
    elif choice == "2":
        if install_requirements():
            run_verification()
    
    elif choice == "3":
        if install_requirements():
            if run_verification():
                run_test()
    
    elif choice == "4":
        if install_requirements():
            if run_verification():
                confirm = input("\nReady to start full scraping? This may take a while. (y/N): ")
                if confirm.lower() in ['y', 'yes']:
                    run_full_scraper()
                else:
                    print("Cancelled.")
    
    elif choice == "5":
        run_verification()
    
    elif choice == "6":
        run_test()
    
    elif choice == "7":
        confirm = input("Ready to start full scraping? This may take a while. (y/N): ")
        if confirm.lower() in ['y', 'yes']:
            run_full_scraper()
        else:
            print("Cancelled.")
    
    else:
        print("Invalid choice. Please run the script again.")

if __name__ == "__main__":
    main()
