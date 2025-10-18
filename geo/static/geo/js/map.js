class GeoReachMap {
    constructor(mapElementId, config, stateMetrics, districtMetrics, matchScores) {
        this.mapConfig = config;
        this.stateMetrics = stateMetrics || {};
        this.districtMetrics = districtMetrics || {};
        this.matchScores = matchScores || {};  // Keep for backward compatibility
        this.map = L.map(mapElementId).setView([config.center_lat, config.center_lng], config.initial_zoom);
        this.geojsonLayerCache = {};
        this.currentLayer = null;
        this.currentZoomLevel = null;
        
        console.log("🗺️ Map initialized with:", {
            matchScores: Object.keys(this.matchScores).length,
            states: Object.keys(this.stateMetrics).length,
            districts: Object.keys(this.districtMetrics).length
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

    /**
     * Get color with fallback logic:
     * 1. Use avg_predicted_success if available
     * 2. Fallback to spending_index
     * 3. Fallback to literacy_rate
     * 4. Default to light blue
     */
    getColorForRegion(regionData) {
        let score = null;
        
        // Priority 1: ML/Business rule prediction
        if (regionData.avg_predicted_success !== null && regionData.avg_predicted_success !== undefined) {
            score = regionData.avg_predicted_success * 100;
        }
        // Priority 2: Spending index
        else if (regionData.spending_index !== null && regionData.spending_index !== undefined) {
            score = regionData.spending_index * 100;
        }
        // Priority 3: Literacy rate
        else if (regionData.literacy_rate !== null && regionData.literacy_rate !== undefined) {
            score = regionData.literacy_rate;
        }
        // Default: light blue
        else {
            return '#ADD8E6';
        }
        
        return this.getColorByScore(score);
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
                        let opacity = 0.6;
                        
                        if (isStateLevel) {
                            const stateData = this.stateMetrics[name];
                            if (stateData) {
                                fillColor = this.getColorForRegion(stateData);
                                
                                // Lower opacity if low confidence
                                if (stateData.confidence_score && stateData.confidence_score < 0.5) {
                                    opacity = 0.4;
                                }
                            }
                        } else {
                            const districtData = this.districtMetrics[name];
                            if (districtData) {
                                fillColor = this.getColorForRegion(districtData);
                                
                                // Lower opacity if low confidence
                                if (districtData.confidence_score && districtData.confidence_score < 0.5) {
                                    opacity = 0.4;
                                }
                            }
                        }
                        
                        return {
                            color: "#2196F3",      // Blue border
                            weight: 1.5,
                            fillOpacity: opacity,
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
                        let popupContent = `<div style="font-family: Arial, sans-serif; min-width: 250px;"><b style="font-size: 1.1em;">${name}</b><br><hr style="margin: 8px 0;">`;
                        
                        if (isStateLevel) {
                            const stateData = this.stateMetrics[name];
                            
                            if (stateData) {
                                // Predicted Success
                                if (stateData.avg_predicted_success !== null && stateData.avg_predicted_success !== undefined) {
                                    const successPercent = (stateData.avg_predicted_success * 100).toFixed(1);
                                    popupContent += `<strong>🎯 Predicted Success:</strong> <span style="color: ${this.getColorByScore(successPercent)}; font-weight: bold;">${successPercent}%</span><br>`;
                                } else {
                                    popupContent += `<strong>🎯 Predicted Success:</strong> <span style="color: #999;">N/A</span><br>`;
                                }
                                
                                // Confidence Score
                                if (stateData.confidence_score !== null && stateData.confidence_score !== undefined) {
                                    const confidencePercent = (stateData.confidence_score * 100).toFixed(0);
                                    const confidenceColor = stateData.confidence_score >= 0.7 ? '#28a745' : stateData.confidence_score >= 0.5 ? '#ffc107' : '#dc3545';
                                    popupContent += `<strong>📊 Confidence:</strong> <span style="color: ${confidenceColor};">${confidencePercent}%</span><br>`;
                                }
                                
                                // Spending Index
                                if (stateData.spending_index !== null && stateData.spending_index !== undefined) {
                                    const spendingPercent = (stateData.spending_index * 100).toFixed(1);
                                    popupContent += `<strong>💰 Spending Index:</strong> ${spendingPercent}%<br>`;
                                } else {
                                    popupContent += `<strong>💰 Spending Index:</strong> <span style="color: #999;">N/A</span><br>`;
                                }
                                
                                popupContent += `<hr style="margin: 8px 0;">`;
                                
                                // Economic Indicators
                                popupContent += `<strong style="color: #17a2b8;">💼 Economic Indicators:</strong><br>`;
                                if (stateData.avg_income) {
                                    popupContent += `• Avg Income: ₹${parseInt(stateData.avg_income).toLocaleString()}<br>`;
                                }
                                if (stateData.avg_spending) {
                                    popupContent += `• Avg Spending: ₹${parseInt(stateData.avg_spending).toLocaleString()}<br>`;
                                }
                                if (stateData.employment_rate) {
                                    popupContent += `• Employment Rate: ${stateData.employment_rate}%<br>`;
                                }
                                
                                popupContent += `<hr style="margin: 8px 0;">`;
                                
                                // Demographics
                                popupContent += `<strong style="color: #6c757d;">📍 Demographics:</strong><br>`;
                                if (stateData.population_density) {
                                    popupContent += `• Population Density: ${parseFloat(stateData.population_density).toFixed(1)}/km²<br>`;
                                }
                                if (stateData.literacy_rate) {
                                    popupContent += `• Literacy Rate: ${stateData.literacy_rate}%<br>`;
                                }
                                
                                // Top Drivers (if available)
                                if (stateData.top_drivers && stateData.top_drivers.length > 0) {
                                    popupContent += `<hr style="margin: 8px 0;">`;
                                    popupContent += `<strong style="color: #28a745;">🎯 Top Drivers:</strong><br>`;
                                    stateData.top_drivers.forEach(driver => {
                                        popupContent += `• ${driver.feature}: ${(driver.weight * 100).toFixed(0)}%<br>`;
                                    });
                                }
                            } else {
                                popupContent += '<i style="color: #999;">No data available</i>';
                            }
                            
                        } else {
                            // DISTRICT POPUP
                            const districtData = this.districtMetrics[name];
                            
                            if (districtData) {
                                // Predicted Success
                                if (districtData.avg_predicted_success !== null && districtData.avg_predicted_success !== undefined) {
                                    const successPercent = (districtData.avg_predicted_success * 100).toFixed(1);
                                    popupContent += `<strong>🎯 Predicted Success:</strong> <span style="color: ${this.getColorByScore(successPercent)}; font-weight: bold;">${successPercent}%</span><br>`;
                                } else {
                                    popupContent += `<strong>🎯 Predicted Success:</strong> <span style="color: #999;">N/A</span><br>`;
                                }
                                
                                // Spending Index
                                if (districtData.spending_index !== null && districtData.spending_index !== undefined) {
                                    const spendingPercent = (districtData.spending_index * 100).toFixed(1);
                                    popupContent += `<strong>💰 Spending Index:</strong> ${spendingPercent}%<br>`;
                                } else {
                                    popupContent += `<strong>💰 Spending Index:</strong> <span style="color: #999;">N/A</span><br>`;
                                }
                                
                                popupContent += `<hr style="margin: 8px 0;">`;
                                
                                // Market Indicators
                                popupContent += `<strong style="color: #17a2b8;">📊 Market Indicators:</strong><br>`;
                                
                                // Literacy Rate with emoji indicator
                                if (districtData.literacy_rate !== null && districtData.literacy_rate !== undefined) {
                                    const literacyEmoji = districtData.literacy_rate >= 80 ? '🟢' : 
                                                        districtData.literacy_rate >= 70 ? '🟡' : 
                                                        districtData.literacy_rate >= 60 ? '🟠' : '🔴';
                                    popupContent += `• Literacy Rate: ${districtData.literacy_rate}% ${literacyEmoji}<br>`;
                                }
                                
                                if (districtData.employment_rate) {
                                    popupContent += `• Employment Rate: ${districtData.employment_rate}%<br>`;
                                }
                                
                                if (districtData.population_density) {
                                    popupContent += `• Population Density: ${parseFloat(districtData.population_density).toFixed(1)}/km²<br>`;
                                }
                                
                                // Economic Indicators (if available)
                                if (districtData.avg_income || districtData.avg_spending) {
                                    popupContent += `<hr style="margin: 8px 0;">`;
                                    popupContent += `<strong style="color: #28a745;">💼 Economic Indicators:</strong><br>`;
                                    
                                    if (districtData.avg_income) {
                                        popupContent += `• Avg Income: ₹${parseInt(districtData.avg_income).toLocaleString()}<br>`;
                                    }
                                    if (districtData.avg_spending) {
                                        popupContent += `• Avg Spending: ₹${parseInt(districtData.avg_spending).toLocaleString()}<br>`;
                                    }
                                }
                                
                                popupContent += `<hr style="margin: 8px 0;">`;
                                
                                // Market Assessment
                                const marketAssessment = 
                                    districtData.literacy_rate >= 80 && districtData.employment_rate >= 70 
                                        ? '<span style="color: #28a745;">✅ Strong market potential</span>' 
                                        : districtData.literacy_rate >= 70 
                                        ? '<span style="color: #ffc107;">⚠️ Moderate market potential</span>' 
                                        : '<span style="color: #dc3545;">❌ Challenging market</span>';
                                
                                popupContent += `<em>${marketAssessment}</em>`;
                                
                            } else {
                                popupContent += '<i style="color: #999;">No data available</i>';
                            }
                        }
                        
                        popupContent += '</div>';
                        layer.bindPopup(popupContent, {
                            maxWidth: 350,
                            className: 'custom-popup'
                        });
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