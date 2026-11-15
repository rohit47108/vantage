"""Research-only bounded header scan and small native FITS fixtures."""
from concurrent.futures import ThreadPoolExecutor
import io, json, warnings
from itertools import combinations
from scipy.ndimage import map_coordinates
from astropy.time import Time
from astropy.coordinates import get_body_barycentric, Distance
from astropy import log
from inspect_fits import EV, FIX, SkyCoord, WCS, fits, np, u, requests, read_table, download
from probe_metadata import probe

warnings.filterwarnings('ignore')
log.setLevel('ERROR')
centers = json.loads((EV/'full_challenge_coordinates.json').read_text())
astrometry = {
 'barnard': (269.4520769586187,4.693364966576667,-801.551,10362.394,546.9759,-110.11),
 'eps_indi_b': (centers['eps_indi_b'][0],centers['eps_indi_b'][1],3981.977,-2466.832,None,None),
 'wise0855': (133.81890825,-7.247048,-8123.7,673.2,439.0,None),
}
def prediction(k, m):
    if k not in astrometry: return SkyCoord(*centers[k],unit='deg')
    a,d,px,py,p,v=astrometry[k]
    kw = {'distance':Distance(parallax=p*u.mas)} if p else {}
    if v is not None: kw['radial_velocity']=v*u.km/u.s
    c = SkyCoord(a*u.deg,d*u.deg,pm_ra_cosdec=px*u.mas/u.yr,pm_dec=py*u.mas/u.yr,obstime=Time('J2000'),**kw)
    t=Time(m,format='mjd',scale='utc'); c=c.apply_space_motion(t)
    if p:
        c=SkyCoord(c.cartesian.without_differentials()-get_body_barycentric('earth',t),frame='icrs')
        c.representation_type='spherical'
    return c

def dataset(k,detector):
    t=read_table(EV/f'full_sia_{k}_qr2.vot')
    t=t[t['energy_bandpassname']==f'SPHEREx-D{detector}'];t.sort('t_min')
    return t

def calibrations():
    files={2:FIX/'spectral_wcs_d2.fits'}
    t=dataset('wise0855',6)
    if not (EV/'full_wise_d6_datalink.vot').exists():
        probe('full_wise_d6_datalink','https://irsa.ipac.caltech.edu/datalink/links/spherex',{'ID':str(t['obs_publisher_did'][0])})
    links=read_table(EV/'full_wise_d6_datalink.vot')
    for row in links:
        if 'spectral_wcs' in str(row['access_url']):
            files[6]=download('full_spectral_wcs_d6',str(row['access_url']));break
    result = {}
    for detector, path in files.items():
        with fits.open(path, memmap=False) as hdus:
            assert hdus['CWAVE'].header['DETECTOR'] == detector
            # Materialize both planes before parallel scans. Astropy lazy HDU reads
            # on a shared file handle can race and return the wrong image plane.
            maps = {name: np.array(hdus[name].data, dtype=np.float64) for name in ('CWAVE', 'CBAND')}
            for array in maps.values():
                array.setflags(write=False)
            assert 1 < np.min(maps['CWAVE']) < np.max(maps['CWAVE']) < 5.1
            assert 0 < np.min(maps['CBAND']) < np.max(maps['CBAND']) < 0.1
            result[detector] = (path, maps)
    return result

def header(row):
    cloud=json.loads(str(row['cloud_access']))['aws']
    url=f"https://{cloud['bucket_name']}.s3.{cloud['region']}.amazonaws.com/{cloud['key']}"
    with requests.get(url,headers={'Range':'bytes=0-65535'},timeout=(6,15),stream=True) as r:
        if r.status_code != 206: raise ValueError(f'header range {r.status_code}')
        b=io.BytesIO(r.content)
    fits.Header.fromfile(b)
    return url,fits.Header.fromfile(b)

def wavelength(cal, xy):
    x,y=xy
    return [float(map_coordinates(cal[n],[[y],[x]],order=1,mode='constant',cval=np.nan)[0])
            for n in ['CWAVE','CBAND']]

def scan(k,d,row,cal):
    try:
        path, maps = cal
        s3,h=header(row);w=WCS(h);m=(float(row['t_min'])+float(row['t_max']))/2
        c=SkyCoord(*centers[k],unit='deg');p=prediction(k,m)
        xy=[float(x) for x in w.world_to_pixel(p)];center_xy=[float(x) for x in w.world_to_pixel(c)]
        sky_grid=c.spherical_offsets_by(*[v*u.arcsec for v in np.meshgrid([-120,0,120],[-120,0,120])])
        gx,gy=w.world_to_pixel(sky_grid)
        samples=np.stack([map_coordinates(maps[n],[gy,gx],order=1,mode='constant',cval=np.nan) for n in ('CWAVE','CBAND')],axis=-1)
        if not all(45<x<1994 for x in center_xy) or not np.isfinite(samples).all() or not all(3<x<2037 for x in xy):
            return None
        return {'obs_id':str(row['obs_id']),'publisher_id':str(row['obs_publisher_did']),
                'detector':d,'release':'qr2','ibe':str(row['access_url']),'s3':s3,
                'mjd_mid':m,'utc_mid':Time(m,format='mjd',scale='utc').isot,
                'predicted_target_deg':[float(p.ra.deg),float(p.dec.deg)],
                'target_xy':xy,'center_xy':center_xy,'target_lambda_width_um':wavelength(maps,xy),
                'field_9_lambda_width_um':samples.reshape(9,2).tolist(),
                'source_calibration':path.relative_to(FIX.parent.parent).as_posix()}
    except Exception as e:
        return {'obs_id':str(row['obs_id']),'error':str(e)}

def ranking(a,b):
    f=np.array(a['field_9_lambda_width_um']); g=np.array(b['field_9_lambda_width_um'])
    frac=float(np.mean((abs(f[:,0]-g[:,0]) <= .1*np.minimum(f[:,1],g[:,1])) &
                       (abs(np.log(f[:,1]/g[:,1])) <= np.log(1.10))))
    l,w=a['target_lambda_width_um'];v,z=b['target_lambda_width_um']
    m=abs(l-v)/min(w,z)
    return frac,m,abs(np.log(w/z))

def select(rows):
    ranked=[]
    for group in combinations(rows,3):
        times=[a['mjd_mid'] for a in group]
        if min(np.diff(times))<1:continue
        pairs=[ranking(a,b) for a,b in combinations(group,2)]
        points = np.array([r['field_9_lambda_width_um'] for r in group])
        min_width = points[:,:,1].min(axis=0)
        joint = (np.ptp(points[:,:,0],axis=0) <= .1*min_width) & (points[:,:,1].max(axis=0) <= 1.10*min_width)
        frac=float(joint.mean());m=max(t[1] for t in pairs);width=max(t[2] for t in pairs)
        score=(int(m<=.1 and width<=np.log(1.10)),frac, min(1,(times[-1]-times[0])/160),-m)
        ranked.append((score,group,{'joint_9point_spectral_fraction':frac,'max_target_delta_over_width':m,'max_target_log_width_ratio':width,'span_days':times[-1]-times[0]}))
    return sorted(ranked,key=lambda a:a[0],reverse=True)

def save_crop(k,i,entry,center):
    name=f'full_{k}_frame{i+1}'
    existing = FIX/(name+'.fits')
    tagged = name+'_'+entry['obs_id']
    if (FIX/(tagged+'.fits')).exists() or (existing.exists() and fits.getheader(existing,'IMAGE')['OBSID'] != entry['obs_id']):
        name = tagged
    src=entry['ibe']; args={'center':f'{center[0]},{center[1]}deg','size':'0.1deg'}
    try:
        path=download(name,src,args)
    except Exception:
        from native_crop_research import remote_native_crop
        path=remote_native_crop(name,{'url':src},*center)
        meta=EV/(name+'_download.json'); data=json.loads(meta.read_text())
        data['access_date']='2026-11-07';meta.write_text(json.dumps(data,indent=2))
    with fits.open(path) as h:
        assert h['IMAGE'].header['OBSID'] == entry['obs_id']
        assert h['IMAGE'].header['DETECTOR'] == entry['detector']
        w=WCS(h['IMAGE'].header); p=SkyCoord(*entry['predicted_target_deg'],unit='deg')
        x,y=[float(v) for v in w.world_to_pixel(p)]
        im=np.asarray(h['IMAGE'].data); q=np.asarray(h['FLAGS'].data,dtype=np.uint32);var=np.asarray(h['VARIANCE'].data)
        cy,cx=np.indices(im.shape); rad=np.hypot(cx-x,cy-y)
        core=rad<=1.5;ann=(rad>=3)&(rad<=6)&np.isfinite(im)
        b=float(np.median(im[ann])) if np.any(ann) else None
        bg=im[ann]; mad=float(1.4826*np.median(abs(bg-b))) if b is not None else None
        bits=int(np.bitwise_or.reduce(q[core],initial=np.uint32(0)))
        peak=float(np.nanmax(im[core])-b) if np.any(core) and b is not None and np.any(np.isfinite(im[core])) else None
        var_ok=float(np.mean(np.isfinite(var[core]) & (var[core]>0))) if np.any(core) else 0
        result=entry|{'fixture':'research/fixtures/'+path.name,'shape_yx':list(im.shape),
            'target_crop_xy':[x,y],'core_flag_bits':[z for z in range(32) if bits&(1<<z)],
            'core_pixel_count':int(np.count_nonzero(core)),'core_positive_finite_variance_fraction':var_ok,
            'peak_minus_annulus_median_mjy_sr':peak,'annulus_mad_scaled_mjy_sr':mad,
            'hdu_names':[v.name for v in h]}
    return result

if __name__=='__main__':
    cs=calibrations(); results={}
    for k in centers:
        d=6 if k in ('wise0855','r_dra') else 2
        t=dataset(k,d)
        indices=np.unique(np.rint(np.linspace(0,len(t)-1,min(44,len(t)))).astype(int))
        with ThreadPoolExecutor(max_workers=6) as p:
            raw=list(p.map(lambda j:scan(k,d,t[j],cs[d]),indices))
        rows=sorted([r for r in raw if r and 'error' not in r],key=lambda x:x['mjd_mid'])
        (EV/f'full_scan_{k}.json').write_text(json.dumps(raw,indent=2,allow_nan=False))
        rank=select(rows)
        if not rank:
            print(f'No three separated candidate frames for {k}; {len(rows)} valid of {len(raw)}',flush=True)
            continue
        _,group,metrics=rank[0]
        with ThreadPoolExecutor(max_workers=3) as p:
            saved=list(p.map(lambda pair: save_crop(k,*pair,centers[k]),enumerate(group)))
        results[k]={'center_deg':centers[k],'requested_fov_arcmin':6,'scanned':len(raw),'valid_header_candidates':len(rows),
                    'header_scan_errors':sum(1 for v in raw if v and 'error' in v),
                    'sequence':saved,'selection_metrics':metrics,
                    'scope':'Research only: header and native pixel screening. No registered PSF detection, variability or significance claim.'}
        (EV/'full_challenge_sequence_screening.json').write_text(json.dumps(results,indent=2,allow_nan=False))
        print(k, metrics, [(v['obs_id'],v['utc_mid'],v['core_flag_bits']) for v in saved],flush=True)
