# Test Suite for Playwright VNC Images

## Quick Start

```bash
# Install dependencies
pip install -r tests/requirements.txt

# Run all tests
pytest tests/test_images.py -v

# Test specific base
pytest tests/ -v -k bookworm
pytest tests/ -v -k ubi9

# Test specific browser
pytest tests/ -v -k firefox

# Test specific mode
pytest tests/ -v -k headed
pytest tests/ -v -k headless

# Use docker instead of podman
CONTAINER_ENGINE=docker pytest tests/ -v

# Custom repository
IMAGE_REPO=myrepo/playwright pytest tests/ -v
```

## Configuration

Set via environment variables:
- `CONTAINER_ENGINE` - podman (default) or docker
- `IMAGE_REPO` - Image repository name (default: digitronik/playwright-vnc)
