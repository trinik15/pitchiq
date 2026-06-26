/** Capture 8-tab Devpost gallery screenshots from live PitchIQ app. */
import { chromium } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const BASE_URL = 'https://pitchiq-aqx.streamlit.app/';
const OUT_DIR = path.join(__dirname, '..', '..', 'pitchiq', 'screenshots_devpost');

async function getApp(page: import('@playwright/test').Page) {
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 120_000 });
  const app = page.frameLocator('iframe[title="streamlitApp"]').first();
  await app.getByText('Paul Skenes', { exact: false }).first().waitFor({ timeout: 120_000 });
  await page.waitForTimeout(5000);
  return app;
}

const shots: { file: string; setup: (app: ReturnType<import('@playwright/test').Page['frameLocator']>) => Promise<void> }[] = [
  { file: '01_scouting_summary.png', setup: async (app) => { await app.getByRole('tab', { name: 'Scouting Summary' }).click(); } },
  { file: '02_pitch_arsenal.png', setup: async (app) => { await app.getByRole('tab', { name: 'Pitch Arsenal' }).click(); } },
  { file: '03_location_zones.png', setup: async (app) => { await app.getByRole('tab', { name: 'Location & Zones' }).click(); } },
  {
    file: '04_count_tendencies.png',
    setup: async (app) => {
      await app.getByRole('tab', { name: 'Count Tendencies' }).click();
      await app.getByLabel('Select count').click();
      await app.getByRole('option', { name: '0-2' }).click();
    },
  },
  { file: '05_sequencing.png', setup: async (app) => { await app.getByRole('tab', { name: 'Sequencing' }).click(); } },
  { file: '06_pitch_grades.png', setup: async (app) => { await app.getByRole('tab', { name: 'Pitch Grades' }).click(); } },
  { file: '07_season_trends.png', setup: async (app) => { await app.getByRole('tab', { name: 'Season Trends' }).click(); } },
  {
    file: '08_matchup.png',
    setup: async (app) => {
      await app.getByRole('tab', { name: 'Matchup' }).click();
      const lhb = app.getByText('vs LHB', { exact: true }).first();
      if (await lhb.isVisible()) await lhb.click();
    },
  },
];

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const app = await getApp(page);

  for (const { file, setup } of shots) {
    await setup(app);
    await page.waitForTimeout(4000);
    await page.screenshot({ path: path.join(OUT_DIR, file), fullPage: false });
    console.log(`Saved ${file}`);
  }

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
