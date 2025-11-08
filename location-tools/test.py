import requests
import xml.etree.ElementTree as ET

url = "https://map.geo.lu.ch/feed.xml"
r = requests.get(url, timeout=20)
r.raise_for_status()
root = ET.fromstring(r.content)

paths = []
for item in root.findall(".//item/link"):
    link = (item.text or "").strip()
    if "map.geo.lu.ch" in link:
        p = link.split("map.geo.lu.ch", 1)[1].lstrip("/")
        if p:
            paths.append(p)

MAPS = {f"{i:03d}_" + p.replace("/", "_"): p for i, p in enumerate(paths, 1)}

print("MAPS = {")
for k, v in MAPS.items():
    print(f"    '{k}': '{v}',")
print("}")