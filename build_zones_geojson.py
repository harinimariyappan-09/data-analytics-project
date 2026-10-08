"""Dissolve district-level India boundaries into the 5 sales zones used by the dashboard.
Source: udit-001/india-maps-data (geojson/india.geojson, district boundaries). Output is simplified for web use."""
import json
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

ZONES = {
    "North":   ["Jammu and Kashmir", "Ladakh", "Himachal Pradesh", "Punjab", "Haryana", "Delhi", "Chandigarh", "Uttarakhand", "Rajasthan"],
    "Central": ["Uttar Pradesh", "Madhya Pradesh", "Chhattisgarh"],
    "East":    ["Bihar", "Jharkhand", "West Bengal", "Odisha", "Assam", "Arunachal Pradesh", "Manipur", "Meghalaya", "Mizoram",
                "Nagaland", "Tripura", "Sikkim", "Andaman and Nicobar Islands"],
    "West":    ["Gujarat", "Maharashtra", "Goa", "Dadra and Nagar Haveli and Daman and Diu"],
    "South":   ["Andhra Pradesh", "Telangana", "Karnataka", "Kerala", "Tamil Nadu", "Puducherry", "Lakshadweep"],
}
state_to_zone = {s: z for z, ss in ZONES.items() for s in ss}

import os, urllib.request
SRC = "india_districts_source.geojson"
if not os.path.exists(SRC):
    urllib.request.urlretrieve("https://raw.githubusercontent.com/udit-001/india-maps-data/main/geojson/india.geojson", SRC)
g = json.load(open(SRC))
buckets, unmatched = {z: [] for z in ZONES}, set()
for f in g["features"]:
    st = f["properties"]["st_nm"]
    if st not in state_to_zone:
        unmatched.add(st); continue
    buckets[state_to_zone[st]].append(shape(f["geometry"]).buffer(0))
print("unmatched states:", unmatched)

features = []
for z, geoms in buckets.items():
    u = unary_union([x.buffer(0.01) for x in geoms]).buffer(-0.01).simplify(0.03, preserve_topology=True)
    features.append({"type": "Feature", "id": z, "properties": {"zone": z}, "geometry": mapping(u)})
    print(z, len(geoms), "districts ->", u.geom_type, "| bounds", [round(b, 1) for b in u.bounds])
json.dump({"type": "FeatureCollection", "features": features}, open("india_zones.geojson", "w"), separators=(",", ":"))
