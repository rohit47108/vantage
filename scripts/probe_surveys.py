"""Live service verification before committing a catalog adapter."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import requests

TASKS={
    'gaia':('https://irsa.ipac.caltech.edu/TAP/sync',{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':"SELECT TOP 5 source_id,ra,dec,ref_epoch,pmra,pmdec,parallax,radial_velocity,phot_g_mean_mag FROM gaia_dr3_source WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',210.80227,54.34895,0.05))"}),
    'wise':('https://irsa.ipac.caltech.edu/TAP/sync',{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':"SELECT TOP 5 designation,ra,dec,w1mpro,w2mpro,w1mjdmean,w2mjdmean,cc_flags,ph_qual,ext_flg FROM allwise_p3as_psd WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',210.80227,54.34895,0.05))"}),
    'name':('https://cds.unistra.fr/cgi-bin/nph-sesame/-oxp/SNV?M101',{}),
    'mirror':('https://vizier.idia.ac.za/viz-bin/nph-sesame/-oxp/SNV?M101',{}),
    'wise_gator':('https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query',{'catalog':'allwise_p3as_psd','spatial':'cone','radius':3,'radunits':'arcmin','objstr':'210.80227 54.34895','outfmt':3,'selcols':'designation,ra,dec,w1mpro,w2mpro,w1mjdmean,w2mjdmean,cc_flags,ph_qual,ext_flg'}),
    'gaia_gator':('https://irsa.ipac.caltech.edu/cgi-bin/Gator/nph-query',{'catalog':'gaia_dr3_source','spatial':'cone','radius':3,'radunits':'arcmin','objstr':'210.80227 54.34895','outfmt':3,'selcols':'source_id,ra,dec,ref_epoch,pmra,pmdec,parallax,radial_velocity,phot_g_mean_mag'}),
    'gaia_esa':('https://gea.esac.esa.int/tap-server/tap/sync',{'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'votable','QUERY':"SELECT TOP 5 source_id,ra,dec,ref_epoch,pmra,pmdec,parallax,radial_velocity,phot_g_mean_mag FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',210.80227,54.34895,0.05))"}),
}

def main():
    root=Path('research/updates/2026-11-15');root.mkdir(parents=True,exist_ok=True)
    def fetch(item):
        name,(url,params)=item
        try:
            r=requests.get(url,params=params,timeout=65)
            (root/(name+'.xml')).write_bytes(r.content)
            return {'name':name,'url':r.url,'status':r.status_code,'bytes':len(r.content),'sample':r.text[:350]}
        except requests.RequestException as exc:return {'name':name,'error':type(exc).__name__}
    results=list(ThreadPoolExecutor(7).map(fetch,TASKS.items()))
    (root/'service-probe.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
