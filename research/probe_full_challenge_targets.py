"""Public archive research for the five official challenge targets."""
from probe_metadata import probe, ROOT
from concurrent.futures import ThreadPoolExecutor
from astropy.coordinates import SkyCoord
import astropy.units as u
import json

def degrees(ra, dec):
    c = SkyCoord(ra, dec, unit=(u.hourangle, u.deg))
    return [c.ra.deg, c.dec.deg]

# Fixed field centers: older catalog coordinates do not denote exposure-date positions.
coords = {'barnard': [269.44624, 4.76864],
          'eps_indi_b': degrees('22 04 10.5951812451','-56 46 58.239102418'),
          'wise0855': degrees('08 55 10.831','-07 14 42.53'),
          'rw_aur': [76.95654,30.40144],
          'r_dra': degrees('16 32 40.2265999080','+66 45 17.925901992')}

if __name__ == '__main__':
    (ROOT/'full_challenge_coordinates.json').write_text(json.dumps(coords, indent=2))
    tasks = [(f'full_sia_{k}_{release}', 'https://irsa.ipac.caltech.edu/SIA',
              {'COLLECTION': 'spherex_'+release, 'POS': f'CIRCLE {xy[0]} {xy[1]} 0.06', 'MAXREC': 3000})
             for k, xy in coords.items() for release in ['qr2','qr3']]
    tasks.insert(0, ('full_sia_barnard_dr1', 'https://irsa.ipac.caltech.edu/SIA',
                    {'COLLECTION':'spherex_dr1','POS':f'CIRCLE {coords["barnard"][0]} {coords["barnard"][1]} 0.06','MAXREC':5}))
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda a: probe(*a), tasks))
