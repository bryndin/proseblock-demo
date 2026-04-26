import { defineConfig, devices } from '@playwright/test';

const port = 1315;
const baseURL = `http://localhost:${port}`;

export default defineConfig({
  testDir: './tests/e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. */

  use: {
    baseURL,
    trace: 'on-first-retry',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // You can add Firefox/Webkit later if needed
  ],

  /* Run your local dev server before starting the tests */
  /* It's broken on WSL, see my https://github.com/microsoft/playwright/issues/40430 */
  // webServer: {
  //   command: `npx serve public -l ${port} --no-clipboard`,
  //   url: baseURL,
  //   reuseExistingServer: !process.env.CI,
  //   stdout: process.env.VERBOSE === '1' ? 'pipe' : 'ignore',
  //   stderr: process.env.VERBOSE === '1' ? 'pipe' : 'ignore',
  // },
});

