import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {readFileSync} from 'node:fs';

const parent=JSON.parse(readFileSync('artifacts/native-workflow-public-product.json','utf8'));

test('native time/channel summaries retain real contributors, gaps, exports and saved selection',async({page,baseURL})=>{
  await page.goto('/?view=measure&samples='+parent.id);
  await expect(page.getByRole('heading',{name:'P330E · measured light',exact:true})).toBeVisible();
  await expect(page.getByTestId('summary-coverage-count')).toContainText('6 of 102');
  await page.getByLabel('Summary start date · UTC').fill('2025-07-16');
  await page.getByLabel('Summary end date · UTC').fill('2025-07-16');
  await page.getByRole('button',{name:'Apply time and channel summary',exact:true}).click();
  await expect(page.getByTestId('summary-coverage-count')).toContainText('1 of 102');
  await expect(page.getByRole('region',{name:'Native source measurements',exact:true}).getByRole('button',{name:/Inspect /})).toHaveCount(2);
  await page.getByRole('button',{name:'Inspect summary D5 channel 17',exact:true}).click();
  await expect(page.getByTestId('summary-contributors')).toContainText('2025W29_1A_0544_1/D5');
  await page.getByRole('button',{name:'Inspect native 2025W29_1A_0544_1/D5',exact:true}).click();
  await expect(page.getByTestId('native-selected-sample')).toContainText('5,277.56');
  const download=page.waitForEvent('download');await page.getByRole('link',{name:'Binned ECSV',exact:true}).click();
  const file=await download;expect(readFileSync((await file.path())!,'utf8')).toContain('input_sample_ids_json');
  const link=page.url();expect(link).toContain('summary=');
  await page.getByRole('button',{name:'Share measured light',exact:true}).click();
  expect(await page.getByLabel('Measured-light link').inputValue()).toContain('summary=');
  await page.reload();await expect(page.getByTestId('summary-coverage-count')).toContainText('1 of 102');
  await expect(page.getByLabel('Summary start date · UTC')).toHaveValue('2025-07-16');
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations).toEqual([]);
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  for(const [regionName,buttonName] of [
    ['Time-combined summary chart',/^Select summary D5 channel 17,/],
    ['Native source chart',/^Select sample 2025W29_1A_0544_1\/D5,/],
  ] as const){
    const region=page.getByRole('region',{name:regionName,exact:true});
    const point=region.getByRole('button',{name:buttonName});
    await expect(async()=>{const parent=(await region.boundingBox())!,child=(await point.boundingBox())!;expect(child.x).toBeGreaterThanOrEqual(parent.x);expect(child.x+child.width).toBeLessThanOrEqual(parent.x+parent.width);}).toPass({timeout:3000});
  }
  await page.screenshot({path:`artifacts/source-summary-${baseURL?.startsWith('https:')?'public':'local'}-mobile.png`,fullPage:true});
});

test('real adjacent-position measurement preserves negative flux and separates bounds from sensitivity',async({page})=>{
  const blank=JSON.parse(readFileSync('artifacts/source-blank-native-product.json','utf8'));
  await page.goto('/?view=measure&samples='+blank.id);
  await expect(page.getByTestId('summary-coverage-count')).toContainText('1 of 102');
  await expect(page.getByTestId('native-measured-flux')).toContainText('-18.79');
  await page.getByText('Statistical upper bounds and sensitivity',{exact:true}).click();
  await expect(page.getByText(/95% upper credible bound 18.06 µJy/)).toBeVisible();
  await expect(page.getByText(/conditional 95% detection sensitivity 94.03 µJy/)).toBeVisible();
  await expect(page.getByText(/without a saved discovery field/)).toBeVisible();
  await page.getByLabel('Summary start date · UTC').fill('2025-07-01');
  await page.getByLabel('Summary end date · UTC').fill('2025-07-02');
  await page.getByRole('button',{name:'Apply time and channel summary',exact:true}).click();
  await expect(page.getByTestId('summary-coverage-count')).toContainText('0 of 102');
  await expect(page.getByTestId('native-selected-sample')).toHaveCount(0);
  await page.getByText('Statistical upper bounds and sensitivity',{exact:true}).click();
  await expect(page.getByText('No low-signal fixed-position sample supports an upper bound in this selection.')).toBeVisible();
});
