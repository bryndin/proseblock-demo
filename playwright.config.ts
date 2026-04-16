import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',

  use: {
    baseURL: 'http://localhost:1313',
    headless: true,
  },

  webServer: {
    command: 'hugo --gc --minify && npx serve public -l 1313',
    port: 1313,
    reuseExistingServer: true,
  },
});