import { test, expect } from '@playwright/test';

test.describe('Dark Mode CSS Cascade @structure', () => {
  
  test('toggling dark mode successfully inverts Tier 2.1 Semantics without breaking layout', async ({ page }) => {
    // 1. Navigate to a known content page
    await page.goto('/about/');

    // Ensure the page is fully loaded
    await expect(page.locator('body')).toBeVisible();

    // 2. Capture initial Light Mode computed styles
    const body = page.locator('body');
    const lightBg = await body.evaluate((el) => window.getComputedStyle(el).backgroundColor);
    const lightText = await body.evaluate((el) => window.getComputedStyle(el).color);

    // 3. Trigger Dark Mode
    // If you have a specific UI toggle button, you should test the UI by clicking it:
    // await page.click('.js-theme-toggle'); 
    
    // However, to strictly test the CSS Architecture cascade, we can directly set the data-theme attribute
    // that your tokens.css uses to trigger the Tier 2.1 inversion:
    await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'));

    // Give the browser a tiny window to compute the new CSS cascade
    await page.waitForTimeout(100);

    // 4. Capture Dark Mode computed styles
    const darkBg = await body.evaluate((el) => window.getComputedStyle(el).backgroundColor);
    const darkText = await body.evaluate((el) => window.getComputedStyle(el).color);

    // 5. Assertions: Ensure colors inverted
    expect(darkBg).not.toBe(lightBg);
    expect(darkText).not.toBe(lightText);

    // Optional Check: Ensure structural configurations (Tier 3) were NOT altered by dark mode.
    // For example, body margin/padding should remain strictly identical.
    const darkPadding = await body.evaluate((el) => window.getComputedStyle(el).padding);
    const lightPadding = await body.evaluate((el) => {
      document.documentElement.removeAttribute('data-theme'); // revert to check
      return window.getComputedStyle(el).padding;
    });
    
    expect(darkPadding).toBe(lightPadding);
  });
});