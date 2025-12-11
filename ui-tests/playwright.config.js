// ui-tests/playwright.config.js
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests",
  use: {
    baseURL: "http://localhost:8501", // Streamlit default
    headless: true,
  },
  reporter: [["list"]],
});
