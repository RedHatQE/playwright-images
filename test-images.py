#!/usr/bin/env python3
"""
Test script for Playwright VNC images
Tests all image variants to ensure they work correctly

Requirements:
  pip install playwright
  playwright install  # Not needed for client-only connection
"""

import subprocess
import time
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: Playwright is not installed!")
    print("Install with: pip install playwright")
    print("Note: You don't need to run 'playwright install' for testing remote connections")
    sys.exit(1)

# Configuration
REPO = "digitronik/playwright-vnc"
VNC_PORT = 5900
PW_PORT = 3000
TEST_URL = "https://example.com"
TEST_TIMEOUT = 30  # seconds

# Define all images to test
IMAGES = {
    "bookworm": {
        "all": {"browsers": ["firefox", "chromium", "chrome"], "default": "chromium"},
        "firefox": {"browsers": ["firefox"], "default": "firefox"},
        "chromium": {"browsers": ["chromium"], "default": "chromium"},
        "chrome": {"browsers": ["chrome"], "default": "chrome"},
    },
    "ubi9": {
        "all": {"browsers": ["firefox", "chromium", "chrome"], "default": "chromium"},
        "firefox": {"browsers": ["firefox"], "default": "firefox"},
        "chromium": {"browsers": ["chromium"], "default": "chromium"},
        "chrome": {"browsers": ["chrome"], "default": "chrome"},
    }
}

class Colors:
    """ANSI color codes"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(message):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{message}{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(message):
    print(f"{Colors.GREEN}✓{Colors.END} {message}")

def print_error(message):
    print(f"{Colors.RED}✗{Colors.END} {message}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ{Colors.END} {message}")

def start_container(image_tag, browser=None):
    """Start a container and return container ID"""
    cmd = [
        "podman", "run", "--rm", "-d",
        "-p", f"{VNC_PORT}:5900",
        "-p", f"{PW_PORT}:3000",
        "--name", f"pw-test-{int(time.time())}"
    ]
    
    if browser:
        cmd.extend(["-e", f"PW_BROWSER={browser}"])
    
    cmd.append(image_tag)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            container_id = result.stdout.strip()
            return container_id
        else:
            print_error(f"Failed to start container: {result.stderr}")
            return None
    except Exception as e:
        print_error(f"Exception starting container: {e}")
        return None

def stop_container(container_id):
    """Stop and remove a container"""
    try:
        subprocess.run(["podman", "stop", container_id], 
                      capture_output=True, timeout=10)
        subprocess.run(["podman", "rm", container_id], 
                      capture_output=True, timeout=10)
    except Exception as e:
        print_error(f"Error stopping container: {e}")

def test_browser(browser_type, expected_title="Example Domain"):
    """Test a specific browser by connecting via Playwright"""
    try:
        with sync_playwright() as p:
            # Connect based on browser type (use 127.0.0.1 for reliability)
            if browser_type == "firefox":
                browser = p.firefox.connect(f"ws://127.0.0.1:{PW_PORT}/playwright", timeout=15000)
            elif browser_type in ["chromium", "chrome"]:
                browser = p.chromium.connect(f"ws://127.0.0.1:{PW_PORT}/playwright", timeout=15000)
            else:
                print_error(f"Unknown browser type: {browser_type}")
                return False
            
            # Create a new page and navigate
            page = browser.new_page()
            page.goto(TEST_URL, wait_until="domcontentloaded", timeout=10000)
            
            # Verify page loaded
            title = page.title()
            url = page.url
            
            # Get browser info to verify correct browser is running
            user_agent = page.evaluate("navigator.userAgent")
            
            # Verify correct browser type
            browser_match = False
            if browser_type == "firefox":
                browser_match = "Firefox" in user_agent
                browser_name = "Firefox"
            elif browser_type == "chromium":
                browser_match = "Chrome" in user_agent and "Edg" not in user_agent
                browser_name = "Chromium"
            elif browser_type == "chrome":
                browser_match = "Chrome" in user_agent
                browser_name = "Chrome"
            
            browser.close()
            
            # Validate title
            if expected_title.lower() not in title.lower():
                print_error(f"{browser_type}: Unexpected title: {title}")
                return False
            
            # Validate browser type
            if not browser_match:
                print_error(f"{browser_type}: Wrong browser detected!")
                print_info(f"  Expected: {browser_name}")
                print_info(f"  User-Agent: {user_agent}")
                return False
            
            print_success(f"{browser_type}: Page loaded successfully")
            print_info(f"  Title: {title}")
            print_info(f"  URL: {url}")
            print_info(f"  Browser: {browser_name} ✓")
            return True
                
    except Exception as e:
        print_error(f"{browser_type}: {str(e)}")
        return False

def test_image(base, target):
    """Test a specific image variant"""
    if target == "all":
        image_tag = f"{REPO}:{base}-latest"
    else:
        image_tag = f"{REPO}:{base}-{target}-latest"
    
    config = IMAGES[base][target]
    browsers_to_test = config["browsers"]
    
    print_header(f"Testing: {base}/{target}")
    print_info(f"Image: {image_tag}")
    print_info(f"Browsers: {', '.join(browsers_to_test)}")
    
    results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    for browser in browsers_to_test:
        print(f"\n  Testing {browser}...")
        
        # Start container with specific browser
        container_id = start_container(image_tag, browser if target == "all" else None)
        
        if not container_id:
            results["failed"] += 1
            results["errors"].append(f"{browser}: Failed to start container")
            continue
        
        # Wait for services to start
        print_info(f"  Container started: {container_id[:12]}")
        print_info(f"  Waiting for services to start...")
        time.sleep(8)
        
        # Test the browser
        if test_browser(browser):
            results["passed"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(f"{browser}: Test failed")
        
        # Cleanup
        stop_container(container_id)
        time.sleep(2)
    
    # Print results
    print(f"\n  Results: {results['passed']}/{len(browsers_to_test)} passed")
    
    if results["failed"] > 0:
        print_error(f"  {results['failed']} tests failed:")
        for error in results["errors"]:
            print(f"    - {error}")
        return False
    else:
        print_success(f"  All tests passed for {base}/{target}")
        return True

def main():
    """Main test function"""
    print_header("Playwright VNC Image Test Suite")
    print_info(f"Repository: {REPO}")
    print_info(f"Test URL: {TEST_URL}")
    print_info(f"Ports: VNC={VNC_PORT}, Playwright={PW_PORT}")
    
    total_passed = 0
    total_failed = 0
    failed_images = []
    
    # Test all images
    for base in IMAGES:
        for target in IMAGES[base]:
            if test_image(base, target):
                total_passed += 1
            else:
                total_failed += 1
                failed_images.append(f"{base}/{target}")
            
            # Brief pause between images
            time.sleep(2)
    
    # Final summary
    print_header("Test Summary")
    total_images = total_passed + total_failed
    print(f"Total Images Tested: {total_images}")
    print(f"Passed: {Colors.GREEN}{total_passed}{Colors.END}")
    print(f"Failed: {Colors.RED}{total_failed}{Colors.END}")
    
    if total_failed > 0:
        print(f"\n{Colors.RED}Failed Images:{Colors.END}")
        for img in failed_images:
            print(f"  ✗ {img}")
        sys.exit(1)
    else:
        print(f"\n{Colors.GREEN}{'='*70}")
        print(f"✓ All {total_images} images passed testing!{Colors.END}")
        print(f"{'='*70}\n")
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
