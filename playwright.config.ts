import {defineConfig} from '@playwright/test';

export default defineConfig({
  testDir:'tests/browser',
  timeout:120_000,
  expect:{timeout:10_000},
  workers:1,
  retries:0,
  reporter:[['list'],['json',{outputFile:'artifacts/browser-results.json'}]],
  use:{baseURL:process.env.VANTAGE_BASE_URL||'http://127.0.0.1:5173',channel:'chrome',viewport:{width:1440,height:900},headless:true,trace:'retain-on-failure',screenshot:'only-on-failure'},
});
