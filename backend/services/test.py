import requests
import xml.etree.ElementTree as ET
map_id = []
url = "https://map.geo.lu.ch/feed.xml"
r = requests.get(url, timeout=20)
r.raise_for_status()

root = ET.fromstring(r.content)

links = []
for item in root.findall(".//item/link"):
    link_text = item.text.strip()
    if "map.geo.lu.ch" in link_text:
        path = link_text.split("map.geo.lu.ch", 1)[1]
        links.append(path)

for l in links:
    map_id.append(l)
print(map_id)