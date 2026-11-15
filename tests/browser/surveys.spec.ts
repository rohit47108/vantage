import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {readFileSync,writeFileSync} from 'node:fs';

const catalog=JSON.parse(readFileSync('public/prepared/catalog.json','utf8'));
const field=catalog.find((s:any)=>s.key==='m101');

test('real Gaia and WISE markers follow camera and epoch; provenance and share retain context',async({page,context})=>{
  test.setTimeout(180_000);
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  let gaiaRequests=0;
  page.on('request',r=>{if(r.url().includes('/v1/surveys/gaia?'))gaiaRequests++;});
  await page.goto(`/sequence/${field.id}?layers=gaia,wise&gaia_opacity=0.6&wise_opacity=0.4`);
  await expect(page.getByRole('heading',{name:'M101',exact:true})).toBeVisible();
  await page.getByText('Other telescopes · Gaia / WISE',{exact:true}).click();
  const gaiaSelect=page.getByRole('combobox',{name:'Select Gaia source',exact:true});
  const wiseSelect=page.getByRole('combobox',{name:'Select WISE source',exact:true});
  await expect(gaiaSelect).toBeVisible({timeout:90_000});
  await expect(wiseSelect).toBeVisible({timeout:90_000});
  await expect(page.getByRole('slider',{name:'Gaia marker opacity'})).toHaveValue('0.6');
  const gaia=await (await page.request.get(`/v1/surveys/gaia?sequence_id=${field.id}`)).json();
  const wise=await (await page.request.get(`/v1/surveys/wise?sequence_id=${field.id}`)).json();
  expect(gaia.sources.length).toBeGreaterThan(0);expect(wise.sources.length).toBeGreaterThan(0);
  const source=[...gaia.sources].sort((a:any,b:any)=>Math.hypot(...a.pixels_by_frame[0].map((v:number,i:number)=>v-(field.shape[i]-1)/2))-Math.hypot(...b.pixels_by_frame[0].map((v:number,i:number)=>v-(field.shape[i]-1)/2)))[0];
  expect(typeof source.id).toBe('string');expect(source.id.length).toBeGreaterThan(15);
  await gaiaSelect.selectOption(source.id);
  const inspector=page.getByRole('region',{name:'Selected catalog source',exact:true});
  await expect(inspector.getByText(source.id,{exact:true})).toBeVisible();
  await expect(inspector).toContainText('J2016.0 TCB');
  await page.getByRole('button',{name:'Zoom in',exact:true}).click();
  const canvas=page.getByRole('img',{name:/Infrared sky/});
  await canvas.press('ArrowLeft');
  const box=(await canvas.boundingBox())!;
  const clickPosition=(frame:number)=>({
    x:(400+20+1.25*(-350+(source.pixels_by_frame[frame][0]+.5)*700/field.shape[1]))*box.width/800,
    y:(400+1.25*(350-(source.pixels_by_frame[frame][1]+.5)*700/field.shape[0]))*box.height/800,
  });
  await wiseSelect.selectOption(wise.sources[0].id);
  await canvas.click({position:clickPosition(0)});
  await expect(inspector.getByText(source.id,{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Next frame',exact:true}).click();
  await expect(inspector).toContainText(field.frames[1].utc_mid);
  await page.getByRole('button',{name:'A/B compare',exact:true}).click();
  await page.locator('canvas').nth(1).click({position:clickPosition(1)});
  await expect(inspector).toContainText(field.frames[1].utc_mid);
  await page.getByRole('button',{name:'A/B compare',exact:true}).click();
  await page.getByRole('button',{name:'Check Gaia / WISE associations',exact:true}).click();
  await expect(page.getByText('Candidate associations only.',{exact:true})).toBeVisible({timeout:60_000});
  await page.getByText('Association method and candidates',{exact:true}).click();
  await expect(page.getByRole('table')).toBeVisible();
  await page.screenshot({path:'artifacts/surveys-desktop.png',fullPage:true});
  const report=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag22aa']).analyze();
  expect(report.violations).toEqual([]);
  await page.getByRole('checkbox',{name:'AllWISE · infrared diamonds',exact:true}).uncheck();
  await page.getByRole('checkbox',{name:'AllWISE · infrared diamonds',exact:true}).check();
  await expect(wiseSelect).toBeVisible();
  expect(gaiaRequests).toBe(1);
  await context.grantPermissions(['clipboard-read','clipboard-write']);
  await page.getByRole('button',{name:'Share view ↗',exact:true}).click();
  const link=await page.evaluate(()=>navigator.clipboard.readText());
  expect(link).toContain('gaia_opacity=0.6');expect(link).toContain('wise_opacity=0.4');
  const fresh=await context.newPage();await fresh.goto(link);
  await fresh.getByText('Other telescopes · Gaia / WISE',{exact:true}).click();
  await expect(fresh.getByRole('checkbox',{name:'Gaia DR3 · optical circles',exact:true})).toBeChecked();
  await expect(fresh.getByRole('slider',{name:'WISE marker opacity'})).toHaveValue('0.4');await fresh.close();
  const pending=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export provenance ↓',exact:true}).click();
  const provenance=JSON.parse(readFileSync((await (await pending).path())!,'utf8'));
  expect(provenance.catalog_context.gaia.sources[0].id).toBe(gaia.sources[0].id);
  expect(provenance.catalog_context.wise.credits).toContain('NASA');
  expect(provenance.catalog_context.associations.status).toBe('candidate_associations_only');
  expect(provenance.view.survey_opacity).toEqual([.6,.4]);
  writeFileSync('artifacts/survey-export-provenance.json',JSON.stringify(provenance,null,2));
  const image=page.waitForEvent('download');await page.getByRole('button',{name:'Export labeled image ↓',exact:true}).click();
  expect(readFileSync((await (await image).path())!).readUInt32BE(20)).toBe(1020);
  expect(errors).toEqual([]);
});

test('catalog and name outages preserve prepared images and offer recovery',async({page})=>{
  await page.route('**/v1/surveys/wise?*',route=>route.abort());
  await page.route('**/v1/targets/resolve?*',route=>route.abort());
  await page.goto(`/sequence/${field.id}?layers=gaia,wise`);
  await page.getByText('Other telescopes · Gaia / WISE',{exact:true}).click();
  await expect(page.getByRole('button',{name:'Retry catalogs',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Next frame',exact:true}).click();
  await expect(page.getByText(field.frames[1].obs_id,{exact:true})).toBeVisible();
  await page.getByRole('textbox',{name:'Object name',exact:true}).fill('M101');
  await page.getByRole('button',{name:'Find object',exact:true}).click();
  await expect(page.locator('.name-lookup [role=status]')).toContainText('featured field');
  await page.unroute('**/v1/surveys/wise?*');
  await page.getByRole('button',{name:'Retry catalogs',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'Select WISE source',exact:true})).toBeVisible({timeout:90_000});
  await page.screenshot({path:'artifacts/surveys-recovered.png',fullPage:true});
});

test('mobile catalog keyboard selection retains dates and fits the viewport',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto(`/sequence/${field.id}?layers=gaia,wise`);
  await page.getByTitle('Examples',{exact:true}).click();
  await page.getByText('Other telescopes · Gaia / WISE',{exact:true}).click();
  const select=page.getByRole('combobox',{name:'Select WISE source',exact:true});
  await expect(select).toBeVisible({timeout:90_000});
  await select.focus();await page.keyboard.press('Home');await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');
  await expect(page.getByRole('region',{name:'Selected catalog source',exact:true})).toContainText('W1 mean MJD');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'artifacts/surveys-mobile.png',fullPage:true});
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag22aa']).analyze()).violations).toEqual([]);
});

test('actual name resolution selects a new spectral sky field',async({page})=>{
  test.setTimeout(180_000);
  await page.goto('/?view=wavelengths');
  await page.getByRole('textbox',{name:'Object name',exact:true}).fill('M101');
  await page.getByRole('button',{name:'Find object',exact:true}).click();
  await expect(page.locator('.name-lookup [role=status]')).toContainText('Found M 101',{timeout:60_000});
  await expect(page.getByRole('spinbutton',{name:'Right ascension · degrees',exact:true})).toHaveValue('210.8024292');
  await expect(page.getByRole('button',{name:'Export view & provenance'})).toBeEnabled({timeout:90_000});
  const result=await (await page.request.get('/v1/targets/resolve?name=M101')).json();
  expect(result.provider).toContain('Simbad');expect(result.warning).toContain('No observation epoch');
  writeFileSync('artifacts/name-resolver-live.json',JSON.stringify(result,null,2));
});
