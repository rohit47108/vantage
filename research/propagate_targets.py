from probe_metadata import probe
probe('simbad_luhman','https://simbad.cds.unistra.fr/simbad/sim-tap/sync',{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','QUERY':"SELECT b.main_id,b.ra,b.dec,b.pmra,b.pmdec,b.plx_value,b.rvz_radvel FROM basic b JOIN ident i ON b.oid=i.oidref WHERE i.id='WISE J104915.57-531906.1'"})
from astropy.coordinates import SkyCoord,Distance
from astropy.time import Time
import astropy.units as u,json
from pathlib import Path
c=SkyCoord(ra=269.4520769586187*u.deg,dec=4.693364966576667*u.deg,pm_ra_cosdec=-801.551*u.mas/u.yr,pm_dec=10362.394*u.mas/u.yr,distance=Distance(parallax=546.9759*u.mas),radial_velocity=-110.11*u.km/u.s,obstime=Time('J2000'))
out=[]
for d in ['2025-08-15','2026-05-05']:
 p=c.apply_space_motion(Time(d));out.append({'date_utc':d,'ra_deg':p.ra.deg,'dec_deg':p.dec.deg,'caveat':'Space-motion propagation from SIMBAD epoch 2000; apparent observer parallax not applied.'})
Path('research/evidence/barnard_propagation.json').write_text(json.dumps(out,indent=2));print(out)
