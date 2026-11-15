# MoonMatrix
**NASA Space Apps Challenge 2026 – Tabuk team · Challenge: Lunar Landing Site Navigator**

## Summary
**MoonMatrix** is an interactive web tool to compare lunar landing sites and time windows. Click any point on the Moon to see the nearest past mission, terrain elevation and slope (NASA LRO/LOLA), estimated power needs, illumination, shadow, temperature, Earth-communication status and dust level. A date/time selector moves the Sun across the surface.

## Run
    pip install -r requirements.txt
    python backend/app.py      # open http://localhost:5000
Without the server, open `index.html` directly (or host it on GitHub Pages): the interface falls back to local calculation.

## API
- `GET /api/missions`
- `GET /api/site?lat=-69.37&lon=32.32&sun=0`  (`sun` = sub-solar longitude, degrees)

## NASA data used
- **LRO LOLA LDEM_4** (elevation; slope derived) – https://imbrium.mit.edu/DATA/LOLA_GDR/CYLINDRICAL/IMG/ · rebuild: `python tools/build_terrain.py LDEM_4.IMG backend/terrain.json`
- References: LRO QuickMap, NASA Moon Trek, JPL Horizons, CSA Moon Exploration.
- Illumination, temperature, dust, communication and power values are approximate models, not NASA measurements. Slope is regional (1° grid, ~15 km baseline).

## Use of AI
Built with help from Claude (Anthropic) for code and text.

## Team
[Add team member names]

## Machine learning
`tools/train_suitability.py` trains a logistic regression on NASA LOLA elevation, slope, latitude and Earth line-of-sight. The 11 past soft-landing sites are the positives; the rest of the Moon is background. The output is a **0–100 percentile of similarity to past landing sites** (shown in the data panel and as a map layer).
- Leave-one-out validation (hold one site out, rank it): mean percentile **76** (random = 50); it works for near-side equatorial sites but **fails for far-side and polar sites** (Chang'e 4: 5th, Chandrayaan-3: 27th percentile). See `data/ml_report.json`.
- It measures similarity to where we have landed before – **not** safety or mission success. Only 11 examples, with selection bias.
