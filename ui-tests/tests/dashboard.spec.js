const { test, expect } = require("@playwright/test");

// These tests assume Streamlit is already running at http://localhost:8501.
// They simulate a risk analyst using the dashboard.

test("loads dashboard and shows main layout", async ({ page }) => {
  await page.goto("/");

  // Check the main title is visible
  await expect(
    page.getByText("Crypto Transaction Risk Simulator")
  ).toBeVisible();

  // Check that at least one metric block is rendered (KPI row)
  // Streamlit metrics are wrapped in elements that often have 'stMetric' in data-testid.
  const metricBlock = page.locator('[data-testid="stMetric"]').first();
  await expect(metricBlock).toBeVisible();

  // Also confirm the main sections exist
  await expect(
    page.getByRole("heading", { name: "High-risk wallets" })
  ).toBeVisible();
  await expect(page.getByText("Wallet details and network")).toBeVisible();
});

test("shows high-risk wallets table and wallet details by default", async ({
  page,
}) => {
  await page.goto("/");

  // Use heading role to avoid strict-mode issues
  await expect(
    page.getByRole("heading", { name: "High-risk wallets" })
  ).toBeVisible();

  // Wait for the data table to render
  const tableLocator = page.locator('div[data-testid="stDataFrame"]').first();
  await expect(tableLocator).toBeVisible();

  // The selectbox has a default wallet selected, so details should already be visible
  await expect(page.getByText("Wallet ID:")).toBeVisible();
  await expect(page.getByText("Wallet risk bucket:")).toBeVisible();
  await expect(page.getByText("Wallet network view")).toBeVisible();
});

test("renders wallet network graph for default selected wallet", async ({
  page,
}) => {
  await page.goto("/");

  // Ensure the network section is rendered
  await expect(page.getByText("Wallet network view")).toBeVisible();

  // Streamlit renders matplotlib charts as <img> tags inside a container.
  // Assert that at least one image is visible on the page.
  const graphImage = page.locator("img").first();
  await expect(graphImage).toBeVisible();
});
