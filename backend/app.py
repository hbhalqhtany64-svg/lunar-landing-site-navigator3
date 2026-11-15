"""Lunar Landing Site Navigator - Flask API + SQLite"""
import math, os, sqlite3
from flask import Flask, jsonify, request, send_from_directory

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "missions.db")
ROOT = os.path.abspath(os.path.join(BASE, ".."))
app = Flask(__name__, static_folder=None)
R, rad = 1737.4, math.pi / 180

MISSIONS = [
 ("Apollo 11",0.67,23.47,"July 20, 1969","First crewed landing; samples from Mare Tranquillitatis"),
 ("Apollo 12",-3.01,-23.42,"Nov 19, 1969","Precision landing near Surveyor 3; science experiments"),
 ("Apollo 14",-3.65,-17.47,"Feb 5, 1971","Fra Mauro exploration and sample collection"),
 ("Apollo 15",26.13,3.63,"July 30, 1971","Apennine Mountains exploration with lunar rover"),
 ("Apollo 16",-8.97,15.5,"Apr 21, 1972","Study of the ancient lunar highlands"),
 ("Apollo 17",20.19,30.77,"Dec 11, 1972","Final Apollo mission; Taurus-Littrow valley"),
 ("Luna 9",7.08,-64.37,"Feb 3, 1966","First soft landing; images from the surface"),
 ("Chang'e 3",44.12,-19.51,"Dec 14, 2013","Yutu rover exploring Mare Imbrium"),
 ("Chang'e 4",-45.46,177.6,"Jan 3, 2019","First landing on the far side"),
 ("Chandrayaan-3",-69.37,32.32,"Aug 23, 2023","Near-south-pole landing; soil and thermal studies"),
 ("SLIM",-13.3,25.25,"Jan 19, 2024","Pin-point landing demonstration"),
 ("Shackleton (Artemis candidate)",-89.9,0,"Planned","Searching for water ice in permanently shadowed regions"),
]
MARIA = [("Imbrium",35,-15,18),("Serenitatis",28,18,10),("Tranquillitatis",8,31,10),
         ("Fecunditatis",-3,52,10),("Procellarum",18,-57,20),("Nubium",-21,-15,10),("Crisium",17,59,8)]

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init():
    c = db()
    c.execute("CREATE TABLE IF NOT EXISTS missions(id INTEGER PRIMARY KEY,name TEXT,lat REAL,lon REAL,date TEXT,purpose TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS maria(id INTEGER PRIMARY KEY,name TEXT,lat REAL,lon REAL,radius_deg REAL)")
    if c.execute("SELECT COUNT(*) FROM missions").fetchone()[0] == 0:
        c.executemany("INSERT INTO missions(name,lat,lon,date,purpose) VALUES(?,?,?,?,?)", MISSIONS)
        c.executemany("INSERT INTO maria(name,lat,lon,radius_deg) VALUES(?,?,?,?)", MARIA)
    c.commit(); c.close()

import base64, json, struct
_T = json.load(open(os.path.join(BASE, "terrain.json")))
_E = struct.unpack("<64800h", base64.b64decode(_T["elev_b64"]))
_S = base64.b64decode(_T["slope_b64"])
_U = base64.b64decode(_T["suit_b64"])

def lola(la, lo):
    """Elevation (m) and regional slope (deg) from NASA LRO/LOLA LDEM_4, 1-degree grid."""
    r, c = min(179, int(90 - la)), int(lo % 360)
    return _E[r*360+c], _S[r*360+c]/10, _U[r*360+c]

def slope_class(s):
    return "Flat – suitable for landing" if s < 3 else "Moderate – use caution" if s < 6 else "Steep – hazardous"

def dist(a, b, c, d):
    x = math.sin((c-a)*rad/2)**2 + math.cos(a*rad)*math.cos(c*rad)*math.sin((d-b)*rad/2)**2
    return 2*R*math.asin(math.sqrt(x))

def model(la, lo, sun):
    c = db(); missions = c.execute("SELECT * FROM missions").fetchall(); maria = c.execute("SELECT * FROM maria").fetchall(); c.close()
    sinE = math.cos(la*rad)*math.cos((lo-sun)*rad)
    el = math.degrees(math.asin(max(-1, min(1, sinE))))
    lit = max(0, sinE)*100
    if el <= 0: shadow = "Night – no shadow (full darkness)"
    else:
        k = 1/math.tan(math.radians(el))
        shadow = ("Very long shadows" if el < 8 else "Long shadows" if el < 30 else "Short shadows") + f" (~{k:.1f}× object height)"
    tk = min(394, 390*sinE**.25) if el > 0 else max(40, 100-.6*abs(la))
    if abs(la) > 85: tk = min(tk, 200 if el > 0 else 40)
    in_maria = any(dist(la, lo, m["lat"], m["lon"]) < m["radius_deg"]*30 for m in maria)
    terrain = ("Deep craters and permanent shadow – very hazardous" if abs(la) > 80 else
               "Basaltic plain (lunar mare) – flat and relatively safe" if in_maria else "Highlands with dense craters – rugged")
    cz = math.cos(la*rad)*math.cos(lo*rad)
    comm = (("Excellent","Direct line of sight to Earth") if cz > .35 else ("Limited","Near the lunar limb – weak signal") if cz > 0
            else ("None","Far side – relay satellite required (Relay)"))
    v = 35 + (35 if abs(el) < 10 else 0) + (0 if in_maria else 12) + (10 if abs(la) > 80 else 0)
    dust = "High" if v >= 65 else "Medium" if v >= 45 else "Low"
    need = 1.5 + max(0, 293-tk)*.04 + (2 if lit < 5 else 0)
    el_m, sl, su = lola(la, lo)
    best = min(missions, key=lambda m: dist(la, lo, m["lat"], m["lon"]))
    d = dist(la, lo, best["lat"], best["lon"])
    mission = dict(name=best["name"], date=best["date"], purpose=best["purpose"], distance_km=round(d)) if d < 800 else None
    return dict(lat=la, lon=lo, mission=mission, terrain=terrain, elevation_m=el_m, slope_deg=round(sl,1), slope_class=slope_class(sl), similarity_ml=su,
                power_kwh=round(need,1), illumination=round(lit,1), sun_elevation=round(el,1), shadow=shadow,
                temp_c=round(tk-273.15,1), temp_k=round(tk), comm_level=comm[0], comm_note=comm[1],
                dust_level=dust, dust_score=v)

@app.route("/")
def index(): return send_from_directory(ROOT, "index.html")

@app.route("/assets/<path:name>")
def assets(name): return send_from_directory(os.path.join(ROOT, "assets"), name)

@app.route("/api/missions")
def missions():
    c = db(); rows = [dict(r) for r in c.execute("SELECT * FROM missions")]; c.close(); return jsonify(rows)

@app.route("/api/site")
def site():
    try:
        la = float(request.args["lat"]); lo = float(request.args["lon"]); sun = float(request.args.get("sun", 0))
    except (KeyError, ValueError):
        return jsonify(error="lat and lon are required numbers"), 400
    if not (-90 <= la <= 90): return jsonify(error="lat must be in [-90, 90]"), 400
    return jsonify(model(la, lo, sun))

init()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
