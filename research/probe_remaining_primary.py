from probe_metadata import probe
from inspect_fits import download,EV,FIX
from astropy.io import fits
import json
probe('horizons_spherex_lookup','https://ssd.jpl.nasa.gov/api/horizons.api',{'format':'json','COMMAND':"'SPHEREx'",'MAKE_EPHEM':"'NO'",'OBJ_DATA':"'YES'"})
# Standalone ePSF is an implementation calibration, so retain one concrete example.
u='https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/qr3/epsf/cal-epsf-v1-2026-191/2/epsf_D2_spx_cal-epsf-v1-2026-191.fits';p=download('epsf_d2',u)
with fits.open(p) as h:
 out=[{'name':x.name,'type':type(x).__name__,'shape':getattr(x,'shape',None),'rows':len(x.data) if isinstance(x,fits.BinTableHDU) else None,'header':dict(x.header)} for x in h];(EV/'epsf_d2_hdus.json').write_text(json.dumps(out,indent=2,default=str));print([(x['name'],x['shape'],x['rows']) for x in out])
