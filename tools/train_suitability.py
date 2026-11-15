"""Supervised ML: similarity of every 1-degree lunar cell to the sites of past successful soft landings.
Features come from NASA LRO/LOLA (elevation, slope) + geometry (latitude, Earth line-of-sight).
Positives = 11 landing sites; everything else = unlabeled background (positive-vs-background logistic regression).
Output = percentile (0-100) of the model score. Usage: python tools/train_suitability.py backend/terrain.json
NOTE: this measures similarity to where people HAVE landed, not a guarantee of safety."""
import base64, json, math, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
path = sys.argv[1]; t = json.load(open(path))
E = np.frombuffer(base64.b64decode(t["elev_b64"]), dtype='<i2').reshape(180, 360).astype(float)
S = np.frombuffer(base64.b64decode(t["slope_b64"]), dtype=np.uint8).reshape(180, 360) / 10.0
lat = 89.5 - np.arange(180)[:, None] * np.ones((1, 360)); lon = (np.arange(360)[None, :] + .5) * np.ones((180, 1))
cz = np.cos(np.radians(lat)) * np.cos(np.radians(lon))
X = np.stack([E.ravel() / 1000, S.ravel(), np.abs(lat).ravel() / 90, cz.ravel()], 1)
SITES = [(0.67,23.47),(-3.01,-23.42),(-3.65,-17.47),(26.13,3.63),(-8.97,15.5),(20.19,30.77),(7.08,-64.37),(44.12,-19.51),(-45.46,177.6),(-69.37,32.32),(-13.3,25.25)]
idx = [min(179, int(90 - la)) * 360 + int(lo % 360) for la, lo in SITES]
def fit(pos):
    y = np.zeros(len(X)); y[pos] = 1
    sc = StandardScaler().fit(X); m = LogisticRegression(class_weight='balanced', C=1.0, max_iter=1000).fit(sc.transform(X), y)
    return m.decision_function(sc.transform(X))
def pct(score, i): return 100.0 * (score < score[i]).mean()
loo = [pct(fit([j for j in idx if j != i]), i) for i in idx]       # leave-one-out: hold a landing site out, rank it
score = fit(idx); ranks = score.argsort().argsort() / (len(score) - 1) * 100
t["suit_b64"] = base64.b64encode(np.rint(ranks).astype(np.uint8).tobytes()).decode()
json.dump(t, open(path, 'w'))
rep = {"n_sites": len(idx), "leave_one_out_percentile_mean": round(float(np.mean(loo)), 1),
       "leave_one_out_percentile_median": round(float(np.median(loo)), 1), "random_baseline": 50.0,
       "per_site": [round(float(x), 1) for x in loo]}
json.dump(rep, open('data/ml_report.json', 'w'), indent=1); print(rep)
