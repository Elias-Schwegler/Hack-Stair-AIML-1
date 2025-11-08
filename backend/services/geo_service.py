import httpx
from typing import Dict, Tuple, Optional
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class GeoService:
    """Service to query actual geodata from WMS and ESRI REST APIs"""
    
    async def query_wms_getfeatureinfo(
        self, 
        wms_url: str, 
        layer: str, 
        coords: Tuple[float, float],
        bbox_size: int = 100
    ) -> Dict:
        """
        Query WMS GetFeatureInfo at coordinates
        
        Args:
            wms_url: WMS service URL
            layer: Layer name/number
            coords: (x, y) in Swiss coordinates (LV95/EPSG:2056)
            bbox_size: Size of bounding box around point
            
        Returns:
            Dict with feature info results
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
        
        try:
            logger.info(f"WMS GetFeatureInfo query at {coords}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(wms_url, params=params)
                response.raise_for_status()
                
                result_text = response.text
                logger.info(f"WMS response: {result_text[:200]}")
                
                return {
                    "success": True,
                    "data": result_text,
                    "format": "text/plain"
                }
                
        except Exception as e:
            logger.error(f"WMS query error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def query_esri_rest(
        self,
        service_url: str,
        layer_id: int,
        coords: Tuple[float, float]
    ) -> Dict:
        """
        Query ESRI REST API at point
        
        Args:
            service_url: Base ESRI MapServer URL
            layer_id: Layer ID number
            coords: (x, y) coordinates
            
        Returns:
            Dict with query results
        """
        x, y = coords
        
        # Build query URL
        query_url = f"{service_url}/{layer_id}/query"
        
        params = {
            'geometry': f"{x},{y}",
            'geometryType': 'esriGeometryPoint',
            'inSR': '2056',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',  # Get all fields
            'returnGeometry': 'false',
            'f': 'json'
        }
        
        try:
            logger.info(f"ESRI REST query at {coords}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(query_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract features
                features = data.get('features', [])
                logger.info(f"ESRI REST found {len(features)} features")
                
                if features:
                    return {
                        "success": True,
                        "features": features,
                        "count": len(features)
                    }
                else:
                    return {
                        "success": True,
                        "features": [],
                        "count": 0,
                        "message": "No features found at this location"
                    }
                    
        except Exception as e:
            logger.error(f"ESRI REST query error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_elevation_at_point(
        self,
        coords: Tuple[float, float]
    ) -> Dict:
        """
        Get elevation at a specific point using DTM service
        
        This is a specialized method for elevation queries.
        It tries to query the Digital Terrain Model (DTM) service.
        """
        # DTM 2024 ESRI Service from Canton Lucerne
        # Based on the documentation, look for DTM service URL
        dtm_service_url = "https://public.geo.lu.ch/ogd/rest/services/managed/DTMXXX_COL_V1_MP/MapServer"
        
        try:
            # Try to query DTM layer (usually layer 0 or 1 for elevation)
            result = await self.query_esri_rest(dtm_service_url, 0, coords)
            
            if result.get('success') and result.get('features'):
                feature = result['features'][0]
                attributes = feature.get('attributes', {})
                
                # Look for elevation field (common names: HOEHE, ELEVATION, Z, HEIGHT)
                elevation = None
                for key in ['HOEHE', 'ELEVATION', 'Z', 'HEIGHT', 'hoehe', 'elevation']:
                    if key in attributes:
                        elevation = attributes[key]
                        break
                
                if elevation is not None:
                    return {
                        "success": True,
                        "elevation": elevation,
                        "unit": "m ü. M.",
                        "coordinates": coords,
                        "source": "DTM 2024"
                    }
            
            return {
                "success": False,
                "message": "Elevation data not available at this location",
                "note": "You may need to download the DTM dataset for detailed elevation information"
            }
            
        except Exception as e:
            logger.error(f"Elevation query error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Test
if __name__ == "__main__":
    import asyncio
    
    async def test():
        service = GeoService()
        
        # Test coordinates (Bahnhof Luzern area)
        test_coords = (2667100, 1212500)
        
        print("Testing Elevation Query")
        print("="*60)
        
        result = await service.get_elevation_at_point(test_coords)
        
        print(f"Success: {result.get('success')}")
        if result.get('success'):
            print(f"Elevation: {result.get('elevation')} {result.get('unit')}")
        else:
            print(f"Message: {result.get('message')}")
            print(f"Error: {result.get('error')}")
    
    asyncio.run(test())