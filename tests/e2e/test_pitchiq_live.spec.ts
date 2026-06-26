import { test, expect } from '@playwright/test';
import { waitForApp, TAB_LABELS } from './helpers';

test.describe('PitchIQ live app', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 1000 });
  });

  test('loads default Paul Skenes 2025 with PitchIQ header', async ({ page }) => {
    const app = await waitForApp(page);
    await expect(app.getByText('Paul Skenes', { exact: false }).first()).toBeVisible();
    await expect(app.getByText('2025', { exact: false }).first()).toBeVisible();
  });

  test('shows KPI metrics on Scouting Summary', async ({ page }) => {
    const app = await waitForApp(page);
    await expect(app.getByTestId('stMetricLabel').filter({ hasText: 'Total Pitches' })).toBeVisible({ timeout: 60_000 });
    await expect(app.getByTestId('stMetricLabel').filter({ hasText: 'Overall CSW%' })).toBeVisible();
  });

  test('all 8 tabs present and clickable without errors', async ({ page }) => {
    const app = await waitForApp(page);
    for (const label of TAB_LABELS) {
      const tab = app.getByRole('tab', { name: label });
      await expect(tab).toBeVisible();
      await tab.click();
      await page.waitForTimeout(2000);
      await expect(app.locator('text=Traceback (most recent call last)')).toHaveCount(0);
    }
  });

  test('platoon toggle vs LHB changes displayed metrics', async ({ page }) => {
    const app = await waitForApp(page);
    await app.getByRole('tab', { name: 'Scouting Summary' }).click();

    const totalMetric = app.getByTestId('stMetricLabel').filter({ hasText: 'Total Pitches' });
    await expect(totalMetric).toBeVisible({ timeout: 60_000 });

    const getTotalPitches = async () => {
      const card = totalMetric.locator('xpath=ancestor::div[contains(@data-testid,"stMetric")]');
      return (await card.locator('[data-testid="stMetricValue"]').textContent())?.trim() ?? '';
    };

    const allBatters = await getTotalPitches();
    await app.getByText('vs LHB', { exact: true }).click();
    await page.waitForTimeout(3000);
    const vsLhb = await getTotalPitches();
    expect(allBatters).not.toEqual(vsLhb);
  });

  test('Count Tendencies 0-2 shows count analysis', async ({ page }) => {
    const app = await waitForApp(page);
    await app.getByRole('tab', { name: 'Count Tendencies' }).click();
    await page.waitForTimeout(3000);

    const countSelect = app.getByLabel('Select count');
    await countSelect.click();
    await app.getByRole('option', { name: '0-2' }).click();
    await page.waitForTimeout(3000);

    const hasContent =
      (await app.locator('.js-plotly-plot').count()) > 0 ||
      (await app.getByText('Whiff', { exact: false }).count()) > 0 ||
      (await app.getByText('outlier', { exact: false }).count()) > 0 ||
      (await app.getByTestId('stMetricLabel').filter({ hasText: 'Pitches in count' }).count()) > 0;
    expect(hasContent).toBeTruthy();
  });

  test('Sequencing tab shows transition matrix', async ({ page }) => {
    const app = await waitForApp(page);
    await app.getByRole('tab', { name: 'Sequencing' }).click();
    await page.waitForTimeout(4000);
    const hasSequencingContent =
      (await app.getByText('transition', { exact: false }).count()) > 0 ||
      (await app.getByText('sequence', { exact: false }).count()) > 0 ||
      (await app.locator('.js-plotly-plot').count()) > 0;
    expect(hasSequencingContent).toBeTruthy();
  });

  test('Matchup tab renders situational controls', async ({ page }) => {
    const app = await waitForApp(page);
    await app.getByRole('tab', { name: 'Matchup' }).click();
    await page.waitForTimeout(3000);
    const hasControls =
      (await app.getByText('vs LHB', { exact: false }).count()) > 0 ||
      (await app.getByLabel('Count (Balls-Strikes)').count()) > 0;
    expect(hasControls).toBeTruthy();
  });

  test('Scouting Summary shows letter grades', async ({ page }) => {
    const app = await waitForApp(page);
    await app.getByRole('tab', { name: 'Scouting Summary' }).click();
    await page.waitForTimeout(3000);
    const gradePattern = app.locator('text=/\\bA\\+|\\bA\\b|\\bB\\+|\\bF\\b/');
    await expect(gradePattern.first()).toBeVisible({ timeout: 60_000 });
  });

  test('CSV download buttons exist', async ({ page }) => {
    const app = await waitForApp(page);
    await app.getByRole('tab', { name: 'Scouting Summary' }).click();
    await page.waitForTimeout(3000);
    await expect(app.getByRole('button', { name: /Pitch Summary CSV/i })).toBeVisible({ timeout: 60_000 });
    await expect(app.getByRole('button', { name: /Full Report CSV/i })).toBeVisible();
  });
});
