"""
Tool-calling functions for Geopard RAG - Phase 1
Provides integration with LocationFinder API and Webmap URL generation
"""

import requests
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlencode, quote
import requests
import xml.etree.ElementTree as ET


class LocationFinderTool:
    """
    LocationFinder API integration for converting location queries to coordinates
    """
    
    BASE_URL = "https://svc.geo.lu.ch/locationfinder/api/v1/lookup"
    
    SEARCH_TYPES = {
        'adresse': 'Adresse',
        'gemeinde': 'Gemeinde', 
        'ortsname': 'Ortsname',
        'flurname': 'Flurname',
        'egid': 'EGID',
        'egrid': 'EGRID',
        'parzelle': 'Parzellennummer',
        'gebaeude': 'Gebäudeversicherungsnummer'
    }
    
    def search(self, query: str, limit: int = 10, filter_type: Optional[str] = None) -> List[Dict]:
        """
        Search for locations using LocationFinder API
        
        Args:
            query: Search query (address, place name, EGID, etc.)
            limit: Maximum number of results
            filter_type: Optional filter for specific type (e.g., 'Adresse')
        
        Returns:
            List of location results with coordinates
        """
        params = {
            'query': query,
            'limit': limit
        }
        
        if filter_type:
            params['filter'] = f"type:{filter_type}"
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # API returns 'locs' array, not 'results'
            items = data.get('locs', [])
            
            results = []
            for item in items:
                results.append({
                    'id': item.get('id'),
                    'type': item.get('type'),
                    'name': item.get('name'),
                    'cx': item.get('cx'),  # Center X coordinate
                    'cy': item.get('cy'),  # Center Y coordinate
                    'xmin': item.get('xmin'),
                    'ymin': item.get('ymin'),
                    'xmax': item.get('xmax'),
                    'ymax': item.get('ymax'),
                    'fields': item.get('fields', {})
                })
            
            return results
            
        except requests.RequestException as e:
            print(f"❌ LocationFinder API error: {e}")
            return []
        except Exception as e:
            print(f"❌ LocationFinder parsing error: {e}")
            return []
    
    def get_coordinates(self, query: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a location query
        
        Returns:
            (x, y) coordinates or None if not found
        """
        results = self.search(query, limit=1)
        if results:
            result = results[0]
            return (result['cx'], result['cy'])
        return None


class WebmapURLBuilder:
    """
    Build URLs for Luzern Webmaps with zoom and marker support
    """
    
    BASE_URL = "https://map.geo.lu.ch"
    
    # Common map themes
        
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
    MAPS["default"] = "objekte/grundbuchplan"

   
    
    def build_url(
        self, 
        map_theme: str = 'default',
        x: Optional[float] = None,
        y: Optional[float] = None,
        zoom: int = 4515,
        add_marker: bool = True
    ) -> str:
        """
        Build a webmap URL with focus and marker
        
        Args:
            map_theme: Map theme key (e.g., 'grundbuchplan')
            x, y: Coordinates (Swiss LV95)
            zoom: Zoom level (higher = more zoomed in)
            add_marker: Whether to add a marker at the location
        
        Returns:
            Complete webmap URL
        """
        map_path = self.MAPS.get(map_theme, self.MAPS['default'])
        url = f"{self.BASE_URL}/{map_path}"
        
        params = []
        
        if x is not None and y is not None:
            params.append(f"FOCUS={x:.0f}:{y:.0f}:{zoom}")
        
        if add_marker and x is not None and y is not None:
            params.append("marker")
        
        if params:
            url += "?" + "&".join(params)
        
        return url
    
    def get_map_for_dataset(self, dataset_title: str) -> str:
        """
        Determine appropriate map theme based on dataset title
        
        Args:
            dataset_title: Title of the dataset
        
        Returns:
            Map theme key
        """
        t = dataset_title.lower()
        
        if any(w in t for w in ["baugesuch", "baubewilligung"]): return "objekte/baugesuche"
        elif any(w in t for w in ["grundbuch", "kataster", "parzelle", "vermess"]): return "objekte/grundbuchplan"
        elif any(w in t for w in ["baugrund", "untergrund", "geologie"]): return "baugrundklassen/"
        elif any(w in t for w in ["altlast", "bodenbelast"]): return "bodenbelastung/altlasten"
        elif "bodenverschieb" in t: return "bodenbelastung/bodenverschiebungen"
        elif any(w in t for w in ["bistum", "kirche", "pfarrei"]): return "bistum/"
        elif any(w in t for w in ["bodenkarte", "pedolog", "boden " ]): return "boden/karten"
        elif any(w in t for w in ["melioration", "bodenverbesserung", "boden verbesserung"]): return "boden/verbesserungen"
        elif "kartier" in t: return "boden/kartierung"
        elif "bage" in t: return "bage"
        elif any(w in t for w in ["geak", "gebaeudeenergie geak"]): return "gebaeudeenergie/geak"
        elif any(w in t for w in ["heizung", "wärme", "waerme", "heiz"]): return "gebaeudeenergie/heizungen"
        elif any(w in t for w in ["solar", "photovoltaik", "pv"]): return "gebaeudeenergie/solarpotential"
        elif any(w in t for w in ["erdwärme", "erdwaerme", "tiefenwärme"]): return "gebaeudeenergie/erdwaerme"
        elif any(w in t for w in ["energieplanung", "energiestadt"]): return "energieplanung/planung"
        elif "energiestadt" in t: return "energieplanung/energiestadt"
        elif "fischerei" in t: return "fauna/fischerei"
        elif "jagd" in t: return "fauna/jagd"
        elif any(w in t for w in ["hundeleinenpflicht", "leinenpflicht"]): return "fauna/hundeleinenpflicht"
        elif "fff" in t: return "fff"
        elif any(w in t for w in ["mobilfunk", "antenne", "sender"]): return "infrastruktur/mobilfunk"
        elif any(w in t for w in ["strassenbeleuchtung", "straßenbeleuchtung", "beleuchtung"]): return "infrastruktur/strassenbeleuchtung"
        elif "2017" in t and "histor" in t: return "historische_karten/2017"
        elif "1970" in t and "histor" in t: return "historische_karten/1970"
        elif "1930" in t and "histor" in t: return "historische_karten/1930"
        elif any(w in t for w in ["1880", "siegfried", "dufour"]): return "historische_karten/1880"
        elif any(w in t for w in ["1864", "1867"]) and "histor" in t: return "historische_karten/1864-1867"
        elif any(w in t for w in ["klimaanalyse", "heiß", "heiss", "hitze", "hitzetag"]): return "klimakarten/klimaanalyse_tag"
        elif any(w in t for w in ["klimaanalyse nacht", "nachtkühl", "nachtkuehl"]): return "klimakarten/klimaanalyse_nacht"
        elif "planungshinweis" in t and "tag" in t: return "klimakarten/planungshinweise_tag"
        elif "planungshinweis" in t and "nacht" in t: return "klimakarten/planungshinweise_nacht"
        elif any(w in t for w in ["denkmal", "schutzobjekt", "inventar kulturgüter", "kulturgüter", "kulturgueter"]): return "kulturgueter/denkmaeler"
        elif any(w in t for w in ["fundstelle", "archäologie", "archaeologie"]): return "kulturgueter/fundstellen"
        elif "isos" in t: return "kulturgueter/isos"
        elif any(w in t for w in ["lärm strasse", "laerm strasse", "strassenlaerm", "verkehrslaerm"]): return "laerm/strassenlaerm"
        elif any(w in t for w in ["schiesslärm", "schiesslaerm", "schiess"]): return "laerm/schiesslaerm"
        elif any(w in t for w in ["landwert zone", "bodenrichtwert zone", "zonenwert"]): return "landwerte/zone"
        elif any(w in t for w in ["landwert efh", "einfamilienhaus"]): return "landwerte/efh"
        elif "stockwerkeigentum" in t: return "landwerte/stockwerkeigentum"
        elif "gewerbe" in t and "landwert" in t: return "landwerte/gewerbe"
        elif any(w in t for w in ["bff ", "biodiversitätsförder", "biodiversitaetsfoerder"]): return "landwirtschaft/bff"
        elif any(w in t for w in ["ln ", "landwirtschaftliche nutzfl", "landwirtschaftliche nutzflaechen"]): return "landwirtschaft/ln"
        elif "bewirtschaftung" in t: return "landwirtschaft/bewirtschaftung"
        elif "pflanzenschutz" in t: return "landwirtschaft/pflanzenschutz"
        elif "bodenschutz" in t: return "landwirtschaft/bodenschutz"
        elif "grundlagen" in t and "landwirtschaft" in t: return "landwirtschaft/grundlagen"
        elif "luft" == t or any(w in t for w in ["luftqualität", "luftqualitaet", "immission"]): return "luft"
        elif any(w in t for w in ["sommertage"]): return "klimaszenarien/sommertage"
        elif any(w in t for w in ["hitzetage"]): return "klimaszenarien/hitzetage"
        elif any(w in t for w in ["tropennächte", "tropennaechte"]): return "klimaszenarien/tropennaechte"
        elif "frosttage" in t: return "klimaszenarien/frosttage"
        elif "eistage" in t: return "klimaszenarien/eistage"
        elif "neuschneetage" in t: return "klimaszenarien/neuschneetage"
        elif any(w in t for w in ["niederschlag", "regen"]): return "klimaszenarien/niederschlag"
        elif any(w in t for w in ["tagesmitteltemperatur", "mitteltemperatur"]): return "klimaszenarien/tagesmitteltemperatur"
        elif "tagesmaximumtemperatur" in t: return "klimaszenarien/tagesmaximumtemperatur"
        elif "tagesminimumtemperatur" in t: return "klimaszenarien/tagesminimumtemperatur"
        elif "synopt" in t: return "naturrisiken/synoptisch"
        elif any(w in t for w in ["einzelprozess", "einzelprozesse"]): return "naturrisiken/einzelprozesse"
        elif any(w in t for w in ["bundesinventar", "inventar bundes"]): return "naturinventare/bundesinventare"
        elif "inr" in t: return "naturinventare/inr"
        elif any(w in t for w in ["bestandesaufnahme", "bestandesaufnahmen"]): return "naturinventare/bestandesaufnahmen"
        elif any(w in t for w in ["gefahrenkarte", "gefahrenkarte", "gefahr " , "naturgefahr"]): return "naturgefahren/gefahrenkarten"
        elif "intensitaet" in t or "intensität" in t: return "naturgefahren/intensitaet"
        elif any(w in t for w in ["fließ", "fliess", "fliesstiefe", "fließtiefe"]): return "naturgefahren/fliesstiefen"
        elif any(w in t for w in ["oberflächenabfluss", "oberflaechenabfluss"]): return "naturgefahren/oberflaechenabfluss"
        elif "baulinie" in t: return "nutzungsplanung/baulinien"
        elif "planungszone" in t: return "nutzungsplanung/planungszonen"
        elif any(w in t for w in ["sondernutzung", "sondernutzungsplan"]): return "nutzungsplanung/sondernutzung"
        elif any(w in t for w in ["gewaesserraum", "gewässerraum"]): return "nutzungsplanung/gewaesserraum"
        elif any(w in t for w in ["gefahrenzone", "gefahrenzonen"]): return "nutzungsplanung/gefahrenzonen"
        elif any(w in t for w in ["lärmempfind", "laermempfind"]): return "nutzungsplanung/laermempfindlichkeit"
        elif any(w in t for w in ["zonenplan", "nutzungsplan"]): return "nutzungsplanung/zonenplan"
        elif any(w in t for w in ["luftbild", "orthofoto", "orthophoto", "aerophoto", "luftaufnahme"]): return "luftbilder/2023"
        elif any(w in t for w in ["luftbild 2020", "orthofoto 2020"]): return "luftbilder/2020"
        elif any(w in t for w in ["luftbild 2017", "orthofoto 2017"]): return "luftbilder/2017"
        elif any(w in t for w in ["luftbild 2014", "orthofoto 2014"]): return "luftbilder/2014"
        elif any(w in t for w in ["luftbild 2011", "orthofoto 2011"]): return "luftbilder/2011"
        elif any(w in t for w in ["luftbild 2008", "orthofoto 2008"]): return "luftbilder/2008"
        elif any(w in t for w in ["luftbild 2005", "orthofoto 2005"]): return "luftbilder/2005"
        elif any(w in t for w in ["luftbild 1998", "orthofoto 1998"]): return "luftbilder/1998"
        elif "ortsplan" in t: return "ortsplan"
        elif any(w in t for w in ["technische gefahr", "störfall", "stoerfall"]): return "technische_gefahren/"
        elif "wanderweg" in t and "teilrichtplan" in t: return "teilrichtplan/wanderwege"
        elif "siedlungslenkung" in t: return "teilrichtplan/siedlungslenkung"
        elif any(w in t for w in ["regionale entwicklungsträger", "regionale entwicklungstraeger"]): return "teilrichtplan/regionale_entwicklungstraeger"
        elif any(w in t for w in ["gewässer", "gewaesser", "wasser", "see", "fluss", "bach"]): return "oberflaechengewaesser/netz"
        elif "oekomorphologie" in t and "oberflaechengewaesser" in t: return "oberflaechengewaesser/oekomorphologie"
        elif "revitalisier" in t and "oberflaechengewaesser" in t: return "oberflaechengewaesser/revitalisierung"
        elif "sanierung wasserkraft" in t or "wasserkraft sanierung" in t: return "sanierung_wasserkraft/"
        elif "schutzbauten" in t and "bevoelkerungsschutz" not in t: return "schutzbauten"
        elif "schutzverordnung" in t or "schutzverordnungen" in t: return "schutzverordnungen"
        elif "bevoelkerungsschutz" in t and "schutzbauten" in t: return "bevoelkerungsschutz/schutzbauten"
        elif "alarmierung" in t: return "bevoelkerungsschutz/alarmierung"
        elif "notfalltreffpunkt" in t or "notfall-treffpunkt" in t: return "bevoelkerungsschutz/notfalltreffpunkte"
        elif any(w in t for w in ["sportanlage", "sport anlage", "sporthalle", "sportplatz"]): return "sport/anlagen"
        elif "namenbuch" in t: return "namenbuch/"
        elif any(w in t for w in ["strassennetz", "verkehrsnetz", "strassen netz"]): return "strassen/netz"
        elif "ausnahmetransportroute" in t: return "strassen/ausnahmetransportrouten"
        elif any(w in t for w in ["verkehrszählung", "verkehrszaehlung"]): return "strassen/verkehrszaehlung"
        elif any(w in t for w in ["öpnv", "oev", "oepnv", "bus", "bahn", "zug"]): return "oev/netz"
        elif "angebotsstufe" in t: return "oev/angebotsstufen"
        elif "einzugsgebiet" in t: return "oev/einzugsgebiete"
        elif "wanderwege" in t and "oev" in t: return "oev/wanderwege"
        elif "uebersichtsplan" in t or "übersichtsplan" in t: return "uebersichtsplan"
        elif "standortsuche" in t: return "standortsuche"
        elif any(w in t for w in ["vierwaldst", "vierwaldstaetter", "vierwaldstätter"]): return "vierwaldstaettersee/schutz_und_nutzung"
        elif "wasserpflanzen" in t: return "vierwaldstaettersee/wasserpflanzen"
        elif "oekomorphologie" in t and "vierwaldstaettersee" in t: return "vierwaldstaettersee/oekomorphologie"
        elif "revitalisierungsplanung" in t: return "vierwaldstaettersee/revitalisierungsplanung"
        elif "waldstandort" in t: return "wald/standorte"
        elif "waldbestand" in t or ("wald" in t and "bestand" in t): return "wald/bestand"
        elif "waldfunktion" in t or ("wald" in t and "funktion" in t): return "wald/funktionen"
        elif "waldstrasse" in t or ("wald" in t and "strasse" in t): return "wald/strassen"
        elif "waldbrand" in t: return "wald/waldbrand"
        elif "vernetzung ist" in t: return "vernetzung/ist"
        elif "vernetzung soll" in t: return "vernetzung/soll"
        elif "grundwasser schutz" in t or ("grundwasser" in t and "schutz" in t): return "grundwasser/schutz"
        elif "grundwasser vorkommen" in t or ("grundwasser" in t and "vorkommen" in t): return "grundwasser/vorkommen"
        elif any(w in t for w in ["höhe", "hoehe", "terrain", "dtm", "dom"]): return "hoehen"
        else: return "objekte/grundbuchplan"


class GeodatashopLinkBuilder:
    """
    Build links to Geodatashop for dataset downloads
    """
    
    OPENLY_BASE = "https://www.geo.lu.ch/openly"
    SHOP_BASE = "https://geodatenshop.lu.ch"
    
    def build_openly_link(self, metauid: str) -> str:
        """
        Build link to openly.geo.lu.ch for a dataset
        
        Args:
            metauid: Metadata UID of the dataset
        
        Returns:
            URL to openly page
        """
        return f"{self.OPENLY_BASE}/dataset/{metauid}"
    
    def build_shop_link(self, search_term: str) -> str:
        """
        Build search link to geodatashop
        
        Args:
            search_term: Search term for the shop
        
        Returns:
            URL to shop search
        """
        encoded_term = quote(search_term)
        return f"{self.SHOP_BASE}?search={encoded_term}"


class GeopardToolkit:
    """
    Complete toolkit for Geopard RAG tool-calling
    """
    
    def __init__(self):
        self.location_finder = LocationFinderTool()
        self.webmap_builder = WebmapURLBuilder()
        self.shop_builder = GeodatashopLinkBuilder()
    
    def enrich_dataset_result(
        self, 
        dataset: Dict,
        user_query: str = ""
    ) -> Dict:
        """
        Enrich a dataset search result with location data and URLs
        
        Args:
            dataset: Dataset metadata from search
            user_query: User's original query (may contain location)
        
        Returns:
            Enriched dataset with additional URLs and location data
        """
        enriched = dataset.copy()
        
        # Extract location from query if present
        location_info = None
        if user_query:
            location_info = self.extract_location_from_query(user_query)
        
        # Build webmap URL
        if location_info:
            x = location_info['cx']
            y = location_info['cy']
            map_theme = self.webmap_builder.get_map_for_dataset(dataset.get('title', ''))
            webmap_url = self.webmap_builder.build_url(
                map_theme=map_theme,
                x=x,
                y=y,
                zoom=4515,
                add_marker=True
            )
            enriched['webmap_url_with_location'] = webmap_url
            enriched['location_coordinates'] = {'x': x, 'y': y}
            enriched['location_name'] = location_info.get('name', '')
        
        # Add Geodatashop links
        metauid = dataset.get('metauid', '')
        if metauid:
            enriched['openly_link'] = self.shop_builder.build_openly_link(metauid)
        
        title = dataset.get('title', '')
        if title:
            enriched['shop_search_link'] = self.shop_builder.build_shop_link(title)
        
        return enriched
    
    def extract_location_from_query(self, query: str) -> Optional[Dict]:
        """
        Try to extract location information from user query
        
        Args:
            query: User's query string
        
        Returns:
            Location info dict or None
        """
        # Common location keywords to extract
        import re
        
        # Try direct search first
        results = self.location_finder.search(query, limit=1)
        if results:
            return results[0]
        
        # Extract potential location terms
        # Look for capitalized words that might be place names
        words = query.split()
        
        # Try common patterns
        patterns = [
            r'(Bahnhof\s+\w+)',  # Bahnhof + place
            r'(\w+straße\s+\d+)',  # Street + number
            r'(\w+strasse\s+\d+)',  # Swiss spelling
            r'(\d{4}\s+\w+)',  # Postal code + place
            r'(Gemeinde\s+\w+)',  # Municipality
            r'(in\s+(\w+))',  # in + place name
            r'(für\s+(\w+))',  # für + place name
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                location_term = match.group(1)
                results = self.location_finder.search(location_term, limit=1)
                if results:
                    return results[0]
        
        # Try searching for capitalized words (potential place names)
        for word in words:
            if word and word[0].isupper() and len(word) > 3:
                results = self.location_finder.search(word, limit=1)
                if results and results[0].get('type') in ['Gemeinde', 'Ortsname', 'Adresse']:
                    return results[0]
        
        return None


# Example usage
if __name__ == "__main__":
    toolkit = GeopardToolkit()
    
    # Test LocationFinder
    print("Testing LocationFinder:")
    results = toolkit.location_finder.search("Bahnhof Luzern", limit=3)
    for r in results:
        print(f"  - {r['name']} ({r['type']}): {r['cx']}, {r['cy']}")
    
    # Test Webmap URL
    print("\nTesting Webmap URL:")
    coords = toolkit.location_finder.get_coordinates("Bahnhof Luzern")
    if coords:
        x, y = coords
        url = toolkit.webmap_builder.build_url('hoehen', x, y, zoom=4515)
        print(f"  URL: {url}")
    
    # Test enrichment
    print("\nTesting dataset enrichment:")
    sample_dataset = {
        'metauid': 'DTM2024_DST',
        'title': 'Digitales Terrainmodell 2024',
        'data_type': 'Datensatz'
    }
    enriched = toolkit.enrich_dataset_result(sample_dataset, "Bahnhof Luzern")
    print(f"  Openly: {enriched.get('openly_link')}")
    print(f"  Webmap: {enriched.get('webmap_url_with_location')}")
