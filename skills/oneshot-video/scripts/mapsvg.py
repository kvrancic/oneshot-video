#!/usr/bin/env python3
"""Map paths for RouteMap: regions from GeoJSON or TopoJSON projected to a 1920x1080 frame.

  mapsvg.py us --points "Seattle=47.61,-122.33" "Boston=42.36,-71.06" --out src/map.json
  mapsvg.py world --points "Zagreb=45.81,15.98" "Tokyo=35.68,139.69" --out src/map.json
  mapsvg.py FILE.(geo|topo)json --name-key name [--object states] [--projection mercator] --points ... --out src/map.json

`us` uses US states (us-atlas, Albers equal-area, the lower 48), `world` Natural Earth countries
(equirectangular fit). Output: {"paths": {region: "M..."}, "points": {name: [x, y]}} for
<RouteMap paths={map.paths} from={{x, y, label}} to={...} />. Datasets are fetched once from jsDelivr
into ~/.oneshot-video/maps.
"""
import argparse, json, math, sys, urllib.request
from pathlib import Path

CACHE = Path.home() / ".oneshot-video" / "maps"
SOURCES = {
    "us": ("https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json", "states", "name", "albers"),
    "world": ("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json", "countries", "name", "equirect"),
}
DROP_US = {"Alaska", "Hawaii", "Puerto Rico", "Guam", "American Samoa", "Commonwealth of the Northern Mariana Islands", "United States Virgin Islands"}
W, H, PAD = 1920, 1080, 80


def fetch(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / url.rsplit("/", 1)[-1]
    if not p.exists():
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
    return json.loads(p.read_text())


def topo_features(topo, obj):
    """TopoJSON object -> [(properties, [polygon rings in lon/lat])]."""
    tf = topo.get("transform")
    arcs = []
    for arc in topo["arcs"]:
        if tf:
            x = y = 0
            pts = []
            for dx, dy in arc:
                x, y = x + dx, y + dy
                pts.append((x * tf["scale"][0] + tf["translate"][0], y * tf["scale"][1] + tf["translate"][1]))
            arcs.append(pts)
        else:
            arcs.append([tuple(p) for p in arc])

    def ring(idx):
        out = []
        for i in idx:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        return out

    feats = []
    for g in topo["objects"][obj]["geometries"]:
        if g["type"] == "Polygon":
            polys = [g["arcs"]]
        elif g["type"] == "MultiPolygon":
            polys = g["arcs"]
        else:
            continue
        feats.append((g.get("properties", {}), [[ring(r) for r in poly] for poly in polys]))
    return feats


def geo_features(geo):
    feats = []
    for f in geo["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"] if g["type"] == "MultiPolygon" else []
        feats.append((f.get("properties", {}), polys))
    return feats


def albers(lon, lat, lat1=29.5, lat2=45.5, lat0=37.5, lon0=-96):
    r = math.radians
    n = (math.sin(r(lat1)) + math.sin(r(lat2))) / 2
    c = math.cos(r(lat1)) ** 2 + 2 * n * math.sin(r(lat1))
    rho = lambda la: math.sqrt(c - 2 * n * math.sin(r(la))) / n  # noqa: E731
    th = n * r(lon - lon0)
    return rho(lat) * math.sin(th), -(rho(lat0) - rho(lat) * math.cos(th))


def project_fn(kind):
    if kind == "albers":
        return albers
    if kind == "mercator":
        return lambda lon, lat: (math.radians(lon), -math.log(math.tan(math.pi / 4 + math.radians(max(min(lat, 85), -85)) / 2)))
    return lambda lon, lat: (lon, -lat)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="us, world, or a .geojson / .topojson file")
    ap.add_argument("--object", help="TopoJSON object name")
    ap.add_argument("--name-key", default="name")
    ap.add_argument("--projection", choices=["albers", "mercator", "equirect"])
    ap.add_argument("--points", nargs="*", default=[], help='"Label=lat,lon"')
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.source in SOURCES:
        url, obj, key, proj = SOURCES[args.source]
        data = fetch(url)
    else:
        data, obj, key, proj = json.loads(Path(args.source).read_text()), args.object, args.name_key, "equirect"
    proj = args.projection or proj
    feats = topo_features(data, obj or next(iter(data["objects"]))) if data.get("type") == "Topology" else geo_features(data)
    if args.source == "us":
        feats = [f for f in feats if f[0].get(key) not in DROP_US]
    P = project_fn(proj)
    proj_feats = [(props.get(key, f"r{i}"), [[[P(lon, lat) for lon, lat in ring] for ring in poly] for poly in polys]) for i, (props, polys) in enumerate(feats)]
    xs = [x for _, polys in proj_feats for poly in polys for ring in poly for x, _ in ring]
    ys = [y for _, polys in proj_feats for poly in polys for ring in poly for _, y in ring]
    s = min((W - 2 * PAD) / (max(xs) - min(xs)), (H - 2 * PAD) / (max(ys) - min(ys)))
    ox = (W - s * (max(xs) - min(xs))) / 2 - s * min(xs)
    oy = (H - s * (max(ys) - min(ys))) / 2 - s * min(ys)
    fit = lambda x, y: (round(ox + s * x, 1), round(oy + s * y, 1))  # noqa: E731
    paths = {}
    for name, polys in proj_feats:
        d = []
        for poly in polys:
            for ring in poly:
                pts = [fit(x, y) for x, y in ring]
                d.append("M" + "L".join(f"{x},{y}" for x, y in pts) + "Z")
        paths[name] = paths.get(name, "") + "".join(d)
    points = {}
    for spec in args.points:
        label, ll = spec.split("=")
        lat, lon = (float(v) for v in ll.split(","))
        points[label] = list(fit(*P(lon, lat)))
    Path(args.out).write_text(json.dumps({"paths": paths, "points": points}))
    print(f"{args.out}: {len(paths)} regions, {len(points)} points ({proj}); " + ", ".join(f"{k} {v}" for k, v in points.items()))


if __name__ == "__main__":
    sys.exit(main())
