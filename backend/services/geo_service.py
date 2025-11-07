import httpx
from typing import Dict, Optional
from xml.etree import ElementTree as ET

class GeoService:
    
    async def query_wms_getfeatureinfo(
        self, 
        wms_url: str, 
        layer: str, 
        coords: tuple,
        bbox_size: int = 100
    ) -> str:
        """
        Query WMS GetFeatureInfo at coordinates
        coords: (x, y) in Swiss coordinates (LV95/EPSG:2056)
        """
        x, y = coords
        
        # Calculate bbox around point
        half_size = bbox_size / 2
        bbox = f"{x-half_size},{y-half_size},{x+half_size},{y+half_size}"
        
        params = {
            'service': 'WMS',
            'version': '1.3.0',
            'request': 'GetFeatureInfo',
            'format': 'image/png',
            'transparent': 'true',
            'query_layers': layer,
            'layers': layer,
            'feature_count': '10',
            'info_format': 'text/plain',
            'i': '50',
            'j': '50',
            'crs': 'EPSG:2056',
            'width': '101',
            'height': '101',
            'bbox': bbox
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(wms_url, params=params)
            response.raise_for_status()
            return response.text
    
    async def query_esri_rest(
        self,
        service_url: str,
        layer_id: int,
        coords: tuple
    ) -> Dict:
        """
        Query ESRI REST API at point
        Example URL: https://public.geo.lu.ch/ogd/rest/services/managed/WRZONXXX_COL_V1_MP/MapServer
        """
        x, y = coords
        
        query_url = f"{service_url}/{layer_id}/query"
        
        params = {
            'geometry': f"{x},{y}",
            'geometryType': 'esriGeometryPoint',
            'inSR': '2056',
            'spatialRel': 'esriSpatialRelIntersects',
            'f': 'json'
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(query_url, params=params)
            response.raise_for_status()
            return response.json()

# Test
if __name__ == "__main__":
    import asyncio
    service = GeoService()
    
    # Test ESRI REST
    result = asyncio.run(service.query_esri_rest(
        "https://public.geo.lu.ch/ogd/rest/services/managed/WRZONXXX_COL_V1_MP/MapServer",
        2,
        (2649672.80, 1207836.67)
    ))
    print(result)