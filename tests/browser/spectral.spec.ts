import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('real spectral channels, blank layer, false color, inspection and exact restore',async({page,context})=>{
  test.setTimeout(180_000);
  await page.goto('/?view=wavelengths');
  await expect(page.getByRole('heading',{name:'3.293 µm',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Export view & provenance'})).toBeEnabled({timeout:60_000});
  await page.getByLabel('SPHEREx spectral sky image; press Enter to inspect center').focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Surface brightness',{exact:true})).toBeVisible();
  await page.screenshot({path:'artifacts/spectral-desktop.png',fullPage:true});
  const violations=(await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations;
  expect(violations).toEqual([]);
  await page.getByRole('slider',{name:'Wavelength channel'}).fill('50');
  await expect(page.getByText('This dichroic channel is blank',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'Next wavelength'}).click();
  await expect(page.getByText('This dichroic channel is blank',{exact:false})).toBeVisible();
  await page.getByRole('button',{name:'Next wavelength'}).click();
  await expect(page.getByRole('button',{name:'Export view & provenance'})).toBeEnabled({timeout:60_000});
  await page.getByText('Build a false-color image',{exact:true}).click();
  await page.getByLabel('Show false color',{exact:true}).check();
  await expect(page.getByRole('heading',{name:'Three wavelengths, one field'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Export view & provenance'})).toBeEnabled({timeout:90_000});
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export view & provenance'}).click();
  expect((await download).suggestedFilename()).toBe('vantage-spectral-provenance.json');
  const fresh=await context.newPage();await fresh.goto(page.url());
  await expect(fresh.getByLabel('Show false color',{exact:true})).toBeChecked();
  await expect(fresh.getByRole('button',{name:'Export view & provenance'})).toBeEnabled({timeout:90_000});
  await fresh.close();
});

test('spectral phone layout keeps real controls and image within viewport',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/?view=wavelengths');
  await expect(page.getByRole('button',{name:'Export view & provenance'})).toBeEnabled({timeout:60_000});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await expect(page.getByRole('button',{name:'Play wavelengths'})).toBeVisible();
  await page.screenshot({path:'artifacts/spectral-mobile.png',fullPage:true});
});
