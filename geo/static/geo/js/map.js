class GeoReachMap {
    constructor(mapElementId, config, clusters, stateDemographics, districtDemographics, matchScores) {
        this.mapConfig = config;
        this.clusters = clusters;
        this.stateDemographics = stateDemographics || {};
        this.districtDemographics = districtDemographics || {};
        this.matchScores = matchScores || {};
        this.map = L.map(mapElementId).setView([config.center_lat, config.center_lng], config.initial_zoom);
        this.geojsonLayerCache = {};
        this.currentLayer = null;
        this.currentZoomLevel = null;
        
        console.log("🗺️ Map initialized with:", {
            matchScores: Object.keys(this.matchScores).length,
            states: Object.keys(this.stateDemographics).length,
            districts: Object.keys(this.districtDemographics).length
        });
        
        this.initBaseMaps();
        this.setupBoundaryLayers();
    }

    initBaseMaps() {
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: this.mapConfig.max_zoom
        }).addTo(this.map);
    }

    /**
     * Get color based on match score (0-100)
     */
    getColorByScore(score) {
        if (score === null || score === undefined || score === 0) return '#ADD8E6';  // Light blue - No data
        if (score >= 70) return '#28a745';  // Green - High match
        if (score >= 50) return '#ffc107';  // Yellow - Medium match
        if (score >= 30) return '#fd7e14';  // Orange - Low-medium match
        return '#dc3545';                    // Red - Low match
    }

    setupBoundaryLayers() {
        // Debounced zoom handler to reduce lag
        let zoomTimeout;
        this.map.on('zoomend', () => {
            clearTimeout(zoomTimeout);
            zoomTimeout = setTimeout(() => {
                const zoom = this.map.getZoom();
                console.log(`🔍 Zoom changed to: ${zoom}`);
                this.showGeoJsonLayer(zoom);
            }, 100); // 100ms debounce
        });

        const initialZoom = this.map.getZoom();
        this.showGeoJsonLayer(initialZoom);
    }

    getGeoJsonFile(zoom) {
        return zoom < this.mapConfig.zoom_thresholds.state_to_district 
            ? this.mapConfig.geojson_paths.adm1 
            : this.mapConfig.geojson_paths.adm2;
    }

    showGeoJsonLayer(zoom) {
        const geojsonFile = this.getGeoJsonFile(zoom);
        const isStateLevel = zoom < this.mapConfig.zoom_thresholds.state_to_district;

        console.log(`📍 Current zoom: ${zoom}, Loading: ${isStateLevel ? 'STATES' : 'DISTRICTS'}`);
        console.log(`📂 GeoJSON file: ${geojsonFile}`);

        // Don't reload if already showing the correct layer
        if (this.currentZoomLevel === (isStateLevel ? 'state' : 'district')) {
            console.log(`✅ Already showing ${isStateLevel ? 'STATE' : 'DISTRICT'} layer`);
            return;
        }

        // Remove current layer
        if (this.currentLayer) {
            console.log(`🗑️ Removing old layer`);
            this.map.removeLayer(this.currentLayer);
            this.currentLayer = null;
        }

        if (zoom < 4) {
            this.currentZoomLevel = null;
            return;
        }

        // Use cached layer if available
        if (this.geojsonLayerCache[geojsonFile]) {
            this.currentLayer = this.geojsonLayerCache[geojsonFile];
            this.currentLayer.addTo(this.map);
            this.currentZoomLevel = isStateLevel ? 'state' : 'district';
            console.log(`✅ Loaded cached ${isStateLevel ? 'STATE' : 'DISTRICT'} layer`);
            return;
        }

        // Fetch and create new layer
        console.log(`📥 Fetching ${isStateLevel ? 'STATE' : 'DISTRICT'} GeoJSON from: /static/${geojsonFile}`);
        
        fetch(`/static/${geojsonFile}`)
            .then(response => {
                console.log(`📡 Response status: ${response.status}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(`✅ GeoJSON loaded: ${geojsonFile}, Features: ${data.features?.length}`);
                
                const layer = L.geoJSON(data, {
                    style: (feature) => {
                        const name = feature.properties.shapeName || 
                                feature.properties.shapeGroup ||
                                feature.properties.DISTRICT || 
                                feature.properties.NAME_1 || 
                                "Unknown";
                        
                        let fillColor = '#ADD8E6';  // Light blue default
                        
                        if (isStateLevel) {
                            // Check if we have match scores
                            const hasMatchScores = Object.keys(this.matchScores).length > 0;
                            
                            if (hasMatchScores) {
                                const score = this.matchScores[name];
                                if (score !== undefined && score !== null) {
                                    fillColor = this.getColorByScore(score);
                                }
                            }
                        } else {
                            // District level - color by literacy rate
                            const districtData = this.districtDemographics[name];
                            if (districtData && districtData.literacy_rate !== null && districtData.literacy_rate !== undefined) {
                                const rate = parseFloat(districtData.literacy_rate);
                                if (rate >= 80) fillColor = '#28a745';      // Green
                                else if (rate >= 70) fillColor = '#ffc107'; // Yellow
                                else if (rate >= 60) fillColor = '#fd7e14'; // Orange
                                else fillColor = '#dc3545';                 // Red
                            }
                        }
                        
                        return {
                            color: "#2196F3",      // Blue border
                            weight: 1.5,
                            fillOpacity: 0.6,
                            fillColor: fillColor
                        };
                    },
                    onEachFeature: (feature, layer) => {
                        const name = feature.properties.shapeName || 
                                feature.properties.shapeGroup ||
                                feature.properties.DISTRICT || 
                                feature.properties.NAME_1 || 
                                "Unknown";
                        
                        // Hover effects
                        layer.on('mouseover', (e) => {
                            const hoveredLayer = e.target;
                            hoveredLayer.setStyle({
                                weight: 3,
                                fillOpacity: 0.8,
                                color: "#1976D2"
                            });
                            
                            if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                                hoveredLayer.bringToFront();
                            }
                        });
                        
                        layer.on('mouseout', (e) => {
                            const hoveredLayer = e.target;
                            hoveredLayer.setStyle({
                                weight: 1.5,
                                fillOpacity: 0.6,
                                color: "#2196F3"
                            });
                        });
                        
                        // Create popup with data
                        let popupContent = `<div style="font-family: Arial, sans-serif;"><b>${name}</b><br>`;
                        
                        if (isStateLevel) {
                            const stateData = this.stateDemographics[name];
                            const matchScore = this.matchScores[name];
                            
                            if (matchScore !== undefined && matchScore !== null) {
                                popupContent += `<strong style="color: ${this.getColorByScore(matchScore)};">Match Score: ${matchScore.toFixed(1)}%</strong><br>`;
                            }
                            
                            if (stateData) {
                                popupContent += `
                                    Population: ${parseInt(stateData.population).toLocaleString()}<br>
                                    Employment Rate: ${stateData.employment_rate || 'N/A'}%<br>
                                    Population Density: ${stateData.population_density || 'N/A'}/km²<br>
                                    Unemployment Rate: ${stateData.est_unemployment_rate || 'N/A'}%<br>
                                    Area Type: ${stateData.area_type || 'N/A'}
                                `;
                            } else {
                                popupContent += '<i>No data available</i>';
                            }
                        } else {
                            // DISTRICT POPUP - Enhanced with entrepreneur-relevant metrics
                            const districtData = this.districtDemographics[name];
                            if (districtData) {
                                popupContent += `
                                    <strong>📍 Location Details:</strong><br>
                                    State: ${districtData.state_name || 'N/A'}<br>
                                    District Population: ${districtData.population_district ? parseInt(districtData.population_district).toLocaleString() : 'N/A'}<br>
                                    <br>
                                    <strong>📊 Market Indicators:</strong><br>
                                    Literacy Rate: ${districtData.literacy_rate || 'N/A'}% 
                                    ${districtData.literacy_rate >= 80 ? '🟢' : districtData.literacy_rate >= 70 ? '🟡' : districtData.literacy_rate >= 60 ? '🟠' : '🔴'}<br>
                                    Area Type: ${districtData.area_type || 'N/A'}<br>
                                    Population Density: ${districtData.population_density || 'N/A'}/km²<br>
                                    <br>
                                    <strong>💼 Economic Indicators:</strong><br>
                                    Employment Rate: ${districtData.employment_rate || 'N/A'}%<br>
                                    Unemployment Rate: ${districtData.est_unemployment_rate || 'N/A'}%<br>
                                    ${districtData.avg_income ? `Avg Income: ₹${parseInt(districtData.avg_income).toLocaleString()}<br>` : ''}
                                    ${districtData.avg_spending ? `Avg Spending: ₹${parseInt(districtData.avg_spending).toLocaleString()}<br>` : ''}
                                    <br>
                                    <em style="color: #666; font-size: 0.9em;">
                                    ${districtData.literacy_rate >= 80 && districtData.employment_rate >= 70 
                                        ? '✅ Strong market potential' 
                                        : districtData.literacy_rate >= 70 
                                        ? '⚠️ Moderate market potential' 
                                        : '❌ Challenging market'}
                                    </em>
                                `;
                            } else {
                                popupContent += '<i>No data available</i>';
                            }
                        }
                        
                        popupContent += '</div>';
                        layer.bindPopup(popupContent);
                    }
                });
                
                // Cache and display the layer
                this.geojsonLayerCache[geojsonFile] = layer;
                this.currentLayer = layer;
                this.currentZoomLevel = isStateLevel ? 'state' : 'district';
                layer.addTo(this.map);
                
                console.log(`✅ ${isStateLevel ? 'STATE' : 'DISTRICT'} layer added to map`);
            })
            .catch(error => {
                console.error('❌ Error loading GeoJSON:', error, 'File:', geojsonFile);
                console.error('Full path attempted:', `/static/${geojsonFile}`);
            });
    }
}