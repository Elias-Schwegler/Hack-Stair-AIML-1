/**
 * OpenLayers Map for Kanton Luzern
 * Based on the reference implementation
 */

let map;
let currentBackgroundLayer = 'osm';
let osmLayer, swissLayer;
let dynamicWmsLayers = []; // Store dynamically added WMS layers
let markerLayer; // Vector layer for location markers
let markerSource; // Source for markers

// Initialize the map
function initializeMap() {
    try {
        // Check if OpenLayers is loaded
        if (typeof ol === 'undefined') {
            console.error('OpenLayers (ol) is not loaded');
            return;
        }

        // Check if Proj4 is loaded
        if (typeof proj4 === 'undefined') {
            console.error('Proj4 is not loaded');
            return;
        }

        // Define Swiss coordinate system (EPSG:2056)
        proj4.defs('EPSG:2056', '+proj=somerc +lat_0=46.95240555555556 +lon_0=7.439583333333333 +k_0=1 +x_0=2600000 +y_0=1200000 +ellps=bessel +towgs84=674.374,15.056,405.346,0,0,0,0 +units=m +no_defs');
        ol.proj.proj4.register(proj4);

        // Create OSM layer with performance optimizations
        osmLayer = new ol.layer.Tile({
            source: new ol.source.OSM({
                attributions: '© OpenStreetMap contributors',
                url: 'https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                maxZoom: 19,
                cacheSize: 2048,
                crossOrigin: 'anonymous'
            }),
            visible: true,
            zIndex: 0,
            preload: 1,
            useInterimTilesOnError: false
        });

        // Create Swiss tile layer with performance optimizations
        swissLayer = new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: 'https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.pixelkarte-farbe/default/current/3857/{z}/{x}/{y}.jpeg',
                attributions: '© swisstopo',
                crossOrigin: 'anonymous',
                maxZoom: 18,
                cacheSize: 2048
            }),
            visible: false,
            zIndex: 0,
            preload: 1,
            useInterimTilesOnError: false
        });

        // Convert Luzern coordinates from EPSG:2056 to EPSG:3857
        const luzernSwiss = [2666232, 1211056]; // Swiss coordinates (LV95)
        const luzernCenter = ol.proj.transform(luzernSwiss, 'EPSG:2056', 'EPSG:3857');
        const extent = ol.proj.transformExtent([5.96, 45.82, 10.49, 47.81], 'EPSG:4326', 'EPSG:3857');
        
        const view = new ol.View({
            center: luzernCenter,
            zoom: 13,
            extent: extent
        });

        // Initialize map with basic controls
        map = new ol.Map({
            target: 'map',
            layers: [osmLayer, swissLayer],
            view: view
        });

        // Add scale line control
        map.addControl(new ol.control.ScaleLine());

        // Create marker layer for location highlighting
        markerSource = new ol.source.Vector();
        markerLayer = new ol.layer.Vector({
            source: markerSource,
            style: new ol.style.Style({
                image: new ol.style.Icon({
                    anchor: [0.5, 1],
                    anchorXUnits: 'fraction',
                    anchorYUnits: 'fraction',
                    src: 'data:image/svg+xml;utf8,' + encodeURIComponent(
                        '<svg width="32" height="48" xmlns="http://www.w3.org/2000/svg">' +
                        '<path d="M16 0C7.2 0 0 7.2 0 16c0 12 16 32 16 32s16-20 16-32C32 7.2 24.8 0 16 0z" fill="%23e74c3c"/>' +
                        '<circle cx="16" cy="16" r="8" fill="white"/>' +
                        '</svg>'
                    ),
                    scale: 1.2
                })
            }),
            zIndex: 1000
        });
        map.addLayer(markerLayer);

        // Make map globally available
        window.map = map;
        window.markerSource = markerSource;

        console.log('Map initialized successfully!');

    } catch (error) {
        console.error('Error initializing map:', error);
    }
}

// Toggle between Swiss, OSM, and WMS layers
function toggleBackgroundLayer() {
    if (!map) return;

    if (currentBackgroundLayer === 'osm') {
        // Switch to Swiss layer
        osmLayer.setVisible(false);
        swissLayer.setVisible(true);
        currentBackgroundLayer = 'swiss';
        console.log('Switched to Swiss layer');
    } else {
        // Switch to OSM layer
        swissLayer.setVisible(false);
        osmLayer.setVisible(true);
        currentBackgroundLayer = 'osm';
        console.log('Switched to OSM layer');
    }
}

// Add dynamic WMS layer from URL
function addWmsLayer(wmsUrl, layerName = 'Dynamic WMS Layer') {
    if (!map) {
        console.error('Map not initialized');
        return;
    }

    // Parse WMS URL to extract base URL and parameters
    let baseUrl = wmsUrl;
    let layerParams = '0';

    // If URL already has parameters, extract them
    if (wmsUrl.includes('?')) {
        const urlParts = wmsUrl.split('?');
        baseUrl = urlParts[0];
        
        // Parse existing parameters
        const urlParams = new URLSearchParams(urlParts[1]);
        if (urlParams.has('LAYERS')) {
            layerParams = urlParams.get('LAYERS');
        }
    }

    try {
        // Create WMS tile source (using TileWMS like the reference implementation)
        const wmsSource = new ol.source.TileWMS({
            url: baseUrl,
            params: {
                'LAYERS': layerParams,
                'VERSION': '1.3.0',
                'FORMAT': 'image/png',
                'TRANSPARENT': true,
                'STYLES': '',
                'TILED': true
            },
            serverType: 'mapserver',
            crossOrigin: 'anonymous'
        });

        const wmsLayer = new ol.layer.Tile({
            source: wmsSource,
            visible: true,
            zIndex: 100 + dynamicWmsLayers.length,
            opacity: 1.0
        });

        wmsLayer.set('name', layerName);
        wmsLayer.set('wmsUrl', wmsUrl);
        
        map.addLayer(wmsLayer);
        dynamicWmsLayers.push(wmsLayer);
        
        console.log('Added WMS layer:', layerName, wmsUrl);
        console.log('Layer params:', layerParams);
        
        // Update layer control UI
        updateLayerControl();
        
        return wmsLayer;
    } catch (error) {
        console.error('Error adding WMS layer:', error);
        return null;
    }
}

// Remove all dynamic WMS layers
function clearDynamicWmsLayers() {
    if (!map) return;
    
    dynamicWmsLayers.forEach(layer => {
        map.removeLayer(layer);
    });
    
    dynamicWmsLayers = [];
    updateLayerControl();
    console.log('Cleared all dynamic WMS layers');
}

// Toggle visibility of a specific WMS layer
function toggleWmsLayer(layerIndex) {
    if (layerIndex < 0 || layerIndex >= dynamicWmsLayers.length) return;
    
    const layer = dynamicWmsLayers[layerIndex];
    layer.setVisible(!layer.getVisible());
    updateLayerControl();
}

// Update the layer control UI
function updateLayerControl() {
    const mapSection = document.querySelector('.map-section');
    let layerControl = document.getElementById('layer-control');
    
    // Create layer control if it doesn't exist
    if (!layerControl && dynamicWmsLayers.length > 0) {
        layerControl = document.createElement('div');
        layerControl.id = 'layer-control';
        layerControl.className = 'layer-control';
        mapSection.appendChild(layerControl);
    }
    
    if (layerControl) {
        if (dynamicWmsLayers.length === 0) {
            layerControl.remove();
            return;
        }
        
        let html = '<div class="layer-control-header">WMS Layers <button onclick="clearDynamicWmsLayers()" class="clear-layers-btn">✕ Alle entfernen</button></div>';
        
        dynamicWmsLayers.forEach((layer, index) => {
            const name = layer.get('name') || `Layer ${index + 1}`;
            const visible = layer.getVisible();
            const visibilityIcon = visible ? '👁️' : '👁️‍🗨️';
            
            html += `
                <div class="layer-control-item">
                    <button onclick="toggleWmsLayer(${index})" class="layer-toggle-btn" title="${visible ? 'Ausblenden' : 'Einblenden'}">
                        ${visibilityIcon}
                    </button>
                    <span class="layer-name" title="${layer.get('wmsUrl')}">${name}</span>
                </div>
            `;
        });
        
        layerControl.innerHTML = html;
    }
}

// Get WMS capabilities to extract layer information
async function getWmsCapabilities(wmsUrl) {
    try {
        const baseUrl = wmsUrl.split('?')[0];
        const capabilitiesUrl = `${baseUrl}?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0`;
        
        const response = await fetch(capabilitiesUrl);
        const xmlText = await response.text();
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
        
        // Extract layer names
        const layers = xmlDoc.querySelectorAll('Layer > Name');
        const layerNames = Array.from(layers).map(l => l.textContent);
        
        return layerNames;
    } catch (error) {
        console.error('Error fetching WMS capabilities:', error);
        return [];
    }
}

// Setup button event handlers
function setupButtonHandlers() {
    const toggleButton = document.getElementById('toggle-layers');
    if (toggleButton && !toggleButton.hasAttribute('data-handler-attached')) {
        toggleButton.addEventListener('click', toggleBackgroundLayer);
        toggleButton.setAttribute('data-handler-attached', 'true');
        console.log('Toggle button handler attached');
    }
}

// Initialize map on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing map...');
    initializeMap();
    setupButtonHandlers();
});

// Zoom to location with animated transition
function zoomToLocation(x, y, zoom = 16, addMarker = true) {
    if (!map) {
        console.error('Map not initialized');
        return;
    }

    try {
        // Convert Swiss LV95 coordinates to map projection (EPSG:3857)
        const coords = ol.proj.transform([x, y], 'EPSG:2056', 'EPSG:3857');
        
        // Animate zoom and pan to location
        const view = map.getView();
        view.animate({
            center: coords,
            zoom: zoom,
            duration: 1000,
            easing: ol.easing.easeOut
        });

        // Add marker if requested
        if (addMarker) {
            addLocationMarker(x, y);
        }

        console.log(`Zoomed to location: ${x}, ${y}`);
    } catch (error) {
        console.error('Error zooming to location:', error);
    }
}

// Add a marker at specified location
function addLocationMarker(x, y, label = '') {
    if (!markerSource) {
        console.error('Marker source not initialized');
        return;
    }

    try {
        // Convert coordinates to map projection
        const coords = ol.proj.transform([x, y], 'EPSG:2056', 'EPSG:3857');
        
        // Create marker feature
        const marker = new ol.Feature({
            geometry: new ol.geom.Point(coords),
            name: label
        });

        // Add marker to source
        markerSource.addFeature(marker);

        console.log(`Added marker at: ${x}, ${y}`);
    } catch (error) {
        console.error('Error adding marker:', error);
    }
}

// Clear all markers from map
function clearMarkers() {
    if (markerSource) {
        markerSource.clear();
        console.log('Cleared all markers');
    }
}

// Zoom to location by name using LocationFinder API
async function zoomToLocationByName(locationName) {
    if (!locationName) return;

    try {
        const apiUrl = `https://svc.geo.lu.ch/locationfinder/api/v1/lookup?query=${encodeURIComponent(locationName)}&limit=1`;
        
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error('LocationFinder API request failed');
        }

        const data = await response.json();
        const locs = data.locs || [];

        if (locs.length > 0) {
            const location = locs[0];
            const x = location.cx;
            const y = location.cy;
            const name = location.name;

            // Zoom to location with marker
            zoomToLocation(x, y, 16, true);

            console.log(`Found location: ${name} at ${x}, ${y}`);
            return { x, y, name };
        } else {
            console.log(`No location found for: ${locationName}`);
            return null;
        }
    } catch (error) {
        console.error('Error finding location:', error);
        return null;
    }
}

// Make functions globally available
window.toggleBackgroundLayer = toggleBackgroundLayer;
window.addWmsLayer = addWmsLayer;
window.clearDynamicWmsLayers = clearDynamicWmsLayers;
window.toggleWmsLayer = toggleWmsLayer;
window.getWmsCapabilities = getWmsCapabilities;
window.zoomToLocation = zoomToLocation;
window.addLocationMarker = addLocationMarker;
window.clearMarkers = clearMarkers;
window.zoomToLocationByName = zoomToLocationByName;
