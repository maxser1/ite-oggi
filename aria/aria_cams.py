"""Qualità dell'aria per italytravelescape.com dai dati Copernicus CAMS (scelta di Max, 24/11/2026).

Scarica dall'Atmosphere Data Store (ADS) la previsione europea CAMS "cams-europe-air-quality-forecasts" (modello ensemble,
livello del suolo, corsa delle 00 UTC, prossime 48 ore) per l'Italia, estrae i valori per i capoluoghi e le città con almeno
30.000 abitanti e calcola l'indice europeo della qualità dell'aria (fasce dell'Agenzia europea dell'ambiente).
Scrive site/static/aria/oggi.json, che il build copia in /aria/oggi.json e che la pagina dello strumento legge.

Licenza: dati Copernicus, uso gratuito anche commerciale citando la fonte (licenza CAMS da accettare una volta sul sito ADS).
Credenziali: FUORI dal repository. Il file indicato da ADS_RC (di solito C:\\Users\\stran\\.adsapirc) contiene
    url: https://ads.atmosphere.copernicus.eu/api
    key: <chiave personale dell'account ECMWF>
Questo script non legge e non stampa la chiave: la passa a cdsapi indicando il file con la variabile CDSAPI_RC.

Uso: python -X utf8 aria_cams.py [AAAA-MM-GG]   (senza data: oggi)
Su GitHub (repository pubblico ite-oggi, cartella aria/): ARIA_PUNTI=aria/punti.json ARIA_OUT=aria/oggi.json, chiave dal segreto ADS_KEY.
"""
import datetime, json, math, os, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.environ.get("ARIA_OUT") or os.path.join(HERE, "..", "site", "static", "aria", "oggi.json")
PUNTI = os.environ.get("ARIA_PUNTI")   # file JSON [[nome, sigla, lat, lon], ...]: usato su GitHub, dove it_comuni.json non c'è
RC = os.environ.get("ADS_RC", os.path.join(os.path.expanduser("~"), ".adsapirc"))
AREA = [47.2, 6.5, 36.5, 18.6]   # nord, ovest, sud, est
VARS = {"particulate_matter_2.5um": "pm25", "particulate_matter_10um": "pm10", "nitrogen_dioxide": "no2", "ozone": "o3"}
# fasce dell'indice europeo (EEA, valori orari in µg/m³): limite superiore delle classi 1..5, oltre è 6
FASCE = {"pm25": [10, 20, 25, 50, 75], "pm10": [20, 40, 50, 100, 150], "no2": [40, 90, 120, 230, 340], "o3": [50, 100, 130, 240, 380]}


def classe(k, v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return None
    for i, s in enumerate(FASCE[k]):
        if v <= s: return i + 1
    return 6


def punti():
    if PUNTI:
        return [{"n": n, "sig": s, "lat": la, "lon": lo} for n, s, la, lo in json.load(open(PUNTI, encoding="utf-8"))]
    com = json.load(open(os.path.join(DATA, "it_comuni.json"), encoding="utf-8"))
    # capoluoghi di provincia: il comune con il nome della provincia, altrimenti il più popoloso (come in build.py)
    prov = {}
    for c in com: prov.setdefault(c["sig"], []).append(c)
    caps = set()
    for sig, cs in prov.items():
        nome = cs[0]["prov"].split("/")[0].split(" e ")[0]
        caps.add(next((c["ist"] for c in cs if c["n"] == nome), max(cs, key=lambda c: c.get("pop") or 0)["ist"]))
    sel = [c for c in com if (c.get("pop") or 0) >= 30000 or c["ist"] in caps]
    return sorted(sel, key=lambda c: -(c.get("pop") or 0))


def scarica(giorno, dest):
    import cdsapi
    if not os.path.exists(RC): sys.exit(f"Manca il file delle credenziali ADS: {RC} (vedi istruzioni in testa al file)")
    os.environ["CDSAPI_RC"] = RC
    c = cdsapi.Client(quiet=True)
    c.retrieve("cams-europe-air-quality-forecasts", {
        "variable": list(VARS), "model": ["ensemble"], "level": ["0"], "date": [f"{giorno}/{giorno}"], "type": ["forecast"],
        "time": ["00:00"], "leadtime_hour": [str(h) for h in range(0, 48)], "area": AREA, "data_format": "netcdf_zip"}, dest)


def leggi(path):
    import netCDF4, numpy as np
    files = []
    if zipfile.is_zipfile(path):
        d = tempfile.mkdtemp(); zipfile.ZipFile(path).extractall(d); files = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".nc")]
    else: files = [path]
    out = {}
    for f in files:
        ds = netCDF4.Dataset(f)
        lat = ds.variables.get("latitude") or ds.variables.get("lat"); lon = ds.variables.get("longitude") or ds.variables.get("lon")
        for name, v in ds.variables.items():
            k = {"pm2p5_conc": "pm25", "pm10_conc": "pm10", "no2_conc": "no2", "o3_conc": "o3"}.get(name) or VARS.get(name)
            if k: out[k] = (np.array(lat[:]), np.array(lon[:]), np.squeeze(np.array(v[:])))
    return out


def main():
    giorno = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    tmp = os.path.join(tempfile.gettempdir(), f"cams_{giorno}.zip")
    if not os.path.exists(tmp): scarica(giorno, tmp)
    V = leggi(tmp)
    if set(V) != set(FASCE): sys.exit(f"Variabili trovate: {sorted(V)}")
    pts = []
    for c in punti():
        serie = []
        for k in ("pm25", "pm10", "no2", "o3"):
            la, lo, arr = V[k]
            i = int(abs(la - c["lat"]).argmin()); j = int(abs(((lo + 180) % 360 - 180) - c["lon"]).argmin())
            serie.append([round(float(x), 1) for x in arr[:, i, j]])
        ore = list(zip(*serie))
        aqi = [max(filter(None, (classe(k, v) for k, v in zip(("pm25", "pm10", "no2", "o3"), h))), default=None) for h in ore]
        pts.append([c["n"], c["sig"], round(c["lat"], 3), round(c["lon"], 3), aqi, [list(h) for h in ore[::3]]])   # indice ogni ora, inquinanti ogni 3 ore
    dati = {"inizio": f"{giorno}T00:00Z", "ore": 48, "aggiornato": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"),
            "fonte": "Copernicus Atmosphere Monitoring Service (CAMS), previsione europea della qualità dell'aria, modello ensemble",
            "ordine": ["pm25", "pm10", "no2", "o3"], "passo_inquinanti": 3, "punti": pts}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    s = json.dumps(dati, ensure_ascii=False, separators=(",", ":"))
    open(OUT + ".tmp", "w", encoding="utf-8").write(s); os.replace(OUT + ".tmp", OUT)
    print(f"ok {len(pts)} città, {len(s) // 1024} kB -> {OUT}")


if __name__ == "__main__":
    main()
