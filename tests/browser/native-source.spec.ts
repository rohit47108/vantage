import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {readFileSync} from 'node:fs';

const acquisition=JSON.parse(readFileSync('research/updates/2026-11-15/native-extraction/acquisition.json','utf8'));
const old=JSON.parse(readFileSync('research/updates/2026-11-15/photometry/benchmark.json','utf8'));
// Narrow discovery correctly excludes the uncovered reference cutout.
// Use a covered, authentic poor-fit input for browser rejection guidance;
// retained-fixture regressions separately test missing native coverage.
const wanted=[...acquisition.observations.filter((row:{detector:number})=>row.detector!==2),...old.observations.slice(0,2)];

test('general source workflow uses frozen discovery, all six native detectors and lazy inspection',async({page,baseURL})=>{
  test.setTimeout(240_000);
  await page.goto('/?view=measure');
  await expect(page.getByRole('heading',{name:'Measure a source',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Use P330E calibration example'}).click();
  await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toHaveValue('247.8908392831');
  await page.getByRole('button',{name:'Find source observations'}).click();
  await expect(page.getByRole('heading',{name:'Choose observations',exact:true})).toBeVisible({timeout:90_000});
  await page.getByRole('button',{name:'Clear observation selection'}).click();
  for(const row of wanted){
    await page.getByLabel('Filter observation IDs').fill(row.obs_id);
    await expect(page.getByLabel(`Include ${row.obs_id}/D${row.detector}`,{exact:true})).toBeVisible();
    await page.getByLabel(`Include ${row.obs_id}/D${row.detector}`,{exact:true}).check();
  }
  await page.getByLabel('Filter observation IDs').fill('');
  await expect(page.getByTestId('native-selection-count')).toContainText('7 observations selected');
  await page.getByRole('button',{name:'Measure selected observations',exact:true}).click();
  await expect(page.getByRole('heading',{name:'P330E · measured light',exact:true})).toBeVisible({timeout:120_000});
  await expect(page.getByText('6 pass fit checks',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Inspect 2025W30_1B_0610_2/D1',exact:true}).click();
  await expect(page.getByTestId('native-measured-flux')).toContainText('31,248.75');
  await expect(page.getByRole('img',{name:'Native brightness cutout; source cross marks the measured position. Array rows increase upward.'})).toBeVisible();
  await expect(page.getByText('Solid: fit core · dashed: background annulus').first()).toBeVisible();
  await expect(page.getByText('1 need fit review',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Inspect 2025W29_1A_0544_1/D2',exact:true}).click();
  await expect(page.getByTestId('native-selected-sample')).toContainText('exceeds the declared maximum of 3');
  const download=page.waitForEvent('download');await page.getByRole('link',{name:'ECSV with units'}).click();
  expect((await download).suggestedFilename()).toMatch(/samples\.ecsv$/);
  await page.getByRole('button',{name:'Share measured light',exact:true}).click();
  const link=await page.getByLabel('Measured-light link').inputValue();await page.goto(link);
  await expect(page.getByRole('heading',{name:'P330E · measured light',exact:true})).toBeVisible();
  await expect(page.getByTestId('native-selected-sample')).toContainText('exceeds the declared maximum of 3');
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations).toEqual([]);
  await page.screenshot({path:`artifacts/native-source-${baseURL?.startsWith('https:')?'public':'local'}-desktop.png`,fullPage:true});
  await page.getByRole('button',{name:'Clear observation selection'}).click();
  await page.getByLabel('Filter observation IDs').fill('2025W30_1B_0610_2');
  await page.getByLabel('Include 2025W30_1B_0610_2/D1',{exact:true}).check();
  const submitted=page.waitForRequest(r=>r.url().endsWith('/v1/native-source-samples')&&r.method()==='POST');
  await page.getByRole('button',{name:'Measure selected observations',exact:true}).click();
  expect((await submitted).postDataJSON().observation_indices).toHaveLength(1);
  await expect(page.getByText('1 pass fit checks',{exact:true})).toBeVisible({timeout:60_000});
});

test('moving-source links preserve coordinates and both motion components on mobile',async({page,baseURL})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/?view=measure&source_ra=247.8908392831&source_dec=30.14604947207&pmra=-8.882&pmdec=-38.705&ref_epoch=2016&source_name=P330E');
  await page.getByText('Catalog motion and survey coverage',{exact:true}).click();
  await expect(page.getByLabel('Apply supplied angular motion')).toBeChecked();
  await expect(page.getByLabel('RA motion · mas/year · includes cos(dec)')).toHaveValue('-8.882');
  await expect(page.getByLabel('Declination motion · mas/year')).toHaveValue('-38.705');
  await page.reload();await page.getByText('Catalog motion and survey coverage',{exact:true}).click();
  await expect(page.getByLabel('Apply supplied angular motion')).toBeChecked();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations).toEqual([]);
  await page.screenshot({path:`artifacts/native-source-${baseURL?.startsWith('https:')?'public':'local'}-mobile.png`,fullPage:true});
});

test('sky inspection and real Gaia selection carry the source into native measurement',async({page})=>{
  const catalog=JSON.parse(readFileSync('public/prepared/catalog.json','utf8'));
  const field=catalog.find((row:{key:string})=>row.key==='m101');
  await page.goto(`/sequence/${field.id}?layers=gaia`);
  await expect(page.getByRole('heading',{name:'M101',exact:true})).toBeVisible();
  await page.getByRole('img',{name:/Infrared sky/}).press('Enter');
  await page.getByRole('button',{name:'Measure this sky position',exact:true}).click();
  const point=new URL(page.url());
  await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toHaveValue(point.searchParams.get('source_ra')!);
  await expect(page.getByLabel('Declination · degrees',{exact:true})).toHaveValue(point.searchParams.get('source_dec')!);
  await page.getByRole('button',{name:'← Back to sky',exact:true}).click();
  await expect(page).toHaveURL(new RegExp('/sequence/'+field.id));
  await page.getByText('Other telescopes · Gaia / WISE',{exact:true}).click();
  const select=page.getByRole('combobox',{name:'Select Gaia source',exact:true});
  await expect(select).toBeVisible({timeout:90_000});
  const layer=await (await page.request.get(`/v1/surveys/gaia?sequence_id=${field.id}`)).json();
  const source=layer.sources.find((row:{pmra:number|null;pmdec:number|null})=>row.pmra!=null&&row.pmdec!=null);
  expect(source).toBeTruthy();await select.selectOption(source.id);
  await page.getByRole('button',{name:'Measure selected Gaia source',exact:true}).click();
  await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toHaveValue(String(source.ra));
  await expect(page.getByLabel('Declination · degrees',{exact:true})).toHaveValue(String(source.dec));
  await page.getByText('Catalog motion and survey coverage',{exact:true}).click();
  await expect(page.getByLabel('Apply supplied angular motion')).toBeChecked();
  await expect(page.getByLabel('RA motion · mas/year · includes cos(dec)')).toHaveValue(String(source.pmra));
  await expect(page.getByLabel('Declination motion · mas/year')).toHaveValue(String(source.pmdec));
  await expect(page.getByLabel('Reference epoch · Julian year')).toHaveValue(String(source.ref_epoch));
});

test('source failures, reference loading and real queued cancellation retain clear states',async({page})=>{
  await page.goto('/?view=measure');
  let release!:()=>void;const gate=new Promise<void>(resolve=>release=resolve);
  await page.route('**/v1/source-targets/p330e',async route=>{await gate;await route.continue();});
  await page.getByRole('button',{name:'Use P330E calibration example'}).click();
  await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toBeDisabled();
  release();await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toHaveValue('247.8908392831');
  await page.route('**/v1/source-fields',route=>route.fulfill({status:503,json:{detail:'Archive temporarily unavailable'}}));
  await page.getByRole('button',{name:'Find source observations',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Archive temporarily unavailable');
  await expect(page.getByRole('heading',{name:'Choose observations',exact:true})).toHaveCount(0);
  await page.unroute('**/v1/source-fields');
  await page.getByLabel('Source label',{exact:true}).fill('P330E cancellation '+Date.now());
  await page.getByRole('button',{name:'Refresh archive search',exact:true}).click();
  await page.getByRole('button',{name:'Cancel source analysis',exact:true}).click();
  await expect(page.getByText('Source analysis cancelled.',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Find source observations',exact:true})).toBeEnabled();
});
