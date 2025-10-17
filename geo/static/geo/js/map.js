class GeoReachMap {
    constructor(mapElementId, config, clusters) {
        this.mapConfig = config;
        this.clusters = clusters;
        this.map = L.map(mapElementId).setView([config.center_lat, config.center_lng], config.initial_zoom);
        this.geojsonDataCache = {};
        this.geojsonLayerCache = {};
        this.currentLayer = null;
        
        this.initBaseMaps();
        this.addClusters();
        this.setupBoundaryLayers();
    }

    initBaseMaps() {
        const openStreetMap = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: this.mapConfig.max_zoom,
            attribution: '© OpenStreetMap contributors'
        });

        const cartoDB = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            maxZoom: this.mapConfig.max_zoom,
            attribution: '© CartoDB'
        });

        openStreetMap.addTo(this.map);

        const baseMaps = {
            "OpenStreetMap": openStreetMap,
            "CartoDB Positron": cartoDB
        };
        L.control.layers(baseMaps).addTo(this.map);
    }

    addClusters() {
        this.clusters.forEach(cluster => {
            const color = cluster.level === "high" ? "green" : cluster.level === "medium" ? "yellow" : "red";
            
            const marker = L.circleMarker([cluster.lat, cluster.lng], {
                color: color,
                radius: 10,
                fillOpacity: 0.7
            }).addTo(this.map);

            const popupContent = `<b>${cluster.info}</b><br>
                Income: ${cluster.demographics.income}<br>
                Employment: ${cluster.demographics.employment_rate}<br>
                Density: ${cluster.demographics.population_density}<br>
                Interest Index: ${cluster.demographics.interest_index}`;
            
            marker.bindPopup(popupContent);
        });
    }

    setupBoundaryLayers() {
        this.showGeoJsonLayer(this.map.getZoom());
        
        let zoomTimeout = null;
        this.map.on('zoomend', () => {
            clearTimeout(zoomTimeout);
            zoomTimeout = setTimeout(() => {
                this.showGeoJsonLayer(this.map.getZoom());
            }, 300);
        });
    }

    getApiEndpoint(zoom) {
        // Use PostGIS API endpoints instead of static files
        if (zoom < this.mapConfig.zoom_thresholds.state_to_district) {
            return '/geo/api/states/geojson/';
        } else {
            return '/geo/api/districts/geojson/';
        }
    }

    showGeoJsonLayer(zoom) {
        const apiEndpoint = this.getApiEndpoint(zoom);

        // Remove all active boundary layers
        Object.values(this.geojsonLayerCache).forEach(layer => {
            if (this.map.hasLayer(layer)) this.map.removeLayer(layer);
        });

        // Don't show boundaries when zoomed too far OUT
        if (zoom < 4) {
            return;
        }

        // Use cached layer if available
        if (this.geojsonLayerCache[apiEndpoint]) {
            this.currentLayer = this.geojsonLayerCache[apiEndpoint];
            this.currentLayer.addTo(this.map);
            return;
        }

        // Fetch from PostGIS API endpoint
        console.log('Loading from PostGIS API:', apiEndpoint);
        
        fetch(apiEndpoint)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('GeoJSON loaded from API:', apiEndpoint, 'Features:', data.features?.length);
                
                const isStateLevel = apiEndpoint.includes('states');
                
                const layer = L.geoJSON(data, {
                    style: () => ({
                        color: isStateLevel ? "#2c7fb8" : "#3388ff",
                        weight: isStateLevel ? 3 : 2,
                        fillOpacity: isStateLevel ? 0.15 : 0.2,
                        fillColor: isStateLevel ? "#2c7fb8" : "#3388ff"
                    }),
                    onEachFeature: (feature, layer) => {
                        layer.on('mouseover', () => {
                            layer.setStyle({
                                fillColor: 'yellow',
                                fillOpacity: 0.5
                            });
                        });
                        layer.on('mouseout', () => {
                            layer.setStyle({
                                fillColor: isStateLevel ? "#2c7fb8" : "#3388ff",
                                fillOpacity: isStateLevel ? 0.15 : 0.2
                            });
                        });
                        
                        // Get properties from API response
                        const props = feature.properties;
                        const name = props.name || "Unknown";
                        const population = props.population ? props.population.toLocaleString() : "N/A";
                        const state = props.state || "";
                        
                        let popupContent = `<b>${name}</b>`;
                        if (state) popupContent += ` (${state})`;
                        popupContent += `<br>Population: ${population}`;
                        
                        if (props.literacy_rate) {
                            popupContent += `<br>Literacy Rate: ${props.literacy_rate}%`;
                        }
                        if (props.area_km2) {
                            popupContent += `<br>Area: ${props.area_km2.toLocaleString()} km²`;
                        }
                        
                        layer.bindPopup(popupContent);
                    }
                });
                
                this.geojsonLayerCache[apiEndpoint] = layer;
                this.currentLayer = layer;
                layer.addTo(this.map);
            })
            .catch(error => {
                console.error('Error loading from PostGIS API:', error, 'Endpoint:', apiEndpoint);
            });
    }
}