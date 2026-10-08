import { expect, test } from '@playwright/test'

test('runs a real critical interaction scenario and records an override', async ({ page }, testInfo) => {
  await page.goto('/')
  await expect(page.getByText('API connected')).toBeVisible()
  if (testInfo.project.name === 'mobile') await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('button', { name: 'Scenario launcher' }).click()
  const card = page.locator('.scenario-card').filter({ hasText: 'Warfarin + ibuprofen' })
  await card.getByRole('button', { name: 'Run scenario' }).click()
  await page.getByRole('button', { name: 'Generate & verify' }).click()
  await expect(page.getByRole('heading', { name: 'Critical flag' })).toBeVisible()
  await expect(page.getByText('UNTRUSTED INPUT')).toBeVisible()
  await expect(page.getByText('FHIR SOURCE')).toBeVisible()
  await expect(page.getByText('PRX-DDI-002')).toBeVisible()
  await page.getByRole('button', { name: 'Override' }).click()
  await page.getByPlaceholder(/clinical rationale/i).fill('Reviewed for the research demonstration with mitigation documented.')
  await page.getByRole('button', { name: 'Record override' }).click()
  await expect(page.getByText('Recorded: override')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({ path: `../tmp/ui-verification/${testInfo.project.name}.png`, fullPage: true })
})

test('navigation and content fit the viewport', async ({ page }, testInfo) => {
  await page.goto('/')
  if (testInfo.project.name === 'mobile') {
    await page.getByRole('button', { name: 'Open navigation' }).click()
    await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible()
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({ path: `../tmp/ui-verification/${testInfo.project.name}-workspace.png`, fullPage: true })
})
