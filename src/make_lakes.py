"""Build data/lakes/lakes.geojson: the study-area outline for each lake (contract C1).

Each lake's area of interest (AOI) is:
    HydroLAKES outline  UNION  maximum water extent ever seen by WOfS (1984-today),
    holes filled (islands are part of the lake), then buffered by BUFFER_M metres.

Why both sources:
  - HydroLAKES gives an official, citable outline and ID, and covers swampy lakes
    (e.g. Ol Bolossat) that satellites see poorly as open water.
  - Many Rift Valley lakes have grown a lot since 2010, beyond their HydroLAKES
    outline. WOfS adds that new area so nothing gets cut off.

Usage (from the repo root):
    python -m src.make_lakes --hydrolakes path/to/HydroLAKES_polys_v10.shp

You only need to run this if the lake list changes: the output file is committed.
HydroLAKES (~820 MB zip): https://www.hydrosheds.org/products/hydrolakes
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import rasterio.features
import rasterio.warp
from pyproj import CRS, Transformer
from rasterio.features import shapes
from rasterio.merge import merge
from scipy import ndimage
import shapely
from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union

# ---------------------------------------------------------------------------
# Study lakes (centre points from Ramsar / BirdLife / UNESCO / Wikipedia)
# type:  freshwater | saline | swamp      split: train | val | test (model data)
# ---------------------------------------------------------------------------
LAKES = [
    # lake_id,      name,                 lon,     lat,     type,         split
    ("baringo",     "Lake Baringo",       36.080,  0.630,   "freshwater", "train"),
    ("bogoria",     "Lake Bogoria",       36.098,  0.259,   "saline",     "val"),
    ("solai",       "Lake Solai",         36.150,  0.060,   "saline",     "val"),
    ("nakuru",      "Lake Nakuru",        36.090, -0.360,   "saline",     "test"),
    ("elementaita", "Lake Elementaita",   36.240, -0.443,   "saline",     "train"),
    ("naivasha",    "Lake Naivasha",      36.351, -0.769,   "freshwater", "train"),
    ("ol_bolossat", "Lake Ol' Bolossat",  36.427, -0.108,   "swamp",      "test"),
    ("magadi",      "Lake Magadi",        36.280, -1.870,   "saline",     "test"),
    ("turkana",     "Lake Turkana",       36.052,  3.761,   "saline",     "train"),
]

KENYA_BBOX = (33.8, -4.8, 42.0, 5.1)       # lon/lat box used to pre-filter HydroLAKES
BUFFER_M = 1000                             # buffer around the combined outline
WOFS_MIN_FREQ = 0.05                        # "has been water at least 5% of clear looks"
WOFS_MIN_CLEAR = 20                         # ignore pixels with too few clear looks
MIN_HALF_WIDTH_DEG = 0.25                   # search at least this far around the centre
CENTRE_RADIUS_M = 2000                      # water within this distance of the centre is "the lake"
OPENING_PX = 2                              # strip features narrower than ~(2*2+1)*30 m (rivers)
MAX_GROW = 4                                # times to widen the box if the lake touches its edge
MIN_HL_OVERLAP = 0.5                        # HydroLAKES piece must be >=50% inside the WOfS lake

STAC = "https://explorer.digitalearth.africa/stac/search"
S3 = "https://deafrica-services.s3.af-south-1.amazonaws.com/"
EQUAL_AREA = CRS.from_epsg(6933)
WGS84 = CRS.from_epsg(4326)


def to_crs(geom, src: CRS, dst: CRS):
    t = Transformer.from_crs(src, dst, always_xy=True)
    return shapely.transform(geom, lambda xy: np.column_stack(t.transform(xy[:, 0], xy[:, 1])))


def local_metric_crs(lon: float, lat: float) -> CRS:
    """Azimuthal equidistant projection centred on the lake: true distances for buffering."""
    return CRS.from_proj4(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs")


def area_km2(geom_wgs84) -> float:
    return to_crs(geom_wgs84, WGS84, EQUAL_AREA).area / 1e6


def hydrolakes_near(lakes_gdf: gpd.GeoDataFrame, lon: float, lat: float, radius_m: float):
    """HydroLAKES polygons within radius_m of the centre point."""
    metric = local_metric_crs(lon, lat)
    d = lakes_gdf.to_crs(metric).distance(to_crs(Point(lon, lat), WGS84, metric))
    return lakes_gdf[d <= radius_m]


def wofs_alltime(bbox):
    """Read WOfS all-time frequency and clear-count for a lon/lat box (EPSG:6933 grid)."""
    url = (f"{STAC}?collections=wofs_ls_summary_alltime"
           f"&bbox={','.join(f'{v:.4f}' for v in bbox)}&limit=100")
    feats = json.load(urllib.request.urlopen(url, timeout=60))["features"]
    if not feats:
        raise RuntimeError(f"No WOfS tiles found for {bbox}")
    href = lambda f, k: S3 + f["assets"][k]["href"].split("deafrica-services/")[1]
    b = rasterio.warp.transform_bounds(WGS84, EQUAL_AREA, *bbox)
    out = {}
    for key, nodata in (("frequency", np.nan), ("count_clear", -999)):
        srcs = [rasterio.open(href(f, key)) for f in feats]
        arr, tr = merge(srcs, bounds=b, nodata=nodata)
        for s in srcs:
            s.close()
        out[key] = arr[0]
    return out["frequency"], out["count_clear"], tr


def wofs_max_extent(lon, lat, seed_geom_wgs84, bbox):
    """Water seen often enough over all years, connected to the lake centre (or the seed outline).

    Returns (geometry in WGS84 or None, touches_box_edge)."""
    freq, clear, tr = wofs_alltime(bbox)
    water = (np.nan_to_num(freq, nan=0) >= WOFS_MIN_FREQ) & (clear >= WOFS_MIN_CLEAR)
    # remove thin features (rivers, ditches) so they don't chain other water onto the lake
    water = ndimage.binary_opening(water, structure=np.ones((3, 3)), iterations=OPENING_PX)
    labels, _ = ndimage.label(water)

    centre_6933 = to_crs(Point(lon, lat), WGS84, EQUAL_AREA).buffer(CENTRE_RADIUS_M)
    seed = unary_union([centre_6933] + ([to_crs(seed_geom_wgs84, WGS84, EQUAL_AREA)]
                                        if seed_geom_wgs84 is not None else []))
    seed_mask = rasterio.features.geometry_mask([mapping(seed)], water.shape, tr, invert=True)
    keep = np.setdiff1d(np.unique(labels[seed_mask & water]), [0])
    lake = ndimage.binary_fill_holes(np.isin(labels, keep))
    if not lake.any():
        return None, False

    touches_edge = bool(lake[0].any() or lake[-1].any() or lake[:, 0].any() or lake[:, -1].any())
    polys = [shape(g) for g, v in shapes(lake.astype(np.uint8), mask=lake, transform=tr) if v == 1]
    return to_crs(unary_union(polys), EQUAL_AREA, WGS84), touches_edge


def main(hydrolakes_path: str, out_path: str):
    print("Reading HydroLAKES (Kenya only)...")
    hl = gpd.read_file(hydrolakes_path, bbox=KENYA_BBOX).to_crs(WGS84)

    features = []
    for lake_id, name, lon, lat, ltype, split in LAKES:
        # HydroLAKES polygons at the centre (seed for finding the lake in WOfS)
        seed_hl = hydrolakes_near(hl, lon, lat, CENTRE_RADIUS_M)
        seed_geom = unary_union(list(seed_hl.geometry)) if len(seed_hl) else None

        # search box: around the centre and the seed outline, widened until the lake fits
        h = MIN_HALF_WIDTH_DEG
        boxes = [(lon - h, lat - h, lon + h, lat + h)]
        if seed_geom is not None:
            boxes.append(tuple(np.add(seed_geom.bounds, (-0.1, -0.1, 0.1, 0.1))))
        bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
        for attempt in range(MAX_GROW + 1):
            wofs_geom, touches_edge = wofs_max_extent(lon, lat, seed_geom, bbox)
            if not touches_edge:
                break
            cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            hw, hh = (bbox[2] - bbox[0]) * 0.75, (bbox[3] - bbox[1]) * 0.75
            bbox = (cx - hw, cy - hh, cx + hw, cy + hh)
            print(f"  {lake_id}: lake reaches box edge, widening search (try {attempt + 1})")
        if touches_edge:
            print(f"  WARNING {lake_id}: still touches the box edge after {MAX_GROW} tries; check it by eye")

        # all HydroLAKES pieces that overlap the WOfS lake (Magadi is split into many)
        parts = [wofs_geom] if wofs_geom is not None else []
        if wofs_geom is not None:
            # keep HydroLAKES pieces that lie mostly inside the WOfS lake (drops river channels
            # that only touch it), plus the piece(s) at the centre point
            cand = hl[hl.intersects(wofs_geom)]
            overlap = cand.geometry.apply(lambda g: g.intersection(wofs_geom).area / g.area)
            hl_hits = cand[(overlap >= MIN_HL_OVERLAP) | cand.index.isin(seed_hl.index)]
        else:
            hl_hits = seed_hl
        parts += list(hl_hits.geometry)
        if not parts:
            raise RuntimeError(f"{lake_id}: found no water near its centre point")
        combined = unary_union(parts)

        metric = local_metric_crs(lon, lat)
        aoi_m = to_crs(combined, WGS84, metric).buffer(BUFFER_M).buffer(0)
        # fill holes (islands belong to the lake) and simplify
        polys = getattr(aoi_m, "geoms", [aoi_m])
        aoi_m = unary_union([shapely.Polygon(p.exterior) for p in polys]).simplify(20)
        aoi = to_crs(aoi_m, metric, WGS84)

        props = {
            "lake_id": lake_id,
            "name": name,
            "type": ltype,
            "split": split,
            "centre_lon": lon,
            "centre_lat": lat,
            "hylak_ids": sorted(int(i) for i in hl_hits["Hylak_id"]),
            "hydrolakes_area_km2": round(float(hl_hits["Lake_area"].sum()), 1),
            "wofs_max_area_km2": round(area_km2(wofs_geom), 1) if wofs_geom is not None else None,
            "aoi_area_km2": round(area_km2(aoi), 1),
            "n_parts": len(getattr(aoi, "geoms", [aoi])),
            "country": "Kenya/Ethiopia" if lake_id == "turkana" else "Kenya",
        }
        features.append({"type": "Feature", "properties": props, "geometry": mapping(aoi)})
        print(f"  {lake_id:12s} HydroLAKES {props['hydrolakes_area_km2']:>7} km2 "
              f"({len(hl_hits)} polygons) | WOfS max {props['wofs_max_area_km2']} km2 | "
              f"AOI {props['aoi_area_km2']} km2 | parts {props['n_parts']}")

    fc = {"type": "FeatureCollection", "features": features}
    text = json.dumps(fc, separators=(",", ":"))
    # round coordinates to 5 decimals (~1 m) to keep the file small
    fc = json.loads(text, parse_float=lambda s: round(float(s), 5))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(fc, indent=1))
    print(f"Wrote {out_path} ({len(features)} lakes)")


if __name__ == "__main__":
    p =argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hydrolakes", required=True, help="path to HydroLAKES_polys_v10.shp")
    p.add_argument("--out", default="data/lakes/lakes.geojson")
    a = p.parse_args()
    main(a.hydrolakes, a.out)
