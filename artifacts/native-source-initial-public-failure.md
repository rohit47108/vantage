# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: native-source.spec.ts >> general source workflow uses frozen discovery, all six native detectors and lazy inspection
- Location: tests\browser\native-source.spec.ts:9:1

# Error details

```
Test timeout of 240000ms exceeded.
```

```
Error: locator.check: Test timeout of 240000ms exceeded.
Call log:
  - waiting for getByLabel('Include 2025W29_1A_0544_2/D2', { exact: true })

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - banner [ref=e4]:
    - link "Vantage home" [ref=e5] [cursor=pointer]:
      - /url: /
      - strong [ref=e9]: Vantage
    - button "← Back to sky" [ref=e10] [cursor=pointer]
  - main [ref=e11]:
    - generic [ref=e12]:
      - paragraph [ref=e13]: Measure light
      - heading "Measure a source" [level=1] [ref=e14]
      - paragraph [ref=e15]: Choose a point of light, find its observations, and inspect its brightness across SPHEREx wavelengths.
      - paragraph [ref=e16]: Point-source measurements need a clear, isolated source. Measurements at different dates stay separate; this is not an instantaneous spectrum.
    - region "Find source observations" [ref=e17]:
      - heading "Find source observations" [level=2] [ref=e18]
      - group "Source position and dates" [ref=e19]:
        - button "Use P330E calibration example" [ref=e21] [cursor=pointer]
        - generic [ref=e22]:
          - generic [ref=e23]:
            - text: Find an object
            - textbox "Object name" [ref=e24]:
              - /placeholder: M101, Vega, Barnard's Star
          - button "Find object" [ref=e25] [cursor=pointer]
        - generic [ref=e26]:
          - generic [ref=e27]:
            - generic [ref=e28]:
              - text: Source label
              - textbox "Source label" [ref=e29]: P330E
            - generic [ref=e30]:
              - text: Right ascension · degrees
              - spinbutton "Right ascension · degrees" [ref=e31]: "247.8908392831"
            - generic [ref=e32]:
              - text: Declination · degrees
              - spinbutton "Declination · degrees" [ref=e33]: "30.14604947207"
          - generic [ref=e34]:
            - generic [ref=e35]:
              - text: Start date · UTC
              - textbox "Start date · UTC" [ref=e36]: 2025-07-01
            - generic [ref=e37]:
              - text: End date · UTC
              - textbox "End date · UTC" [ref=e38]: 2025-07-31
          - group [ref=e39]:
            - generic "Catalog motion and survey coverage" [ref=e40] [cursor=pointer]
          - generic [ref=e41]:
            - button "Find source observations" [ref=e42] [cursor=pointer]
            - button "Refresh archive search" [ref=e43] [cursor=pointer]
    - region "Choose observations" [ref=e44]:
      - heading "Choose observations" [level=2] [ref=e45]
      - paragraph [ref=e46]: 147 DR1 candidates · 0 observations from releases awaiting native calibration approval. Metadata query completed for the listed collections.
      - paragraph [ref=e47]: Metadata retrieved 2026-11-15T13:42:36.193006+00:00 · cached archive query.
      - paragraph [ref=e48]: Each native image still needs coverage, pixel-quality, exact calibration and fit checks.
      - group "Observation selection" [ref=e49]:
        - generic [ref=e51]:
          - button "Select supported observations" [ref=e52] [cursor=pointer]
          - button "Clear observation selection" [ref=e53] [cursor=pointer]
        - paragraph [ref=e54]: 1 observations selected · up to 512 per extraction. Native input size is roughly 4 MB before cache reuse.
        - generic [ref=e55]:
          - text: Filter observation IDs
          - textbox "Filter observation IDs" [active] [ref=e56]: 2025W29_1A_0544_2
        - region "Native observation selection" [ref=e57]:
          - table "Individual candidate observations · UTC dates · selection does not guarantee a usable measurement" [ref=e58]:
            - caption [ref=e59]: Individual candidate observations · UTC dates · selection does not guarantee a usable measurement
            - rowgroup [ref=e60]:
              - row [ref=e61]:
                - columnheader "Include" [ref=e62]
                - columnheader "Observation" [ref=e63]
                - columnheader "UTC date" [ref=e64]
                - columnheader "Detector" [ref=e65]
                - columnheader "Release" [ref=e66]
            - rowgroup
        - generic [ref=e67]:
          - button "Previous observation page" [disabled] [ref=e68]
          - generic [ref=e69]: Page 1 of 1
          - button "Next observation page" [disabled] [ref=e70]
        - generic [ref=e71]:
          - generic [ref=e72]:
            - text: Native extraction method
            - combobox "Native extraction method" [ref=e73]:
              - option "Effective PSF fit" [selected]
              - option "Aperture with PSF correction"
          - generic [ref=e74]:
            - text: Source position during fitting
            - combobox "Source position during fitting" [ref=e75]:
              - option "Refine when bright enough" [selected]
              - option "Keep supplied position"
        - group [ref=e76]:
          - generic "Aperture and background geometry" [ref=e77] [cursor=pointer]
        - button "Measure selected observations" [ref=e78] [cursor=pointer]
```

# Test source

```ts
  1   | import {test,expect} from '@playwright/test';
  2   | import AxeBuilder from '@axe-core/playwright';
  3   | import {readFileSync} from 'node:fs';
  4   |
  5   | const acquisition=JSON.parse(readFileSync('research/updates/2026-11-15/native-extraction/acquisition.json','utf8'));
  6   | const old=JSON.parse(readFileSync('research/updates/2026-11-15/photometry/benchmark.json','utf8'));
  7   | // Narrow discovery correctly excludes the uncovered reference cutout.
  8   | // Use a covered, authentic poor-fit input for browser rejection guidance;
  9   | // retained-fixture regressions separately test missing native coverage.
  10  | const wanted=[...acquisition.observations.filter((row:{detector:number})=>row.detector!==2),...old.observations.slice(0,2)];
  11  |
  12  | test('general source workflow uses frozen discovery, all six native detectors and lazy inspection',async({page})=>{
  13  |   test.setTimeout(240_000);
  14  |   await page.goto('/?view=measure');
  15  |   await expect(page.getByRole('heading',{name:'Measure a source',exact:true})).toBeVisible();
  16  |   await page.getByRole('button',{name:'Use P330E calibration example'}).click();
  17  |   await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toHaveValue('247.8908392831');
  18  |   await page.getByRole('button',{name:'Find source observations'}).click();
  19  |   await expect(page.getByRole('heading',{name:'Choose observations',exact:true})).toBeVisible({timeout:90_000});
> 20  |   await page.getByRole('button',{name:'Clear observation selection'}).click();
      |                                                                                  ^ Error: locator.check: Test timeout of 240000ms exceeded.
  21  |   for(const row of wanted){
  22  |     await page.getByLabel('Filter observation IDs').fill(row.obs_id);
  23  |     await expect(page.getByLabel(`Include ${row.obs_id}/D${row.detector}`,{exact:true})).toBeVisible();
  24  |     await page.getByLabel(`Include ${row.obs_id}/D${row.detector}`,{exact:true}).check();
  25  |   }
  26  |   await page.getByLabel('Filter observation IDs').fill('');
  27  |   await expect(page.getByTestId('native-selection-count')).toContainText('7 observations selected');
  28  |   await page.getByRole('button',{name:'Measure selected observations',exact:true}).click();
  29  |   await expect(page.getByRole('heading',{name:'P330E · measured light',exact:true})).toBeVisible({timeout:120_000});
  30  |   await expect(page.getByText('6 pass fit checks',{exact:true})).toBeVisible();
  31  |   await page.getByRole('button',{name:'Inspect 2025W30_1B_0610_2/D1',exact:true}).click();
  32  |   await expect(page.getByTestId('native-measured-flux')).toContainText('31,248.75');
  33  |   await expect(page.getByRole('img',{name:'Native brightness cutout; source cross marks the measured position. Array rows increase upward.'})).toBeVisible();
  34  |   await expect(page.getByText('Solid: fit core · dashed: background annulus').first()).toBeVisible();
  35  |   await expect(page.getByText('1 need fit review',{exact:true})).toBeVisible();
  36  |   await page.getByRole('button',{name:'Inspect 2025W29_1A_0544_1/D2',exact:true}).click();
  37  |   await expect(page.getByTestId('native-selected-sample')).toContainText('exceeds the declared maximum of 3');
  38  |   const download=page.waitForEvent('download');await page.getByRole('link',{name:'ECSV with units'}).click();
  39  |   expect((await download).suggestedFilename()).toMatch(/samples\.ecsv$/);
  40  |   await page.getByRole('button',{name:'Share measured light',exact:true}).click();
  41  |   const link=await page.getByLabel('Measured-light link').inputValue();await page.goto(link);
  42  |   await expect(page.getByRole('heading',{name:'P330E · measured light',exact:true})).toBeVisible();
  43  |   await expect(page.getByTestId('native-selected-sample')).toContainText('exceeds the declared maximum of 3');
  44  |   expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations).toEqual([]);
  45  |   await page.screenshot({path:'artifacts/native-source-desktop.png',fullPage:true});
  46  |   await page.getByRole('button',{name:'Clear observation selection'}).click();
  47  |   await page.getByLabel('Filter observation IDs').fill('2025W30_1B_0610_2');
  48  |   await page.getByLabel('Include 2025W30_1B_0610_2/D1',{exact:true}).check();
  49  |   const submitted=page.waitForRequest(r=>r.url().endsWith('/v1/native-source-samples')&&r.method()==='POST');
  50  |   await page.getByRole('button',{name:'Measure selected observations',exact:true}).click();
  51  |   expect((await submitted).postDataJSON().observation_indices).toHaveLength(1);
  52  |   await expect(page.getByText('1 pass fit checks',{exact:true})).toBeVisible({timeout:60_000});
  53  | });
  54  |
  55  | test('moving-source links preserve coordinates and both motion components on mobile',async({page})=>{
  56  |   await page.setViewportSize({width:390,height:844});
  57  |   await page.goto('/?view=measure&source_ra=247.8908392831&source_dec=30.14604947207&pmra=-8.882&pmdec=-38.705&ref_epoch=2016&source_name=P330E');
  58  |   await page.getByText('Catalog motion and survey coverage',{exact:true}).click();
  59  |   await expect(page.getByLabel('Apply supplied angular motion')).toBeChecked();
  60  |   await expect(page.getByLabel('RA motion · mas/year · includes cos(dec)')).toHaveValue('-8.882');
  61  |   await expect(page.getByLabel('Declination motion · mas/year')).toHaveValue('-38.705');
  62  |   await page.reload();await page.getByText('Catalog motion and survey coverage',{exact:true}).click();
  63  |   await expect(page.getByLabel('Apply supplied angular motion')).toBeChecked();
  64  |   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  65  |   expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()).violations).toEqual([]);
  66  |   await page.screenshot({path:'artifacts/native-source-mobile.png',fullPage:true});
  67  | });
  68  |
  69  | test('sky inspection and real Gaia selection carry the source into native measurement',async({page})=>{
  70  |   const catalog=JSON.parse(readFileSync('public/prepared/catalog.json','utf8'));
  71  |   const field=catalog.find((row:{key:string})=>row.key==='m101');
  72  |   await page.goto(`/sequence/${field.id}?layers=gaia`);
  73  |   await expect(page.getByRole('heading',{name:'M101',exact:true})).toBeVisible();
  74  |   await page.getByRole('img',{name:/Infrared sky/}).press('Enter');
  75  |   await page.getByRole('button',{name:'Measure this sky position',exact:true}).click();
  76  |   const point=new URL(page.url());
  77  |   await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toHaveValue(point.searchParams.get('source_ra')!);
  78  |   await expect(page.getByLabel('Declination · degrees',{exact:true})).toHaveValue(point.searchParams.get('source_dec')!);
  79  |   await page.getByRole('button',{name:'← Back to sky',exact:true}).click();
  80  |   await expect(page).toHaveURL(new RegExp('/sequence/'+field.id));
  81  |   await page.getByText('Other telescopes · Gaia / WISE',{exact:true}).click();
  82  |   const select=page.getByRole('combobox',{name:'Select Gaia source',exact:true});
  83  |   await expect(select).toBeVisible({timeout:90_000});
  84  |   const layer=await (await page.request.get(`/v1/surveys/gaia?sequence_id=${field.id}`)).json();
  85  |   const source=layer.sources.find((row:{pmra:number|null;pmdec:number|null})=>row.pmra!=null&&row.pmdec!=null);
  86  |   expect(source).toBeTruthy();await select.selectOption(source.id);
  87  |   await page.getByRole('button',{name:'Measure selected Gaia source',exact:true}).click();
  88  |   await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toHaveValue(String(source.ra));
  89  |   await expect(page.getByLabel('Declination · degrees',{exact:true})).toHaveValue(String(source.dec));
  90  |   await page.getByText('Catalog motion and survey coverage',{exact:true}).click();
  91  |   await expect(page.getByLabel('Apply supplied angular motion')).toBeChecked();
  92  |   await expect(page.getByLabel('RA motion · mas/year · includes cos(dec)')).toHaveValue(String(source.pmra));
  93  |   await expect(page.getByLabel('Declination motion · mas/year')).toHaveValue(String(source.pmdec));
  94  |   await expect(page.getByLabel('Reference epoch · Julian year')).toHaveValue(String(source.ref_epoch));
  95  | });
  96  |
  97  | test('source failures, reference loading and real queued cancellation retain clear states',async({page})=>{
  98  |   await page.goto('/?view=measure');
  99  |   let release!:()=>void;const gate=new Promise<void>(resolve=>release=resolve);
  100 |   await page.route('**/v1/source-targets/p330e',async route=>{await gate;await route.continue();});
  101 |   await page.getByRole('button',{name:'Use P330E calibration example'}).click();
  102 |   await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toBeDisabled();
  103 |   release();await expect(page.getByLabel('Right ascension · degrees',{exact:true})).toHaveValue('247.8908392831');
  104 |   await page.route('**/v1/source-fields',route=>route.fulfill({status:503,json:{detail:'Archive temporarily unavailable'}}));
  105 |   await page.getByRole('button',{name:'Find source observations',exact:true}).click();
  106 |   await expect(page.getByRole('alert')).toContainText('Archive temporarily unavailable');
  107 |   await expect(page.getByRole('heading',{name:'Choose observations',exact:true})).toHaveCount(0);
  108 |   await page.unroute('**/v1/source-fields');
  109 |   await page.getByLabel('Source label',{exact:true}).fill('P330E cancellation '+Date.now());
  110 |   await page.getByRole('button',{name:'Refresh archive search',exact:true}).click();
  111 |   await page.getByRole('button',{name:'Cancel source analysis',exact:true}).click();
  112 |   await expect(page.getByText('Source analysis cancelled.',{exact:true})).toBeVisible();
  113 |   await expect(page.getByRole('button',{name:'Find source observations',exact:true})).toBeEnabled();
  114 | });
  115 |
```
