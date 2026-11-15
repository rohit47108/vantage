import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('opening examples during first-load retrieval keeps the controls open',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.route('**/prepared/**/frame-*.json',async route=>{
    const response=await route.fetch();await new Promise(resolve=>setTimeout(resolve,1000));await route.fulfill({response});
  });
  await page.goto('/');await page.getByTitle('Examples',{exact:true}).click();
  await expect(page.getByRole('heading',{name:'WISE 0855',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Hide controls',exact:true})).toBeVisible();
});

test('authentic M101 coadd job, FITS/provenance and saved-result restore',async({page,context})=>{
  await page.goto('/');
  await page.getByRole('button',{name:/M101 .*frames/}).click();
  await expect(page.getByRole('heading',{name:'M101',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Stack observations',exact:true}).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button',{name:'Build weighted coadd',exact:true}).click();
  await expect(page.getByRole('heading',{name:'M101 · narrowband coadd'})).toBeVisible({timeout:30_000});
  await expect(page.getByRole('link',{name:'Download science FITS'})).toBeVisible();
  const response=await page.request.get(await page.getByRole('link',{name:'Download science FITS'}).getAttribute('href')||'');
  expect(response.headers()['content-type']).toContain('application/fits');
  expect((await response.body()).subarray(0,6).toString()).toBe('SIMPLE');
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export coadd provenance'}).click();
  expect((await download).suggestedFilename()).toBe('vantage-coadd-provenance.json');
  await page.screenshot({path:'artifacts/coadd-desktop.png',fullPage:true});
  expect((await new AxeBuilder({page}).include('.analysis-dialog').withTags(['wcag2a','wcag2aa','wcag22aa']).analyze()).violations).toEqual([]);
  const saved=await page.getByRole('link',{name:'Open saved result'}).getAttribute('href');
  const fresh=await context.newPage();await fresh.goto(saved!);
  await expect(fresh.getByRole('heading',{name:'M101 · narrowband coadd'})).toBeVisible();
  await fresh.close();
  await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByRole('button',{name:'Stack observations',exact:true})).toBeFocused();
});

test('ineligible Ceres wavelengths remain blocked on mobile',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.route('**/prepared/fbb1d741b19b4f33a5c36c0f5b872219ab110751e098e7e3b86f8c10f08e9dbf/frame-*.json',async route=>{
    const response=await route.fetch();await new Promise(resolve=>setTimeout(resolve,1000));await route.fulfill({response});
  });
  await page.goto('/');await expect(page.getByRole('heading',{name:'WISE 0855',exact:true})).toBeVisible();
  await page.getByTitle('Examples',{exact:true}).click();
  await page.getByRole('button',{name:/Ceres .*frames/}).click();
  await expect(page.getByRole('button',{name:'Stack observations',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Stack observations',exact:true}).click();
  await page.getByRole('button',{name:'Build weighted coadd',exact:true}).click();
  await expect(page.getByRole('alert')).toContainText('No coadd was published.',{timeout:30_000});
  await expect(page.getByRole('link',{name:'Download science FITS'})).not.toBeVisible();
  expect(await page.getByRole('dialog').evaluate(e=>e.scrollWidth<=e.clientWidth)).toBe(true);
  await page.screenshot({path:'artifacts/coadd-mobile-blocked.png',fullPage:true});
});
