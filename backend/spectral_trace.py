"""102-channel native mosaic pixel traces: visualization, never photometry.

https://caltech-ipac.github.io/irsa-tutorials/spherex-hipscube/
https://docs.astropy.org/en/stable/io/fits/usage/cloud.html
"""
import hashlib
import io
import json
import time
from pathlib import Path
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.table import Table,MaskedColumn
from astropy.wcs import WCS
from pydantic import BaseModel,ConfigDict,Field
from backend.hips import metadata,tile_index
from backend.range_reader import VersionedCubeFile
from backend.science import write_json,digest,BAD_MASK,KNOWN_MASK
from backend.spectra import atomic_text

POLICY='visual-native-pixel-trace-1'


class TraceRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    plane_id:str=Field(pattern=r'^[a-f0-9]{64}$')
    x:int=Field(ge=0,le=255)
    y:int=Field(ge=0,le=255)


def sample_visual_point(ra,dec,check_cancel=lambda:None,progress=lambda stage:None,file_factory=VersionedCubeFile):
    if not np.isfinite([ra,dec]).all() or abs(dec)>90:raise ValueError('Choose finite ICRS coordinates with valid declination')
    ra=float(ra)%360;dec=float(dec);check_cancel();started=time.monotonic()
    channels=metadata()['channels'];index=int(tile_index(ra,dec))
    with file_factory(index,check_cancel=check_cancel) as stream:
        with fits.open(stream,memmap=False) as hdus:
            if hdus[0].header.get('VERSION')!='7.2.0':raise ValueError('Unapproved visualization cube processing version')
            if hdus[0].header.get('TIMESYS')!='UTC' or hdus['IMAGE'].header.get('RADESYS')!='ICRS':raise ValueError('Unsupported mosaic time or celestial reference system')
            if any(hdus[name].shape!=(102,512,512) for name in ['IMAGE','NHITS','FLAGS']):raise ValueError('Unapproved visualization cube shape')
            if u.Unit(hdus['IMAGE'].header.get('BUNIT',''))!=u.MJy/u.sr:raise ValueError('Unsupported mosaic brightness unit')
            if any(hdus[name].header['BITPIX']!=32 for name in ['NHITS','FLAGS']):raise ValueError('Unsupported mosaic count/flag storage')
            if set(hdus[0].header.get('BLANKCH','').split(','))!={'D3:17','D4:01'}:raise ValueError('Visualization blank-channel definition changed')
            native_table=hdus['SPECTRAL_CHANNELS'].data
            if len(native_table)!=102:raise ValueError('Visualization channel count changed')
            for row,expected in zip(native_table,channels):
                if row['DETECTOR']!=expected['detector'] or row['SUBCHAN']!=expected['channel'] or not np.allclose([row['WAVELENGTH'],row['BANDWIDTH']],[expected['wavelength_um'],expected['bandwidth_um']],rtol=0,atol=1e-6):
                    raise ValueError('Visualization spectral table differs from the approved grid')
            table=[{key:float(row[key]) for key in native_table.names} for row in native_table]
            wcs=WCS(hdus['IMAGE'].header,fobj=hdus).celestial
            px,py=map(float,wcs.world_to_pixel_values(ra,dec))
            if not np.isfinite([px,py]).all():raise ValueError('Selected position has no finite native cube coordinate')
            x,y=int(np.rint(px)),int(np.rint(py));inside=0<=x<512 and 0<=y<512
            arrays={name:[None]*102 for name in ['IMAGE','NHITS','FLAGS']}
            if inside:
                for first in range(0,102,17):
                    check_cancel()
                    for name in arrays:
                        section=hdus[name].section[first:first+17,y,x]
                        for offset,value in enumerate(section):
                            if np.isfinite(value):arrays[name][first+offset]=float(value) if name=='IMAGE' else int(value)&0xffffffff if name=='FLAGS' else int(value)
                    progress(f'sampling_channels_{first+17}_of_102')
            begin,end=float(hdus[0].header['MJD-BEG']),float(hdus[0].header['MJD-END'])
            if not np.isfinite([begin,end]).all() or begin>end:raise ValueError('Visualization acquisition interval is unsupported')
            source={**stream.source_info,'tile':index,'product_version':str(hdus[0].header['VERSION']),
                'mjd_start':begin,'mjd_end':end,'date_start':str(hdus[0].header['DATE-BEG']),
                'date_end':str(hdus[0].header['DATE-END']),'time_scale':'UTC','celestial_frame':'ICRS','unit':'MJy/sr'}
            center=list(map(float,wcs.pixel_to_world_values(x,y))) if inside else None
        result={'source':source,'native_pixel_xy':[x,y],'native_pixel_center_deg':center,'outside_native_tile':not inside,
            'brightness':arrays['IMAGE'],'hits':arrays['NHITS'],'flags':arrays['FLAGS'],'channel_table':table,
            'byte_ranges':stream.ranges,'transfer':{'bytes':stream.transferred_bytes,'requests':len(stream.ranges),'elapsed_seconds':time.monotonic()-started}}
    check_cancel();return result


def trace_svg(product):
    samples=[s for s in product['samples'] if s['brightness_mjysr'] is not None]
    low=min([s['brightness_mjysr'] for s in samples]+[0.]);high=max([s['brightness_mjysr'] for s in samples]+[1.]);span=high-low
    low-=.08*span;high+=.12*span
    x=lambda v:100+(v-.7)/4.4*620;y=lambda v:280-(v-low)/(high-low)*210
    elements=['<svg xmlns="http://www.w3.org/2000/svg" width="780" height="390" viewBox="0 0 780 390" role="img" aria-labelledby="title desc">',
        '<title id="title">Vantage mosaic pixel brightness trace</title>',
        '<desc id="desc">Visualization context across mosaic channels; combined dates, no source photometry or per-sample errors. Missing and blank channels are not zeros.</desc>',
        '<rect width="100%" height="100%" fill="#09151a"/><g fill="#e3efeb" font-family="sans-serif" font-size="13">',
        '<text x="30" y="28" font-size="20">Vantage · mosaic pixel brightness</text>',
        '<text x="30" y="50">Visualization only · combined dates · no per-sample uncertainty</text>',
        '<path d="M100 70 V280 H720" stroke="#afc6cf" fill="none"/>']
    for tick in [1,2,3,4,5]:elements.append(f'<text x="{x(tick):.2f}" y="305" text-anchor="middle">{tick}</text>')
    for value in np.linspace(low,high,5):elements.append(f'<text x="90" y="{y(value)+4:.2f}" text-anchor="end">{value:.3g}</text>')
    for sample in samples:
        color='#ffc186' if sample['flag_review'] else '#9ddfd2'
        elements.append(f'<circle cx="{x(sample["wavelength_um"]):.2f}" cy="{y(sample["brightness_mjysr"]):.2f}" r="3" fill="{color}"><title>Layer {sample["index"]}; {sample["brightness_mjysr"]:.6g} MJy/sr; hits {sample["hits"]}</title></circle>')
    if not samples:elements.append('<text x="150" y="170">No measured mosaic brightness at this pixel.</text>')
    elements+=['<text x="400" y="335" text-anchor="middle">Mosaic wavelength (µm)</text>',
        '<text transform="translate(22 175) rotate(-90)" text-anchor="middle">Surface brightness (MJy/sr)</text>',
        f'<text x="30" y="363">{len(samples)} available / 102 layers · NASA/SPHEREx; Caltech/IPAC/IRSA</text>','</g></svg>']
    return ''.join(elements)


def build_visual_trace(plane,pixel,destination,sampler=sample_visual_point,check_cancel=lambda:None,progress=lambda stage:None):
    shape=plane.get('shape',[])
    if len(shape)!=2 or not all(isinstance(n,int) and 16<=n<=256 for n in shape) or len(pixel)!=2 or not all(isinstance(n,int) and not isinstance(n,bool) for n in pixel):raise ValueError('Choose an integer display pixel in a supported spectral plane')
    x,y=pixel
    if not 0<=x<shape[1] or not 0<=y<shape[0]:raise ValueError('Selected pixel is outside the saved spectral plane')
    check_cancel();ra,dec=map(float,WCS(plane['grid']).pixel_to_world_values(x,y))
    native=sampler(ra,dec,check_cancel=check_cancel,progress=progress);check_cancel()
    samples=[]
    for channel,brightness,hits,flags in zip(metadata()['channels'],native['brightness'],native['hits'],native['flags']):
        state='blank' if channel['blank'] else 'missing' if brightness is None or hits is None or hits<=0 else 'available'
        samples.append({**channel,'brightness_mjysr':brightness if state=='available' else None,'hits':hits,'flags':flags,
            'status':state,'flag_review':bool(flags is not None and (flags&BAD_MASK or flags&~KNOWN_MASK)),
            'reason':'Blank visualization channel' if state=='blank' else 'No finite mosaic sample with positive contributing hits' if state=='missing' else None})
    data={'policy':POLICY,'source':native['source'],'native_pixel_xy':native['native_pixel_xy'],'outside_native_tile':native['outside_native_tile'],
        'native_pixel_center_deg':native['native_pixel_center_deg'],'channel_table':native['channel_table'],'samples':samples}
    data_id=hashlib.sha256(json.dumps(data,sort_keys=True,allow_nan=False).encode()).hexdigest()
    request={'plane_id':plane['id'],'pixel_xy':pixel,'position_deg':[ra,dec]}
    canonical={'trace_data_id':data_id,'request':request}
    identity=hashlib.sha256(json.dumps(canonical,sort_keys=True,allow_nan=False).encode()).hexdigest()
    product={'schema_version':'1.0.0','id':identity,'type':'visual_spectral_trace',**data,**canonical,
        'display_grid':{k:plane[k] for k in ['center_deg','fov_arcmin','shape','grid']},
        'data_status':'native_mosaic_pixel_samples','numerical_products_authorized':False,'uncertainties_available':False,
        'units':'MJy/sr','byte_ranges':native['byte_ranges'],'transfer':native['transfer'],
        'available_channels':sum(s['status']=='available' for s in samples),
        'interpretation':'A nearest-native-pixel surface-brightness trace from the survey-combined visualization cube. It is not source photometry, an instantaneous spectrum or a measurement with supplied per-channel errors.',
        'limitations':metadata()['limitations']+['Contributing hit counts are not inverse variances. No error bars or statistical upper limits are inferred.',
            'Flags are propagated context indicators. A source flag alone is not a defect; other known or unknown bits are marked for review.',
            'The mosaic acquisition interval describes contributing survey data, not a separate date for each plotted channel.'],
        'credits':metadata()['credits']}
    folder=Path(destination)/identity
    if (folder/'manifest.json').is_file():return json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    folder.mkdir(parents=True,exist_ok=True)
    table=Table(meta={k:product[k] for k in ['id','trace_data_id','request','source','interpretation','limitations','credits']})
    for name in ['index','detector','channel','status','reason']:table[name]=[s[name] if s[name] is not None else '' for s in samples]
    for name,unit in [('wavelength_um',u.um),('bandwidth_um',u.um),('brightness_mjysr',u.MJy/u.sr),('hits',None),('flags',None)]:
        values=[s[name] for s in samples];dtype=np.uint32 if name=='flags' else np.int64 if name=='hits' else float
        table[name]=MaskedColumn([v if v is not None else 0 for v in values],mask=[v is None for v in values],dtype=dtype,unit=unit)
    for name,format in [('trace.ecsv','ascii.ecsv'),('trace.csv','ascii.csv')]:
        output=io.StringIO();table.write(output,format=format);atomic_text(folder/name,output.getvalue())
    atomic_text(folder/'trace.svg',trace_svg(product))
    product['exports']={name:{'url':f'/v1/products/{identity}/{name}','sha256':digest(folder/name)} for name in ['trace.ecsv','trace.csv','trace.svg']}
    check_cancel();write_json(folder/'manifest.json',product);return product
