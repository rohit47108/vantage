import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {readFileSync} from 'node:fs';

test('real mosaic pixel trace links channel, image, exports and restored sky position',async({page,context,baseURL})=>{
  test.setTimeout(240_000);
  await page.goto('/?view=wavelengths');
  const image=page.getByLabel('SPHEREx spectral sky image; press Enter to inspect center');
  await expect(image).toBeVisible({timeout:60_000});await image.focus();await page.keyboard.press('Enter');
  await expect(page.getByRole('button',{name:'Trace pixel across wavelengths',exact:true})).toBeVisible({timeout:5000});
  await page.getByRole('button',{name:'Trace pixel across wavelengths',exact:true}).click();
  await expect(page.getByTestId('trace-coverage')).toContainText('100 of 102',{timeout:180_000});
  await expect(page.getByRole('region',{name:'Mosaic pixel brightness trace',exact:true})).toContainText('MJy/sr');
  await expect(page.getByTestId('trace-interpretation')).toContainText('not source photometry');
  await page.getByRole('button',{name:'Choose trace D1 channel 1',exact:true}).click();
  await expect(page.getByRole('slider',{name:'Wavelength channel'})).toHaveValue('0');
  await expect(image).toBeVisible({timeout:60_000});
  await expect(page.getByTestId('trace-selected-channel')).toContainText('D1 · channel 1');
  await page.getByText('All 102 brightness samples',{exact:true}).click();
  const blank=page.getByRole('row').filter({has:page.getByRole('button',{name:'Show table D3 channel 17',exact:true})});
  await expect(blank).toContainText('blank');await expect(blank).toContainText('No data');
  await blank.getByRole('button').click();
  await expect(page.getByText('This dichroic channel is blank',{exact:false})).toBeVisible();
  await expect(page.getByTestId('trace-coverage')).toContainText('100 of 102');
  const download=page.waitForEvent('download');await page.getByRole('link',{name:'Trace ECSV',exact:true}).click();
  expect(readFileSync((await (await download).path())!,'utf8')).toContain('brightness_mjysr');
  await page.getByRole('button',{name:'Share brightness trace',exact:true}).click();
  const link=await page.getByLabel('Brightness trace link').inputValue();expect(link).toContain('trace=');expect(link).toContain('wave_x=80');
  const fresh=await context.newPage();await fresh.goto(link);
  await expect(fresh.getByTestId('trace-coverage')).toContainText('100 of 102');
  await expect(fresh.getByTestId('trace-selected-channel')).toContainText('D3 · channel 17');await fresh.close();
  await page.getByRole('button',{name:'Measure this trace position',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Measure a source',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'← Back to sky',exact:true}).click();
  await expect(page.getByTestId('trace-coverage')).toContainText('100 of 102');
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations).toEqual([]);
  await page.screenshot({path:`artifacts/spectral-trace-${baseURL?.startsWith('https:')?'public':'local'}-mobile.png`,fullPage:true});
  await image.focus();await page.keyboard.press('ArrowRight');
  await expect(page.getByTestId('trace-coverage')).toHaveCount(0);
  expect(page.url()).not.toContain('trace=');expect(page.url()).toContain('wave_x=81');
});

test('a saved job for another pixel cannot replace the current trace selection',async({page})=>{
  const real=JSON.parse(readFileSync('artifacts/spectral-trace-live-product.json','utf8'));
  const job='a'.repeat(32);
  await page.route('**/v1/analysis/jobs/'+job,route=>route.fulfill({json:{state:'complete',result_id:real.id,error:null}}));
  await page.goto('/?view=wavelengths&wave_x=81&wave_y=80&trace_job='+job);
  await expect(page.getByRole('alert')).toContainText('another sky field or pixel');
  await expect(page.getByTestId('trace-coverage')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Cancel brightness trace',exact:true})).toHaveCount(0);
  expect(page.url()).not.toContain('trace_job=');
});

test('trace request failure and cancellation leave the sky usable without inventing samples',async({page})=>{
  let submitted=0,cancelled=false;const job='b'.repeat(32);
  await page.route('**/v1/spectral-traces',route=>{
    submitted++;return route.fulfill(submitted===1?{status:503,json:{detail:'Archive temporarily unavailable; retry the trace.'}}:{status:202,json:{job_id:job}});
  });
  await page.route('**/v1/analysis/jobs/'+job,route=>{
    if(route.request().method()==='DELETE')cancelled=true;
    return route.fulfill({json:{state:cancelled?'cancelled':'queued',result_id:null,error:null}});
  });
  await page.goto('/?view=wavelengths&wave_x=80&wave_y=80');
  await expect(page.getByRole('button',{name:'Trace pixel across wavelengths',exact:true})).toBeEnabled({timeout:60_000});
  await page.getByRole('button',{name:'Trace pixel across wavelengths',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Archive temporarily unavailable');
  await page.getByRole('button',{name:'Retry brightness trace',exact:true}).click();
  await expect(page.getByRole('button',{name:'Cancel brightness trace',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Cancel brightness trace',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('Trace cancelled');
  await expect(page.getByRole('button',{name:'Retry brightness trace',exact:true})).toBeEnabled();
  await expect(page.getByTestId('trace-coverage')).toHaveCount(0);
  expect(page.url()).not.toContain('trace_job=');
  await expect(page.getByRole('slider',{name:'Wavelength channel'})).toBeEnabled();
});
