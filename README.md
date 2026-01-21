# Playwright with VNC: Headed Browser Docker Images

Official Playwright images from Microsoft are excellent for CI/CD pipelines and pure headless execution. However, they lack a graphical user interface.

This project solves that problem by providing a lightweight, VNC-enabled environment.

**Images are available in two bases:**
- **Bookworm** (Debian) - Smallest images
- **UBI9** (Red Hat) - Enterprise-ready

## Key Features

- VNC Server Built-in: Connect with any VNC client to view and interact with the browser
- Headed Mode by Default: Designed specifically for running browsers with their UI visible
- Dual-Base Support: Choose Debian Bookworm or Red Hat UBI9
- Multiple Browser Variants: Build tailored images for Firefox, Chromium, or Google Chrome
- All-in-One Image: An all variant includes all three browsers for maximum flexibility
- Optimized for Size: Multi-stage Dockerfile and careful package selection to keep images lean
- Configurable: Control the browser type and headless mode at runtime with environment variables
- Automated Builds: Daily CI/CD pipeline builds latest Playwright versions automatically

## 🚀 Quick Start

```bash
# Bookworm Firefox (smallest - 994 MB)
docker run -p 5900:5900 -p 3000:3000 digitronik/playwright-vnc:bookworm-firefox-latest

# UBI9 all browsers (enterprise)
docker run -p 5900:5900 -p 3000:3000 digitronik/playwright-vnc:ubi9-latest

# Connect via VNC
vncviewer localhost:5900
```

**See [Releases](https://github.com/digitronik/playwright-images/releases) for version history and [Docker Hub](https://hub.docker.com/r/digitronik/playwright-vnc/tags) for all available tags.**

## How to Build Images Locally

**Note:** Images are automatically built daily via GitHub Actions. For local development:

```bash
# Build all Bookworm variants (default)
./build.sh

# Build all UBI9 variants
./build.sh --base ubi9

# Build specific browsers
./build.sh firefox chrome
./build.sh --base ubi9 firefox

# Build with specific Playwright version
./build.sh --playwright-version 1.58.0
```

### Available Image Variants

| Base | Image Tag | Default Browser | Installed Browsers |
|------|-----------|-----------------|-------------------|
| Bookworm | `:bookworm-latest` | Chromium | All browsers (Firefox, Chromium, Chrome) |
| Bookworm | `:bookworm-firefox-latest` | Firefox | Playwright's Firefox |
| Bookworm | `:bookworm-chromium-latest`| Chromium | Playwright's Chromium |
| Bookworm | `:bookworm-chrome-latest` | Google Chrome | Google Chrome (Stable) |
| UBI9 | `:ubi9-latest` | Chromium | All browsers (Firefox, Chromium, Chrome) |
| UBI9 | `:ubi9-firefox-latest` | Firefox | Playwright's Firefox |
| UBI9 | `:ubi9-chromium-latest`| Chromium | Playwright's Chromium |
| UBI9 | `:ubi9-chrome-latest` | Google Chrome | Google Chrome (Stable) |

## How to Run the Images

Use docker/podman to start a container. Map VNC port (5900) and Playwright server port (3000).

```bash
# Run specific browser image
docker run -p 5900:5900 -p 3000:3000 digitronik/playwright-vnc:bookworm-firefox-latest

# Run UBI9 all-browsers image with specific browser selection
docker run -e PW_BROWSER="chrome" -p 5900:5900 -p 3000:3000 digitronik/playwright-vnc:ubi9-latest

# Run in headless mode  
docker run -e PW_HEADLESS="true" -p 3000:3000 digitronik/playwright-vnc:bookworm-firefox-latest
```

### Environment Variables

- `PW_BROWSER`: Specify browser (`firefox`, `chromium`, `chrome`) 
- `PW_HEADLESS`: Run in headless mode (`true`/`false`, default: `false`)

### Connecting with a VNC Client

VNC will run at port 5900. You can connect your favorite VNC client.

```bash
vncviewer localhost:5900 
```

## Connecting with a Playwright Client

### Chromium or Chrome

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect("ws://localhost:3000/playwright")
    print("Connected to Chromium!")
    page = browser.new_page()
    page.goto("https://playwright.dev/")
    print(page.title())
    browser.close()
```

### Firefox

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.connect("ws://localhost:3000/playwright")
    print("Connected to Firefox!")
    page = browser.new_page()
    page.goto("https://playwright.dev/")
    print(page.title())
    browser.close()
```

## Testing

Run comprehensive pytest test suite:

```bash
pip install -r tests/requirements.txt
pytest tests/ -v
```

See [tests/README.md](tests/README.md) for details.
