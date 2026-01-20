"""
Test suite for Playwright VNC images
"""

import subprocess
import time
import socket
import os
import pytest
from playwright.sync_api import sync_playwright
from wait_for import wait_for, TimedOutError

IMAGE_REPO = os.environ.get("IMAGE_REPO", "digitronik/playwright-vnc")
PW_PORT = 3000
VNC_PORT = 5900
TEST_URL = "https://example.com"
CONTAINER_ENGINE = os.environ.get("CONTAINER_ENGINE", "podman")

# All image variants
IMAGES = [
    ("bookworm", "firefox"),
    ("bookworm", "chromium"),
    ("bookworm", "chrome"),
    ("bookworm", "all"),
    ("ubi9", "firefox"),
    ("ubi9", "chromium"),
    ("ubi9", "chrome"),
    ("ubi9", "all"),
]

# Browser mappings for each target
BROWSERS = {
    "firefox": ["firefox"],
    "chromium": ["chromium"],
    "chrome": ["chrome"],
    "all": ["firefox", "chromium", "chrome"],
}


def start_container(image_tag, browser=None, headless=False):
    """Start a container and return container ID"""
    cmd = [
        CONTAINER_ENGINE, "run", "--rm", "-d",
        "-p", f"{PW_PORT}:3000"
    ]
    
    if not headless:
        cmd.extend(["-p", f"{VNC_PORT}:5900"])
    
    if headless:
        cmd.extend(["-e", "PW_HEADLESS=true"])
    
    if browser:
        cmd.extend(["-e", f"PW_BROWSER={browser}"])
    
    cmd.extend([
        "--name", f"pw-test-{int(time.time())}",
        image_tag
    ])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"Container start failed: {result.stderr}")
    
    return result.stdout.strip()


def stop_container(container_id):
    """Stop container"""
    subprocess.run([CONTAINER_ENGINE, "stop", container_id],
                  capture_output=True, timeout=10)


def image_exists(image_tag):
    """Check if image exists locally"""
    result = subprocess.run(
        [CONTAINER_ENGINE, "images", "-q", image_tag],
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())


def is_port_open(port):
    """Check if a port is accessible via socket"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False


def check_container_ready(container_id, expect_vnc=True):
    """Check container logs to see if services are ready."""
    try:
        result = subprocess.run(
            [CONTAINER_ENGINE, "logs", container_id],
            capture_output=True,
            text=True,
            timeout=5
        )
        logs = result.stdout + result.stderr
        
        # Check for error messages first
        has_error = "[ERROR]" in logs and "failed to start" in logs.lower()
        if has_error:
            # Extract error lines for debugging
            error_lines = [line for line in logs.split('\n') if '[ERROR]' in line]
            print(f"\n  Container error detected: {error_lines[0] if error_lines else 'Unknown error'}")
            return False
        
        # Check for success messages from entrypoint.sh
        has_playwright = "Playwright server started successfully" in logs
        all_ready = "All services running. Container ready!" in logs
        
        # VNC status checks
        vnc_started = "VNC server started successfully" in logs
        vnc_skipped = "Headless mode enabled - skipping VNC server" in logs
        
        # Validate VNC status matches expectation
        if expect_vnc:
            vnc_ok = vnc_started and not vnc_skipped
        else:
            vnc_ok = vnc_skipped and not vnc_started
        
        return all_ready and has_playwright and vnc_ok
        
    except Exception as e:
        print(f"\n  Failed to check container logs: {e}")
        return False


def wait_for_services(container_id, expect_vnc=True):
    """Wait for services to be ready by checking container logs
    
    Args:
        container_id: Container ID
        expect_vnc: True if VNC should start (headed), False if not (headless)
    """
    wait_for(
        lambda: check_container_ready(container_id, expect_vnc=expect_vnc),
        timeout=45,
        delay=1,
        message=f"Container services to be ready ({'with VNC' if expect_vnc else 'headless'})",
        handle_exception=True
    )


def verify_browser_connection(browser_type):
    """Verify browser via Playwright (helper function, not a test)"""
    with sync_playwright() as p:
        if browser_type == "firefox":
            browser = p.firefox.connect(f"ws://127.0.0.1:{PW_PORT}/playwright", timeout=15000)
        else:
            browser = p.chromium.connect(f"ws://127.0.0.1:{PW_PORT}/playwright", timeout=15000)
        
        page = browser.new_page()
        page.goto(TEST_URL, timeout=10000)
        
        # Verify page
        title = page.title()
        user_agent = page.evaluate("navigator.userAgent")
        
        browser.close()
        
        # Assertions
        assert "Example" in title, f"Unexpected title: {title}"
        
        if browser_type == "firefox":
            assert "Firefox" in user_agent, f"Expected Firefox, got: {user_agent}"
        else:
            assert "Chrome" in user_agent, f"Expected Chrome/Chromium, got: {user_agent}"
        
        return True


@pytest.mark.parametrize("headless", [False, True], ids=["headed", "headless"])
@pytest.mark.parametrize("base,target", IMAGES, ids=[f"{b}-{t}" for b, t in IMAGES]) 
def test_playwright_vnc_connection(base, target, headless):
    """Test playwright browser connection and page loading"""
    image_tag = f"{IMAGE_REPO}:{base}-latest" if target == "all" else f"{IMAGE_REPO}:{base}-{target}-latest"
    
    # Skip if image not built locally
    if not image_exists(image_tag):
        pytest.skip(f"Image not found: {image_tag}")
    
    browsers = BROWSERS[target]
    
    # Test each browser for this image
    for browser_type in browsers:
        container_id = None
        try:
            # Start container
            browser_env = browser_type if target == "all" else None
            container_id = start_container(image_tag, browser=browser_env, headless=headless)
            
            # Wait for services to be ready (validates VNC status matches mode)
            wait_for_services(container_id, expect_vnc=not headless)
            
            # Verify VNC port
            if headless:
                assert not is_port_open(VNC_PORT), f"VNC port {VNC_PORT} should NOT be accessible in headless mode"
            else:
                assert is_port_open(VNC_PORT), f"VNC port {VNC_PORT} should be accessible in headed mode"
            
            # Test playwright browser connection
            verify_browser_connection(browser_type)
            
        finally:
            if container_id:
                stop_container(container_id)
                time.sleep(1)

