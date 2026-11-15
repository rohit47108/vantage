"""Immutable export products for native source coverage and summaries."""
import io
import json
import hashlib
from pathlib import Path
from xml.sax.saxutils import escape
from astropy.table import Table,MaskedColumn
import astropy.units as u
from backend.science import write_json,digest
from backend.spectra import atomic_text
from backend.source_summary import summarize_samples


def summary_plot(product):
    bins=product['bins'];low=min([r['flux_ujy']-3*r['statistical_sigma_ujy'] for r in bins]+[0.])
    high=max([r['flux_ujy']+3*r['statistical_sigma_ujy'] for r in bins]+[1.])*1.1
    x=lambda value:100+(value-.7)/4.4*620
    y=lambda value:285-(value-low)/(high-low)*210
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="780" height="390" viewBox="0 0 780 390" role="img" aria-labelledby="title description">',
        '<title id="title">Vantage source summary</title>',
        '<desc id="description">Time and response mixed statistical means. Vertical bars show one statistical error; horizontal bars span input wavelength centers, not a bandpass. Individual measurements remain authoritative.</desc>',
        '<rect width="100%" height="100%" fill="#09151a"/><g fill="#e3efeb" font-family="sans-serif" font-size="13">',
        f'<text x="30" y="28" font-size="19">{escape(product["source"].get("name","Source"))} · time-combined summary</text>',
        '<text x="30" y="51">Response-mixed means · statistical errors only · not an instantaneous spectrum</text>',
        '<path d="M100 75 V285 H720" stroke="#b7cbc4" fill="none"/>']
    for value in [1,2,3,4,5]:parts.append(f'<text x="{x(value):.2f}" y="308" text-anchor="middle">{value}</text>')
    for ratio in [0,.25,.5,.75,1]:
        value=low+ratio*(high-low);parts.append(f'<text x="90" y="{y(value)+4:.2f}" text-anchor="end">{value:.0f}</text>')
    for row in bins:
        px,py=x(row['weighted_wavelength_um']),y(row['flux_ujy']);sigma=row['statistical_sigma_ujy'];a,b=row['wavelength_range_um']
        color='#ffc186' if row['scatter_warning'] else '#9ddfd2'
        parts.append(f'<g stroke="{color}" fill="{color}"><path d="M{px:.2f} {y(row["flux_ujy"]-sigma):.2f} V{y(row["flux_ujy"]+sigma):.2f} M{x(a):.2f} {py:.2f} H{x(b):.2f}"/><circle cx="{px:.2f}" cy="{py:.2f}" r="4"><title>D{row["detector"]} channel {row["channel"]}; {row["count"]} inputs</title></circle></g>')
    if not bins:parts.append('<text x="150" y="175">No passing measurements in this time window.</text>')
    parts+=['<text x="405" y="335" text-anchor="middle">Mean sample wavelength (µm); horizontal span: input centers</text>',
        '<text transform="translate(22 185) rotate(-90)" text-anchor="middle">Mean flux density (µJy)</text>',
        f'<text x="30" y="363">{len(bins)} summaries · {product["selected_sample_count"]} selected native inputs · NASA/SPHEREx; Caltech/IPAC/IRSA</text>',
        '</g></svg>']
    return ''.join(parts)


def summary_tables(product):
    metadata={k:product[k] for k in ['id','policy','parent_product_id','options','time_bounds_mjd_utc','interpretation','uncertainty_method','scatter_interpretation','credits']}
    tables={}
    specs={
        'coverage':(product['coverage'],{'index':int,'detector':int,'channel':int,'accepted':int,'diagnostic_only':int,'rejected':int,'status':str,'visualization_blank':bool,'fiducial_wavelength_um':float}),
        'bins':(product['bins'],{'bin_id':str,'detector':int,'channel':int,'count':int,'weighted_wavelength_um':float,'flux_ujy':float,'statistical_sigma_ujy':float,'equal_mean_chi2':float,'equal_mean_dof':int,'equal_mean_p_value':float,'scatter_warning':bool})}
    for name,(rows,columns) in specs.items():
        table=Table(meta=metadata)
        for column,dtype in columns.items():
            values=[r[column] for r in rows]
            if dtype==float:
                unit=u.um if column.endswith('_um') else u.uJy if column.endswith('_ujy') else None
                table[column]=MaskedColumn([v if v is not None else 0. for v in values],mask=[v is None for v in values],unit=unit,dtype=float)
            else:table[column]=[dtype(v) for v in values] if values else MaskedColumn([],dtype=dtype)
        if name=='bins':
            for column in ['input_sample_ids','weights','input_utc_mids','input_wavelengths_um','input_bandwidths_um','mjd_range','wavelength_range_um']:
                table[column+'_json']=[json.dumps(r[column],separators=(',',':')) for r in rows] if rows else MaskedColumn([],dtype=str)
        tables[name]=table
    table=Table(meta=metadata);statistics=product['sample_statistics']
    table['sample_id']=[s['sample_id'] for s in statistics] if statistics else MaskedColumn([],dtype=str)
    table['reason']=[s['reason'] or '' for s in statistics] if statistics else MaskedColumn([],dtype=str)
    for column,path in [('snr',('snr',)),('upper_95_ujy',('bound','upper_ujy')),('conditional_95_sensitivity_ujy',('sensitivity','flux_ujy'))]:
        values=[]
        for sample in statistics:
            value=sample
            for key in path:value=value.get(key) if isinstance(value,dict) else None
            values.append(value)
        table[column]=MaskedColumn([v if v is not None else 0 for v in values],mask=[v is None for v in values],dtype=float,unit=u.uJy if column.endswith('_ujy') else None)
    table.meta['bound_model']='95% posterior mass, Gaussian fixed-position likelihood, uniform prior on nonnegative true flux. Only accepted, unrefined samples with signed S/N < 3. Not total error or detection completeness.'
    table.meta['sensitivity_model']='Conditional one-position Gaussian threshold S/N >= 5 and 95% detection probability; (5 + normal_quantile(.95))*sigma. Real-sky quality gates/searching/variance changes excluded.'
    tables['limits']=table
    return tables


def build_source_summary(parent,options,destination,check_cancel=lambda:None):
    check_cancel();summary=summarize_samples(parent,options)
    canonical={**summary,'source':parent['source'],'credits':parent['credits']}
    identity=hashlib.sha256(json.dumps(canonical,sort_keys=True,allow_nan=False).encode()).hexdigest()
    product={'schema_version':'1.0.0','id':identity,'type':'source_summary',**canonical,
        'parent_product_url':'/v1/products/'+parent['id'],'units':'uJy'}
    folder=Path(destination)/identity;folder.mkdir(parents=True,exist_ok=True)
    names=[]
    for stem,table in summary_tables(product).items():
        for extension,format in [('ecsv','ascii.ecsv'),('csv','ascii.csv')]:
            buffer=io.StringIO();table.write(buffer,format=format);name=stem+'.'+extension
            atomic_text(folder/name,buffer.getvalue());names.append(name)
    atomic_text(folder/'summary.svg',summary_plot(product));names.append('summary.svg')
    product['exports']={name:{'url':f'/v1/products/{identity}/{name}','sha256':digest(folder/name)} for name in names}
    check_cancel();write_json(folder/'manifest.json',product)
    return product
