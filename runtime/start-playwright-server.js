// /home/pwuser/start-playwright-server.js
const playwright = require('playwright');

(async () => {
  // Read browser type from PW_BROWSER, default to 'chromium'
  const browserType = (process.env.PW_BROWSER || 'chromium').toLowerCase();

  // Read headless mode from PW_HEADLESS.
  const headlessEnv = (process.env.PW_HEADLESS || 'false').toLowerCase();
  const runHeadless = headlessEnv === 'true';

  let browserLauncher;
  let browserDisplayName;

  // Initialize the options object for launchServer
  let launchServerOptions = {
    headless: runHeadless,
    port: 3000,
    host: '0.0.0.0',
    wsPath: '/playwright'
    // The 'channel' property will be added here if 'google-chrome' is selected
  };

  console.log(`Effective PW_BROWSER: ${browserType}`);
  console.log(`Effective PW_HEADLESS mode: ${runHeadless} (raw PW_HEADLESS env: '${process.env.PW_HEADLESS}', interpreted as '${headlessEnv}')`);

  switch (browserType) {
    case 'firefox':
      browserLauncher = playwright.firefox;
      browserDisplayName = 'Firefox';
      break;
    case 'webkit':
      browserLauncher = playwright.webkit;
      browserDisplayName = 'WebKit';
      break;
    case 'google-chrome': // Option for Google Chrome (stable)
    case 'chrome':        // Allow 'chrome' as an alias
      browserLauncher = playwright.chromium;
      browserDisplayName = 'Google Chrome (via channel)';
      launchServerOptions.channel = 'chrome'; // Add channel to the options
      break;
    case 'chromium':      // Playwright's bundled Chromium
    default:
      browserLauncher = playwright.chromium;
      browserDisplayName = 'Chromium (Playwright default)';
      // Ensure channel is not set if we are explicitly asking for Playwright's Chromium
      // (though with fresh launchServerOptions object, it wouldn't be set unless explicitly added)
      // delete launchServerOptions.channel;
      if (browserType !== 'chromium' && process.env.PW_BROWSER && browserType !== 'google-chrome' && browserType !== 'chrome') {
        console.warn(`Unsupported PW_BROWSER value: "${process.env.PW_BROWSER}". Defaulting to Playwright's Chromium.`);
      }
      break;
  }

  if (!browserLauncher) {
    console.error(`Could not determine browser launcher for type: '${browserType}'. Please check PW_BROWSER.`);
    process.exit(1);
  }

  try {
    console.log(`Attempting to launch Playwright ${browserDisplayName} server (headless: ${runHeadless})...`);
    // Pass the constructed launchServerOptions object
    const browserServer = await browserLauncher.launchServer(launchServerOptions);
    console.log(`Playwright ${browserDisplayName} server (headless: ${runHeadless}) listening on ${browserServer.wsEndpoint()}`);

    if (!runHeadless) {
      console.log(`Browser (${browserDisplayName}) should be running in headed mode. Connect via VNC to view.`);
    } else {
      console.log(`Browser (${browserDisplayName}) is running in headless mode. VNC will not show browser UI.`);
    }
  } catch (error) {
    // Specific error message if Chrome channel fails
    if ((browserType === 'google-chrome' || browserType === 'chrome') && error.message && error.message.includes('Failed to launch browser')) {
        console.error(`Failed to start ${browserDisplayName}. This might be because Google Chrome stable is not installed in the Docker image or not found in PATH.
        You may need to add steps to your Dockerfile to install 'google-chrome-stable'.
        Original error: ${error.message}`);
    } else {
        console.error(`Failed to start Playwright ${browserDisplayName} server:`, error);
    }
    process.exit(1);
  }
})();