"""Survey-combined SPHEREx context, never a source spectrum or temporal image.

Native schema and URL construction: https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/
Range sections: https://docs.astropy.org/en/stable/io/fits/usage/cloud.html
"""
import hashlib
import json
from functools import lru_cache
import aiohttp
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS
from astropy_healpix import HEALPix
from backend.science import ROOT, grid

POLICY='hips-context-2'
BASE='https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/hips_20261026'
HEALPIX=HEALPix(nside=32,order='nested',frame='icrs')
EVIDENCE=ROOT/'research/updates/2026-11-14/hips-live-probe.json'

@lru_cache(maxsize=1)
def metadata():
    evidence=json.loads(EVIDENCE.read_text(encoding='utf-8'))
    channels=[]
    for i,row in enumerate(evidence['channels']):
        detector,channel=int(row['DETECTOR']),int(row['SUBCHAN'])
        if i != 17*(detector-1)+channel-1:
            raise ValueError('Unsupported cube channel schema')
        channels.append({'index':i,'detector':detector,'channel':channel,
                         'wavelength_um':row['WAVELENGTH'],'bandwidth_um':row['BANDWIDTH'],
                         'min_um':row['WL_MIN'],'max_um':row['WL_MAX'],
                         'blank':f'D{detector}:{channel:02}' in evidence['primary']['BLANKCH'].split(',')})
    if len(channels)!=102:raise ValueError('Unexpected cube depth')
    return {'id':hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(),'policy':POLICY,
            'title':'SPHEREx DR1 survey-combined visualization','channels':channels,
            'checked_utc':evidence['checked_utc'],'properties_url':evidence['properties_url'],
            'native_base_url':BASE,'unit':'MJy/sr','numerical_products_authorized':False,
            'limitations':['Survey-combined imagery is not a temporal sequence.',
                           'No per-channel variance is supplied. This view does not measure a validated source spectrum.',
                           'Stripes near bright emission lines can be mosaic artifacts.'],
            'credits':'NASA/SPHEREx; Caltech/IPAC/IRSA. DR1 doi:10.26131/IRSA678.',
            'source_documentation':'https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/'}

def tile_index(ra,dec):
    return HEALPIX.lonlat_to_healpix(np.asarray(ra)*u.deg,np.asarray(dec)*u.deg)

def read_tile(ipix,layer,ra,dec):
    url=f'{BASE}/Norder5/Dir{int(ipix)//10000*10000}/Npix{int(ipix)}_cube.fits'
    # Independent handles; never materialize .data on a cube extension.
    with fits.open(url,use_fsspec=True,memmap=False,
                   fsspec_kwargs={'block_size':65536,'client_kwargs':{'timeout':aiohttp.ClientTimeout(total=45,connect=8,sock_read=20)}}) as hdus:
        if hdus['IMAGE'].shape!=(102,512,512):raise ValueError('Unsupported native cube shape')
        w=WCS(hdus['IMAGE'].header,fobj=hdus).celestial
        x,y=w.world_to_pixel_values(ra,dec)
        ix,iy=np.rint(x).astype(int),np.rint(y).astype(int)
        inside=(ix>=0)&(ix<512)&(iy>=0)&(iy<512)
        out=[np.full(ra.shape,np.nan),np.zeros(ra.shape,dtype=np.int32),np.zeros(ra.shape,dtype=np.uint32)]
        if np.any(inside):
            x0,x1=int(ix[inside].min()),int(ix[inside].max())+1
            y0,y1=int(iy[inside].min()),int(iy[inside].max())+1
            for j,name in enumerate(['IMAGE','NHITS','FLAGS']):
                section=np.asarray(hdus[name].section[layer,y0:y1,x0:x1])
                out[j][inside]=section[iy[inside]-y0,ix[inside]-x0]
        provenance={'url':url,'tile':int(ipix),'mjd_start':hdus[0].header['MJD-BEG'],
                    'mjd_end':hdus[0].header['MJD-END'],'product_version':hdus[0].header['VERSION']}
    return *out,provenance

def render_plane(center,fov,layer,size=160,tile_reader=None):
    center=np.asarray(center,dtype=float)
    if center.shape!=(2,) or not np.all(np.isfinite(center)) or abs(center[1])>90:
        raise ValueError('Enter finite sky coordinates with declination between -90 and 90 degrees.')
    if not np.isfinite(fov) or not 1<=fov<=120 or not 16<=size<=256:
        raise ValueError('Spectral context fields must be 1–120 arcminutes; output is limited to 256 pixels.')
    if not isinstance(layer,int) or not 0<=layer<102:raise ValueError('Choose a channel from 0 to 101.')
    center[0]%=360
    channel=metadata()['channels'][layer]
    w,size=grid(center.tolist(),fov,size)
    yy,xx=np.indices((size,size))
    ra,dec=w.pixel_to_world_values(xx,yy)
    image=np.full((size,size),np.nan)
    hits=np.zeros((size,size),dtype=int)
    flags=np.zeros((size,size),dtype=np.uint32)
    sources=[]
    if not channel['blank']:
        tiles=tile_index(ra,dec)
        if len(np.unique(tiles))>9:raise ValueError('This region crosses too many tiles. Choose a smaller field.')
        for ipix in np.unique(tiles):
            mask=tiles==ipix
            values,counts,bits,source=(tile_reader or read_tile)(ipix,layer,ra[mask],dec[mask])
            image[mask],hits[mask],flags[mask]=values,counts,bits
            sources.append(source)
    image[(hits<=0)|~np.isfinite(image)]=np.nan
    arrays_hash=hashlib.sha256(image.astype('<f8').tobytes()+hits.astype('<i4').tobytes()+flags.astype('<u4').tobytes()).hexdigest()
    canonical={'policy':POLICY,'metadata':metadata()['id'],'center_deg':center.tolist(),
               'fov_arcmin':fov,'layer':layer,'size':size,'sources':sources,'array_sha256':arrays_hash}
    identity=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    brightness=np.where(np.isfinite(image),image,None).tolist()
    return {'id':identity,**canonical,'channel':channel,'shape':[size,size],
            'grid':dict(w.to_header()),'brightness':brightness,'hits':hits.tolist(),'flags':flags.tolist(),
            'coverage_fraction':float(np.isfinite(image).mean()),'units':'MJy/sr',
            'sampling':'Nearest native HPX pixel on a north-up, east-left TAN display grid; visualization only.',
            'numerical_products_authorized':False,'metadata_url':'/v1/spectral/metadata',
            'limitations':metadata()['limitations'],'credits':metadata()['credits']}
