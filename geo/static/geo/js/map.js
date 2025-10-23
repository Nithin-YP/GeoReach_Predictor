class GeoReachMap {
    constructor(mapElementId, config, clusters) {
        console.log('GeoReachMap constructor called');

        this.mapConfig = config;
        this.clusters = clusters;
        this.map = L.map(mapElementId).setView([config.center_lat, config.center_lng], config.initial_zoom);
        this.geojsonDataCache = {};
        this.geojsonLayerCache = {};
        this.currentLayer = null;
        this.contextMenu = null;
        this.selectedFeature = null;
        this.loadingOverlay = document.getElementById('mapLoadingOverlay');
        
        this.initBaseMaps();
        this.addClusters();
        this.setupBoundaryLayers();
        this.initContextMenu();
        this.setupMapEventListeners();

        console.log('GeoReachMap initialized');
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
        if (zoom < this.mapConfig.zoom_thresholds.state_to_district) {
            return '/geo/api/states/geojson/';
        } else {
            return '/geo/api/districts/geojson/';
        }
    }

    initContextMenu() {
        console.log('initContextMenu() called');
        
        // Create context menu element
        this.contextMenu = document.createElement('div');
        this.contextMenu.className = 'geo-context-menu';
        this.contextMenu.innerHTML = `
            <div class="context-menu-header">
                <h4 class="context-menu-title" id="contextMenuTitle">Loading...</h4>
                <p class="context-menu-subtitle" id="contextMenuSubtitle"></p>
            </div>
            <button class="context-menu-item" data-action="view-details">
                <i class="bi bi-info-circle"></i>
                <span>View Details</span>
            </button>
            <button class="context-menu-item" data-action="view-demographics">
                <i class="bi bi-people"></i>
                <span>Demographics</span>
            </button>
            <button class="context-menu-item" data-action="view-economic">
                <i class="bi bi-graph-up"></i>
                <span>Economic Indicators</span>
            </button>
            <div class="context-menu-divider"></div>
            <button class="context-menu-item" data-action="zoom-to">
                <i class="bi bi-zoom-in"></i>
                <span>Zoom to Boundary</span>
            </button>
            <button class="context-menu-item" data-action="export-data">
                <i class="bi bi-download"></i>
                <span>Export Data</span>
            </button>
            <div class="context-menu-divider"></div>
            <button class="context-menu-item" data-action="compare">
                <i class="bi bi-arrows-angle-expand"></i>
                <span>Compare with...</span>
            </button>
        `;
        
        document.body.appendChild(this.contextMenu);
        console.log('Context menu appended to body');

        // Add click handlers to menu items
        this.contextMenu.addEventListener('click', (e) => {
            const button = e.target.closest('.context-menu-item');
            if (!button) return;

            const action = button.dataset.action;
            this.handleContextMenuAction(action);
            this.hideContextMenu();
        });
    }

    setupMapEventListeners() {
        console.log('setupMapEventListeners() called');
        
        // Hide context menu on left click anywhere
        this.map.on('click', () => {
            this.hideContextMenu();
        });

        // Prevent default browser context menu on map
        this.map.getContainer().addEventListener('contextmenu', (e) => {
            e.preventDefault();
            
            // Only hide if not clicking on a feature
            if (!this.selectedFeature) {
                this.hideContextMenu();
            }
        });

        // Hide on scroll/zoom
        this.map.on('movestart zoomstart', () => {
            this.hideContextMenu();
        });

        // Hide on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideContextMenu();
            }
        });

        // Hide when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.contextMenu.contains(e.target)) {
                this.hideContextMenu();
            }
        });
    }

    showLoader(message = 'Loading boundaries...') {
        if (this.loadingOverlay) {
            const textElement = this.loadingOverlay.querySelector('.loading-text');
            if (textElement) {
                textElement.textContent = message;
            }
            this.loadingOverlay.classList.add('active');
        }
    }

    hideLoader() {
        if (this.loadingOverlay) {
            this.loadingOverlay.classList.remove('active');
        }
    }

    showGeoJsonLayer(zoom) {
        const apiEndpoint = this.getApiEndpoint(zoom);

        // Remove current layer first BEFORE checking cache
        if (this.currentLayer) {
            this.map.removeLayer(this.currentLayer);
            this.currentLayer = null;
        }

        // Don't show boundaries when zoomed too far OUT
        if (zoom < 4) {
            this.hideLoader();
            return;
        }

        // Use cached layer if available
        if (this.geojsonLayerCache[apiEndpoint]) {
            console.log('Using cached layer:', apiEndpoint);
            this.currentLayer = this.geojsonLayerCache[apiEndpoint];
            this.currentLayer.addTo(this.map);
            this.hideLoader();
            return;
        }

        const isStateLevel = apiEndpoint.includes('states');
        this.showLoader(isStateLevel ? 'Loading state boundaries...' : 'Loading district boundaries...');

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
                        // Mouseover effect
                        layer.on('mouseover', () => {
                            layer.setStyle({
                                fillColor: 'yellow',
                                fillOpacity: 0.5
                            });
                        });
                        
                        // Mouseout effect
                        layer.on('mouseout', () => {
                            layer.setStyle({
                                fillColor: isStateLevel ? "#2c7fb8" : "#3388ff",
                                fillOpacity: isStateLevel ? 0.15 : 0.2
                            });
                        });
                        
                        // Right-click context menu
                        layer.on('contextmenu', (e) => {
                            console.log('🖱️ Right-click detected on:', feature.properties.name);
                            L.DomEvent.preventDefault(e);
                            this.showContextMenu(e.originalEvent, feature, layer, isStateLevel);
                        });
                        
                        // Left-click popup (existing functionality)
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
                
                // Cache the layer
                this.geojsonLayerCache[apiEndpoint] = layer;
                
                // Only add to map if this is still the correct endpoint for current zoom
                const currentEndpoint = this.getApiEndpoint(this.map.getZoom());
                if (currentEndpoint === apiEndpoint) {
                    this.currentLayer = layer;
                    layer.addTo(this.map);
                }

                this.hideLoader();
            })
            .catch(error => {
                console.error('Error loading from PostGIS API:', error, 'Endpoint:', apiEndpoint);
                this.hideLoader();
            });
    }

    showContextMenu(event, feature, layer, isStateLevel) {
        console.log('showContextMenu called for:', feature.properties.name);
        
        // Store selected feature and layer
        this.selectedFeature = {
            feature: feature,
            layer: layer,
            isStateLevel: isStateLevel
        };

        // Update menu content
        const props = feature.properties;
        const name = props.name || "Unknown";
        const type = isStateLevel ? "State" : "District";
        const state = props.state ? ` • ${props.state}` : "";
        
        document.getElementById('contextMenuTitle').textContent = name;
        document.getElementById('contextMenuSubtitle').textContent = `${type}${state}`;

        // Position the menu
        const x = event.clientX;
        const y = event.clientY;
        
        this.contextMenu.style.left = `${x}px`;
        this.contextMenu.style.top = `${y}px`;
        
        // Show menu
        this.contextMenu.classList.add('active');

        // Adjust position if menu goes off-screen
        requestAnimationFrame(() => {
            const rect = this.contextMenu.getBoundingClientRect();
            
            if (rect.right > window.innerWidth) {
                this.contextMenu.style.left = `${x - rect.width}px`;
            }
            
            if (rect.bottom > window.innerHeight) {
                this.contextMenu.style.top = `${y - rect.height}px`;
            }
        });
    }

    hideContextMenu() {
        if (this.contextMenu) {
            this.contextMenu.classList.remove('active');
        }
        this.selectedFeature = null;
    }

    handleContextMenuAction(action) {
        if (!this.selectedFeature) return;

        const { feature, layer, isStateLevel } = this.selectedFeature;
        const props = feature.properties;

        console.log(`Action: ${action}`, props);

        switch (action) {
            case 'view-details':
                this.viewDetails(props, isStateLevel);
                break;
            case 'view-demographics':
                this.viewDemographics(props, isStateLevel);
                break;
            case 'view-economic':
                this.viewEconomicIndicators(props, isStateLevel);
                break;
            case 'zoom-to':
                this.zoomToBoundary(layer);
                break;
            case 'export-data':
                this.exportData(props, isStateLevel);
                break;
            case 'compare':
                this.compareWith(props, isStateLevel);
                break;
        }
    }

    viewDetails(props, isStateLevel) {
        const regionType = isStateLevel ? 'state' : 'district';
        const regionId = props.id;
        
        this.showLoader('Loading details...');
        
        fetch(`/geo/api/${regionType}/${regionId}/details/`)
            .then(response => response.json())
            .then(result => {
                this.hideLoader();
                
                if (result.success) {
                    this.showDetailsModal(result.data);
                } else {
                    alert(`Error: ${result.error}`);
                }
            })
            .catch(error => {
                this.hideLoader();
                console.error('Error fetching details:', error);
                alert('Failed to load details');
            });
    }

    viewDemographics(props, isStateLevel) {
        const regionType = isStateLevel ? 'state' : 'district';
        const regionId = props.id;
        
        this.showLoader('Loading demographics...');
        
        fetch(`/geo/api/${regionType}/${regionId}/demographics/`)
            .then(response => response.json())
            .then(result => {
                this.hideLoader();
                
                if (result.success) {
                    this.showDemographicsModal(result.data);
                } else {
                    alert(`Error: ${result.error}`);
                }
            })
            .catch(error => {
                this.hideLoader();
                console.error('Error fetching demographics:', error);
                alert('Failed to load demographics');
            });
    }

    viewEconomicIndicators(props, isStateLevel) {
        const regionType = isStateLevel ? 'state' : 'district';
        const regionId = props.id;
        
        this.showLoader('Loading economic data...');
        
        fetch(`/geo/api/${regionType}/${regionId}/economic/`)
            .then(response => response.json())
            .then(result => {
                this.hideLoader();
                
                if (result.success) {
                    this.showEconomicModal(result.data);
                } else {
                    alert(`Error: ${result.error}`);
                }
            })
            .catch(error => {
                this.hideLoader();
                console.error('Error fetching economic data:', error);
                alert('Failed to load economic indicators');
            });
    }

    zoomToBoundary(layer) {
        this.map.fitBounds(layer.getBounds(), {
            padding: [50, 50],
            maxZoom: 10
        });
    }

    exportData(props, isStateLevel) {
        const regionType = isStateLevel ? 'state' : 'district';
        const regionId = props.id;
        
        this.showLoader('Preparing export...');
        
        fetch(`/geo/api/${regionType}/${regionId}/export/`)
            .then(response => response.json())
            .then(result => {
                this.hideLoader();
                
                if (result.success) {
                    // Create downloadable JSON file
                    const dataStr = JSON.stringify(result.data, null, 2);
                    const dataBlob = new Blob([dataStr], { type: 'application/json' });
                    const url = URL.createObjectURL(dataBlob);
                    
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `${props.name.replace(/\s+/g, '_')}_data.json`;
                    link.click();
                    
                    URL.revokeObjectURL(url);
                } else {
                    alert(`Error: ${result.error}`);
                }
            })
            .catch(error => {
                this.hideLoader();
                console.error('Error exporting data:', error);
                alert('Failed to export data');
            });
    }

    compareWith(props, isStateLevel) {
        alert(`Compare feature coming soon!\nSelected: ${props.name}\n\nThis will allow you to select another region and compare demographics, economics, etc.`);
        // TODO: Implement comparison interface
    }

    // Helper methods to show modals with data
    showDetailsModal(data) {
        const content = `
            <div style="padding: 20px;">
                <h3>${data.name}</h3>
                <p><strong>Type:</strong> ${data.type}</p>
                ${data.code ? `<p><strong>Code:</strong> ${data.code}</p>` : ''}
                ${data.state ? `<p><strong>State:</strong> ${data.state}</p>` : ''}
                <p><strong>Population:</strong> ${(data.population || 0).toLocaleString()}</p>
                ${data.area_km2 ? `<p><strong>Area:</strong> ${data.area_km2.toLocaleString()} km²</p>` : ''}
                ${data.population_density ? `<p><strong>Density:</strong> ${data.population_density.toLocaleString()} per km²</p>` : ''}
                ${data.literacy_rate ? `<p><strong>Literacy Rate:</strong> ${data.literacy_rate}%</p>` : ''}
                ${data.district_count ? `<p><strong>Districts:</strong> ${data.district_count}</p>` : ''}
            </div>
        `;
        
        alert(content.replace(/<[^>]*>/g, '\n')); // Simple alert for now
        // TODO: Replace with Bootstrap modal
    }

    showDemographicsModal(data) {
        let content = `Demographics: ${data.name}\n\n`;
        content += `Type: ${data.type}\n`;
        if (data.state) content += `State: ${data.state}\n`;
        content += `Population: ${(data.population || 0).toLocaleString()}\n`;
        if (data.literacy_rate) content += `Literacy: ${data.literacy_rate}%\n`;
        if (data.sex_ratio) content += `Sex Ratio: ${data.sex_ratio}\n`;
        if (data.rural_percentage) content += `Rural: ${data.rural_percentage}%\n`;
        if (data.urban_percentage) content += `Urban: ${data.urban_percentage}%\n`;
        
        alert(content);
        // TODO: Replace with Bootstrap modal with charts
    }

    showEconomicModal(data) {
        let content = `Economic Indicators: ${data.name}\n\n`;
        
        const indicators = data.economic_indicators;
        if (indicators.employment_rate) content += `Employment Rate: ${indicators.employment_rate}%\n`;
        if (indicators.unemployment_rate) content += `Unemployment: ${indicators.unemployment_rate}%\n`;
        if (indicators.avg_monthly_salary) content += `Avg Salary: ₹${indicators.avg_monthly_salary.toLocaleString()}\n`;
        
        if (data.top_industries && data.top_industries.length > 0) {
            content += `\nTop Industries:\n`;
            data.top_industries.forEach((ind, i) => {
                content += `${i + 1}. ${ind.industry}: ${ind.employed.toLocaleString()} employed\n`;
            });
        }
        
        alert(content);
        // TODO: Replace with Bootstrap modal with charts
    }
}