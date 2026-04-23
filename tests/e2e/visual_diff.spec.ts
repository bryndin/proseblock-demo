import { test } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const BASELINE = process.env.VISUAL_BASELINE || 'after';
const RAW_URL = process.env.VISUAL_URL || '/';
const OUT_DIR = process.env.VISUAL_OUT_DIR || 'tests/visual-output';

function resolveUrl(raw: string): string {
    if (raw.startsWith('http://') || raw.startsWith('https://')) {
        return raw;
    }
    return `http://localhost:1315${raw}`;
}

const URL = resolveUrl(RAW_URL);

function getPath(name: string) {
    return path.join(OUT_DIR, BASELINE, name);
}

test.describe('visual diff', () => {
    test('page snapshots', async ({ page }) => {
        await page.goto(URL);

        // Disable animations
        await page.addStyleTag({
            content: `
        * {
          animation: none !important;
          transition: none !important;
        }
      `
        });

        fs.mkdirSync(path.join(OUT_DIR, BASELINE), { recursive: true });

        // Desktop viewport
        await page.setViewportSize({ width: 1280, height: 800 });
        await page.screenshot({
            path: getPath('desktop-viewport.png')
        });

        // Desktop full
        await page.screenshot({
            path: getPath('desktop-full.png'),
            fullPage: true
        });

        // Mobile
        await page.setViewportSize({ width: 375, height: 812 });
        await page.screenshot({
            path: getPath('mobile-full.png'),
            fullPage: true
        });

        // Optional component
        const hero = page.locator('.c-hero');
        if (await hero.count()) {
            await hero.first().screenshot({
                path: getPath('component-hero.png')
            });
        }
    });
});