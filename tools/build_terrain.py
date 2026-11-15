"""Builds a compact 1-degree terrain grid from NASA LRO/LOLA LDEM_4.IMG.
Usage: python tools/build_terrain.py path/to/LDEM_4.IMG backend/terrain.json
Source: https://imbrium.mit.edu/DATA/LOLA_GDR/CYLINDRICAL/IMG/  (HEIGHT = DN*0.5 m, 4 px/deg, 16-bit LSB)
"""
import numpy as np, base64, json, math, sys
src, out = sys.argv[1], sys.argv[2]
h = np.fromfile(src, dtype='<i2').reshape(720, 1440).astype(np.float32) * 0.5
R, d = 1737400.0, math.radians(0.25)
lat = 90 - (np.arange(720) + 0.5) * 0.25
slope = np.zeros_like(h)
for i in range(720):
    c = max(math.cos(math.radians(lat[i])), 1e-3)
    k = min(720, max(1, int(round(1 / c))))          # keep a ~15 km baseline near the poles
    gx = (np.roll(h[i], -k) - np.roll(h[i], k)) / (2 * k * d * R * c)
    i0, i1 = max(i - 1, 0), min(i + 1, 719)
    gy = (h[i0] - h[i1]) / ((i1 - i0) * d * R)
    slope[i] = np.degrees(np.arctan(np.hypot(gx, gy)))
e1 = np.rint(h.reshape(180, 4, 360, 4).mean(axis=(1, 3))).astype('<i2')
s1 = np.clip(np.rint(slope.reshape(180, 4, 360, 4).mean(axis=(1, 3)) * 10), 0, 255).astype(np.uint8)
json.dump({"grid": "1deg, row0 = lat 90..89, col0 = lon 0..1 (east, 0-360)",
           "elev_b64": base64.b64encode(e1.tobytes()).decode(),
           "slope_b64": base64.b64encode(s1.tobytes()).decode()}, open(out, 'w'))
for n, la, lo in [("Apollo 11", .67, 23.47), ("Apollo 17", 20.19, 30.77), ("Chandrayaan-3", -69.37, 32.32),
                  ("Chang'e 4", -45.46, 177.6), ("Tycho-ish -43,-11", -43, -11), ("Shackleton", -89.9, 0)]:
    r, c = min(179, int(90 - la)), int(lo % 360)
    print(f"{n:20s} elev={e1[r,c]:7d} m  slope={s1[r,c]/10:5.1f} deg")
print("elev range", e1.min(), e1.max(), "| slope mean", round(float(s1.mean())/10, 2))
