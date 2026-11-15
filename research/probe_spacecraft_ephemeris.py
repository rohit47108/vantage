from probe_metadata import probe
base={'format':'json','EPHEM_TYPE':"'OBSERVER'",'CENTER':"'500@-163182'",'TLIST_TYPE':"'MJD'",'QUANTITIES':"'1,3,20'",'ANG_FORMAT':"'DEG'",'CSV_FORMAT':"'YES'",'TIME_DIGITS':"'FRACSEC'",'REF_SYSTEM':"'ICRF'",'EXTRA_PREC':"'YES'"}
h={'User-Agent':'VantageResearch/0.1 (OpenAI Codex research client; https://help.openai.com/)'}
probe('horizons_ceres_spherex','https://ssd.jpl.nasa.gov/api/horizons.api',base|{'COMMAND':"'1;'",'TLIST':"'60859.093852034,60859.2937076015'"},headers=h)
probe('horizons_comet_spherex','https://ssd.jpl.nasa.gov/api/horizons.api',base|{'COMMAND':"'3I'",'TLIST':"'60894.247538099,60894.5881452635'"},headers=h)
