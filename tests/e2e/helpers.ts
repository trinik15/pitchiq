import { FrameLocator, Page } from '@playwright/test';

const BASE_URL = 'https://pitchiq-aqx.streamlit.app/';

/** Streamlit Community Cloud embeds the app in an iframe. */
export async function waitForApp(page: Page, timeout = 180_000): Promise<FrameLocator> {
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout });
  const appFrame = page.frameLocator('iframe[title="streamlitApp"]').first();
  await appFrame.getByText('Paul Skenes', { exact: false }).first().waitFor({ timeout });
  return appFrame;
}

export const TAB_LABELS = [
  'Scouting Summary',
  'Pitch Arsenal',
  'Location & Zones',
  'Count Tendencies',
  'Sequencing',
  'Pitch Grades',
  'Season Trends',
  'Matchup',
];
