import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {readFileSync,writeFileSync} from 'node:fs';

const catalog=JSON.parse(readFileSync('public/prepared/catalog.json','utf8'));

test('all five official fields and scientific controls retain identity through playback',async({page})=>{
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  for(const item of catalog){
    await page.getByRole('button',{name:new RegExp(item.name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+' .*frames')}).click();
    await expect(page.getByRole('heading',{name:item.name,exact:true})).toBeVisible();
    await expect(page.getByText(item.frames[0].obs_id,{exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Next frame',exact:true}).click();
    await expect(page.getByText(item.frames[1].obs_id,{exact:true})).toBeVisible();
    await page.getByRole('slider',{name:'Selected frame',exact:true}).fill('0');
    await page.getByRole('button',{name:'Play',exact:true}).click();
    await expect(page.getByText(item.frames[1].obs_id,{exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Pause',exact:true}).click();
    await page.getByRole('combobox',{name:'Speed',exact:true}).selectOption('0.5');
  }
  expect(errors).toEqual([]);
});

test('inspection, synchronized comparison, overlays, exports and immutable restore',async({page,context})=>{
  const item=catalog.find((s:any)=>s.key==='m101');
  await page.goto(`/sequence/${item.id}`);
  await expect(page.getByRole('heading',{name:'M101',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Zoom in',exact:true}).click();
  await page.getByRole('img',{name:/Infrared sky/}).press('ArrowLeft');
  await page.getByRole('img',{name:/Infrared sky/}).press('Enter');
  await expect(page.getByText('ICRS · degrees',{exact:true})).toBeVisible();
  await page.getByRole('checkbox',{name:'Joint support (cyan)',exact:true}).check();
  await page.getByRole('button',{name:'A/B compare',exact:true}).click();
  await expect(page.locator('canvas')).toHaveCount(2);
  await page.locator('canvas').nth(1).press('Enter');
  await expect(page.getByRole('definition').filter({hasText:item.frames[1].utc_mid})).toBeVisible();
  await page.getByRole('button',{name:'A/B compare',exact:true}).click();
  await context.grantPermissions(['clipboard-read','clipboard-write']);
  await page.getByRole('button',{name:'Share view ↗',exact:true}).click();
  const link=await page.evaluate(()=>navigator.clipboard.readText());
  expect(link).toContain('zoom=1.25');expect(link).toContain('x=20');expect(link).toContain('spectral');
  const fresh=await context.newPage();await fresh.goto(link);
  await expect(fresh.getByRole('heading',{name:'M101',exact:true})).toBeVisible();
  await expect(fresh.getByRole('checkbox',{name:'Joint support (cyan)',exact:true})).toBeChecked();
  const provenance=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export provenance ↓',exact:true}).click();
  const file=await provenance;const data=JSON.parse(readFileSync((await file.path())!,'utf8'));
  expect(data.id).toEqual(item.id);expect(data.numerical_products_authorized).toBe(false);
  const image=page.waitForEvent('download');await page.getByRole('button',{name:'Export labeled image ↓',exact:true}).click();
  expect((await image).suggestedFilename()).toMatch(/\.png$/);
  await page.screenshot({path:'artifacts/explorer-desktop.png',fullPage:true});
});

test('methods dialog traps focus, restores trigger and has no critical accessibility findings',async({page})=>{
  await page.goto('/');await expect(page.getByRole('button',{name:'Data & methods',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Data & methods',exact:true}).click();
  await expect(page.getByRole('dialog',{name:'Real observations. Visible limits.',exact:true})).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Data & methods',exact:true})).toBeFocused();
  const findings=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag22aa']).analyze();
  expect(findings.violations).toEqual([]);
});

test('mobile controls, reduced motion and fixed field remain usable',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/');await expect(page.getByRole('heading',{name:'WISE 0855',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Pause',exact:true})).toHaveCount(0);
  await page.getByTitle('Examples',{exact:true}).click();
  await page.getByRole('button',{name:/R Draconis .*frames/}).click();
  await expect(page.getByRole('heading',{name:'R Draconis',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'artifacts/explorer-mobile.png',fullPage:true});
});

test('real coordinate search, date/wavelength controls and validation',async({page})=>{
  await page.goto('/');await expect(page.getByRole('heading',{name:'WISE 0855',exact:true})).toBeVisible();
  await page.getByRole('textbox',{name:'Right ascension',exact:true}).fill('08h55m10.831s');
  await page.getByRole('textbox',{name:'Declination',exact:true}).fill('-7d14m42.53s');
  await page.getByRole('button',{name:'Search archive ↗',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Current coverage',exact:true})).toBeVisible({timeout:100_000});
  await expect(page.getByLabel('Start UTC date')).toBeVisible();
  await expect(page.getByLabel('Wavelength goal · µm')).toBeVisible();
  await page.getByRole('button',{name:'Open live sequence',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Your sky field',exact:true})).toBeVisible({timeout:100_000});
  await expect(page.locator('.badge')).toContainText('live');
  await expect(page.getByText('2025W19_1B_0116_1',{exact:true})).toBeVisible();
  await page.getByRole('textbox',{name:'Declination',exact:true}).fill('91');
  await page.getByRole('button',{name:'Search archive ↗',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('declination');
});

test('coordinate URLs query an arbitrary field and restore the requested FOV',async({page})=>{
  await page.goto('/sky?ra=12.345&dec=-32.1&fov_arcmin=7');
  await expect(page.getByRole('heading',{name:'Current coverage',exact:true})).toBeVisible({timeout:100_000});
  await expect(page.getByRole('textbox',{name:'Right ascension',exact:true})).toHaveValue('12.345');
  await expect(page.getByRole('spinbutton',{name:'Field of view · arcminutes',exact:true})).toHaveValue('7');
});

test('failed assets preserve identity, pause playback and recover on retry',async({page,context})=>{
  await page.goto('/');await expect(page.getByRole('heading',{name:'WISE 0855',exact:true})).toBeVisible();
  await context.setOffline(true);
  await page.getByRole('button',{name:/M101 .*frames/}).click();
  await expect(page.getByRole('status')).toContainText('2025W22_1B_0584_1');
  await expect(page.getByRole('status')).toContainText('Playback paused');
  await expect(page.getByRole('heading',{name:'WISE 0855',exact:true})).toBeVisible();
  await context.setOffline(false);
  await page.getByRole('button',{name:'Retry requested frames',exact:true}).click();
  await expect(page.getByRole('heading',{name:'M101',exact:true})).toBeVisible();
});

test('measure prepared startup and decoded frame changes',async({page})=>{
  await page.goto('/');
  await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.ready);
  const first=await page.evaluate(()=>performance.now());
  const swaps:number[]=[];
  const draws:number[]=[],scheduling:number[]=[],observed:number[]=[];
  for(let index=0;index<5;index++){
    const sample=await page.evaluate(async()=>{
      const before=performance.now();
      const canvas=document.querySelector('canvas')!;
      const previous=canvas.dataset.ready;
      const next=document.querySelector<HTMLButtonElement>('button[aria-label="Next frame"]')!;
      const back=document.querySelector<HTMLButtonElement>('button[aria-label="Previous frame"]')!;
      const label=document.querySelector('input[aria-label="Selected frame"]') as HTMLInputElement;
      (label.value==='0'?next:back).click();
      while(canvas.dataset.ready===previous)await new Promise(resolve=>requestAnimationFrame(resolve));
      // Measure completed canvas updates, separately from a delayed headless RAF poll.
      // The poll can wake tens of milliseconds after the new pixels already exist.
      return {total:Number(canvas.dataset.renderFinished)-before,observed:performance.now()-before,draw:Number(canvas.dataset.renderMs),scheduling:Number(canvas.dataset.renderStarted)-before};
    });
    swaps.push(sample.total);draws.push(sample.draw);scheduling.push(sample.scheduling);observed.push(sample.observed);
  }
  writeFileSync('artifacts/performance.json',JSON.stringify({baseURL:page.url(),checked_utc:new Date().toISOString(),first_frame_ms:first,decoded_swaps_ms:swaps,canvas_draw_ms:draws,event_to_draw_ms:scheduling,raf_observation_ms:observed,environment:'Headless Chrome on Windows, fresh browser context, actual network. No mobile throttling. Swap timing ends when draw calls finish; RAF observation delay is separate. This is not physical display presentation timing.'},null,2));
  expect(first).toBeLessThan(3000);
  expect(Math.max(...swaps)).toBeLessThan(50);
});

test('slow frame requests cannot replace a newer target selection',async({page})=>{
  await page.goto('/');await expect(page.getByRole('heading',{name:'WISE 0855',exact:true})).toBeVisible();
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:800,downloadThroughput:200_000,uploadThroughput:100_000});
  await page.getByRole('button',{name:/M101 .*frames/}).click();
  await page.getByRole('button',{name:/Barnard.*frames/}).click();
  await expect(page.getByRole('heading',{name:"Barnard's Star",exact:true})).toBeVisible({timeout:30_000});
  await page.waitForLoadState('networkidle');
  await expect(page.getByRole('heading',{name:"Barnard's Star",exact:true})).toBeVisible();
  await expect(page.getByText('2025W34_2B_0557_4',{exact:true})).toBeVisible();
  await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
});

test('date and precision wavelength controls select actual matching observations',async({page})=>{
  await page.goto('/');await expect(page.getByRole('heading',{name:'WISE 0855',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Search archive ↗',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Current coverage',exact:true})).toBeVisible({timeout:100_000});
  await page.getByLabel('Start UTC date').fill('2025-05-05');
  await page.getByLabel('End UTC date').fill('2025-05-05');
  await page.getByLabel('Wavelength goal · µm').fill('4.9674');
  await page.getByRole('button',{name:'Open live sequence',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Your sky field',exact:true})).toBeVisible({timeout:100_000});
  const id=new URL(page.url()).pathname.split('/sequence/')[1];
  const manifest=await (await page.request.get('/v1/sequences/'+id)).json();
  expect(manifest.coverage_state).toBe('single');
  expect(manifest.frames[0].utc_mid).toMatch(/^2025-05-05/);
  expect(Math.abs(manifest.frames[0].wavelength_um-4.9674)).toBeLessThanOrEqual(.1*manifest.frames[0].bandwidth_um);
  expect(manifest.science_status).toBe('context_only');
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'A/B compare',exact:true})).toBeDisabled();
});

test('looping, shared stretch and reset controls affect the rendered view',async({page})=>{
  await page.goto('/');await expect(page.getByRole('heading',{name:'WISE 0855',exact:true})).toBeVisible();
  await page.getByRole('slider',{name:'Selected frame',exact:true}).fill('2');
  await page.getByRole('checkbox',{name:'Loop',exact:true}).check();
  await page.getByRole('combobox',{name:'Speed',exact:true}).selectOption('2');
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await expect(page.getByRole('slider',{name:'Selected frame',exact:true})).toHaveValue('0');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.getByRole('slider',{name:'Shared display stretch',exact:true}).fill('2');
  await page.getByRole('button',{name:'Zoom in',exact:true}).click();
  await page.getByRole('button',{name:'Reset view',exact:true}).click();
  await expect(page.getByRole('slider',{name:'Shared display stretch',exact:true})).toHaveValue('1');
});
