class GeoReachMap {
    constructor(mapElementId, config, stateMetrics, districtMetrics, matchScores) {
        this.mapConfig = config;
        this.stateMetrics = stateMetrics || {};
        this.districtMetrics = districtMetrics || {};
        this.matchScores = matchScores || {};
        this.map = L.map(mapElementId).setView([config.center_lat, config.center_lng], config.initial_zoom);
        this.geojsonLayerCache = {};
        this.currentLayer = null;
        this.currentZoomLevel = null;
        
        console.log("🗺️ Map initialized with:", {
            matchScores: Object.keys(this.matchScores).length,
            states: Object.keys(this.stateMetrics).length,
            districts: Object.keys(this.districtMetrics).length
        });

        this.currentTheme = 'light'; 
        this.baseLayers = {};
        this.initBaseMaps();
        // this.addThemeSelector();
        this.setupControlPanel();
        this.setupBoundaryLayers();

        document.getElementById(mapElementId).addEventListener('contextmenu', function(e) {
            e.preventDefault();
        });
    }

    initBaseMaps() {

        // Streets (OSM default)
        this.baseLayers['Streets'] = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: this.mapConfig.max_zoom
        });

        // Light theme (CartoDB Positron)
        this.baseLayers['Light'] = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
            maxZoom: this.mapConfig.max_zoom
        });

        // Dark theme
        this.baseLayers['Dark'] = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
            maxZoom: this.mapConfig.max_zoom
        });

        // Satellite theme
        this.baseLayers['Satellite'] = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri',
            maxZoom: this.mapConfig.max_zoom
        });

        // Add default layer
        this.baseLayers['Streets'].addTo(this.map);
    }

    // addThemeSelector() {
    //     // Add Leaflet layer control for theme switching
    //     L.control.layers(this.baseLayers, null, {
    //         position: 'bottomright',
    //         collapsed: false
    //     }).addTo(this.map);
    // }

    setBaseLayer(layerName) {
        // Remove all base layers
        Object.values(this.baseLayers).forEach(layer => {
            if (this.map.hasLayer(layer)) {
                this.map.removeLayer(layer);
            }
        });
        // Add selected layer
        const selected = this.baseLayers[layerName];
        if (selected) selected.addTo(this.map);
    }
    
    // ========================================
    // CONTROL PANEL SETUP
    // ========================================
    setupControlPanel() {
        // Create control panel toggle handler
        setTimeout(() => {
            const toggleBtn = document.getElementById('toggle-panel');
            const controlContent = document.getElementById('control-content');
            
            if (toggleBtn && controlContent) {
                toggleBtn.addEventListener('click', () => {
                    controlContent.classList.toggle('hidden');
                });

                // Setup filter handlers
                this.setupFilterHandlers();
            }
        }, 500); // Wait for DOM to be ready
    }

    setupFilterHandlers() {
        // Price filter
        const priceMin = document.getElementById('filter-price-min');
        const priceMax = document.getElementById('filter-price-max');
        
        // Category filter
        const categoryFilter = document.getElementById('filter-category');
        
        // Audience filter
        const audienceFilter = document.getElementById('filter-audience');
        
        // Layer toggles
        const toggleSuccess = document.getElementById('toggle-success');
        const toggleLiteracy = document.getElementById('toggle-literacy');
        const toggleDensity = document.getElementById('toggle-density');

        // Apply filters button
        const applyFiltersBtn = document.getElementById('apply-filters');
        
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => {
                const filters = {
                    priceMin: priceMin ? parseFloat(priceMin.value) || 0 : 0,
                    priceMax: priceMax ? parseFloat(priceMax.value) || Infinity : Infinity,
                    category: categoryFilter ? categoryFilter.value : 'all',
                    audience: audienceFilter ? audienceFilter.value : 'all',
                    showSuccess: toggleSuccess ? toggleSuccess.checked : true,
                    showLiteracy: toggleLiteracy ? toggleLiteracy.checked : true,
                    showDensity: toggleDensity ? toggleDensity.checked : true
                };
                
                this.applyFilters(filters);
                this.showToast('Filters applied successfully', 'success');
            });
        }

        // Reset filters button
        const resetFiltersBtn = document.getElementById('reset-filters');
        if (resetFiltersBtn) {
            resetFiltersBtn.addEventListener('click', () => {
                if (priceMin) priceMin.value = '';
                if (priceMax) priceMax.value = '';
                if (categoryFilter) categoryFilter.value = 'all';
                if (audienceFilter) audienceFilter.value = 'all';
                if (toggleSuccess) toggleSuccess.checked = true;
                if (toggleLiteracy) toggleLiteracy.checked = true;
                if (toggleDensity) toggleDensity.checked = true;
                
                this.applyFilters({
                    priceMin: 0,
                    priceMax: Infinity,
                    category: 'all',
                    audience: 'all',
                    showSuccess: true,
                    showLiteracy: true,
                    showDensity: true
                });
                
                this.showToast('Filters reset', 'info');
            });
        }
    }

    applyFilters(filters) {
        console.log('Applying filters:', filters);
        
        // Filter the displayed regions based on criteria
        if (this.currentLayer) {
            this.currentLayer.eachLayer((layer) => {
                const name = layer.feature.properties.shapeName || 
                            layer.feature.properties.shapeGroup ||
                            layer.feature.properties.DISTRICT || 
                            layer.feature.properties.NAME_1;
                
                const isStateLevel = this.currentZoomLevel === 'state';
                const regionData = isStateLevel ? this.stateMetrics[name] : this.districtMetrics[name];
                
                if (!regionData) {
                    layer.setStyle({ fillOpacity: 0.1 });
                    return;
                }

                // Check if region passes filters
                let passes = true;
                
                // Price filter (if avg_income exists)
                if (regionData.avg_income) {
                    if (regionData.avg_income < filters.priceMin || regionData.avg_income > filters.priceMax) {
                        passes = false;
                    }
                }

                // Category filter (placeholder - you can add product_type matching)
                // if (filters.category !== 'all') {
                //     // Add logic to match against prediction data
                // }

                // Update layer visibility/opacity
                if (passes) {
                    // Determine which metric to show based on toggles
                    let fillColor = '#ADD8E6';
                    
                    if (filters.showSuccess && regionData.avg_predicted_success) {
                        fillColor = this.getColorByScore(regionData.avg_predicted_success * 100);
                    } else if (filters.showLiteracy && regionData.literacy_rate) {
                        fillColor = this.getColorByScore(regionData.literacy_rate);
                    } else if (filters.showDensity && regionData.population_density) {
                        // Normalize density to 0-100 scale for coloring
                        const normalizedDensity = Math.min(regionData.population_density / 10, 100);
                        fillColor = this.getColorByScore(normalizedDensity);
                    }
                    
                    layer.setStyle({
                        fillOpacity: 0.6,
                        fillColor: fillColor
                    });
                } else {
                    // Dim regions that don't pass filters
                    layer.setStyle({
                        fillOpacity: 0.15,
                        fillColor: '#cccccc'
                    });
                }
            });
        }
    }

    /**
     * Get color based on match score (0-100)
     */
    getColorByScore(score) {
        if (score === null || score === undefined || score === 0) return '#ADD8E6';
        if (score >= 70) return '#28a745';
        if (score >= 50) return '#ffc107';
        if (score >= 30) return '#fd7e14';
        return '#dc3545';
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
    // ========================================
    // CONTEXT MENU ACTION METHODS
    // ========================================
    
    viewDetailedInsights(regionName, regionType) {
        console.log('View insights:', regionName, regionType);
        
        // Get region data
        const regionData = regionType === 'state' 
            ? this.stateMetrics[regionName] 
            : this.districtMetrics[regionName];
        
        if (!regionData) {
            this.showToast(`No detailed data available for ${regionName}`, 'warning');
            return;
        }

        // Create detailed modal/popup content
        const detailsHtml = this.generateDetailedInsightsHtml(regionName, regionData, regionType);
        
        // Show in a Bootstrap modal
        this.showModal('Detailed Insights: ' + regionName, detailsHtml);
    }

    compareRegion(regionName) {
        console.log('Compare region:', regionName);
        
        // Determine if it's state or district
        const isState = this.stateMetrics.hasOwnProperty(regionName);
        const regionType = isState ? 'state' : 'district';
        
        // Get neighboring regions using spatial analysis
        const neighbors = this.getNeighboringRegions(regionName, regionType);
        
        if (neighbors.length === 0) {
            this.showToast(`No neighboring regions found for ${regionName}`, 'info');
            return;
        }

        // Get current region data
        const currentData = isState ? this.stateMetrics[regionName] : this.districtMetrics[regionName];
        
        // Create comparison content
        const comparisonHtml = this.generateComparisonHtml(regionName, currentData, neighbors, regionType);
        
        // Show comparison
        this.showModal('Compare ' + regionName + ' with Neighbors', comparisonHtml);
    }

    viewChartForRegion(regionName) {
        console.log('View charts for:', regionName);
        
        // Smooth scroll to charts section
        const chartsSection = document.querySelector('.row.mt-4');
        if (chartsSection) {
            chartsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            
            // Show notification with region name
            this.highlightRegionInCharts(regionName);
            
            // Optional: Filter charts to show only this region's data
            // You can emit a custom event that your charts listen to
            const event = new CustomEvent('regionSelected', { 
                detail: { regionName: regionName } 
            });
            document.dispatchEvent(event);
        } else {
            this.showToast('Charts section not found', 'warning');
        }
    }

    centerAndZoom(lat, lng, zoomLevel = 8) {
        this.map.setView([lat, lng], zoomLevel, {
            animate: true,
            duration: 1.0
        });
        
        // Show subtle animation
        this.showToast('Map centered', 'success');
    }

    // ========================================
    // HELPER METHODS
    // ========================================

    generateDetailedInsightsHtml(regionName, regionData, regionType) {
        // Calculate market score
        let marketScore = 0;
        let scoreFactors = [];
        
        if (regionData.avg_predicted_success) {
            marketScore += regionData.avg_predicted_success * 40;
            scoreFactors.push(`Predicted Success: ${(regionData.avg_predicted_success * 100).toFixed(1)}%`);
        }
        if (regionData.literacy_rate) {
            marketScore += (regionData.literacy_rate / 100) * 30;
            scoreFactors.push(`Literacy: ${regionData.literacy_rate}%`);
        }
        if (regionData.employment_rate) {
            marketScore += (regionData.employment_rate / 100) * 30;
            scoreFactors.push(`Employment: ${regionData.employment_rate}%`);
        }
        
        const scoreColor = this.getColorByScore(marketScore);
        
        return `
            <div style="font-family: Arial, sans-serif;">
                <!-- Header with Score -->
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin: 0;">${regionName}</h3>
                    <p style="margin: 5px 0; opacity: 0.9; text-transform: capitalize;">${regionType}</p>
                    <div style="font-size: 48px; font-weight: bold; margin: 10px 0;">${marketScore.toFixed(0)}</div>
                    <div style="opacity: 0.9;">Market Potential Score</div>
                </div>
                
                <!-- Key Metrics Grid -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">PREDICTED SUCCESS</div>
                        <div style="font-size: 24px; font-weight: bold; color: ${scoreColor};">
                            ${regionData.avg_predicted_success ? (regionData.avg_predicted_success * 100).toFixed(1) + '%' : 'N/A'}
                        </div>
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">CONFIDENCE</div>
                        <div style="font-size: 24px; font-weight: bold; color: ${regionData.confidence_score >= 0.7 ? '#28a745' : regionData.confidence_score >= 0.5 ? '#ffc107' : '#dc3545'};">
                            ${regionData.confidence_score ? (regionData.confidence_score * 100).toFixed(0) + '%' : 'N/A'}
                        </div>
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">SPENDING INDEX</div>
                        <div style="font-size: 24px; font-weight: bold;">
                            ${regionData.spending_index ? (regionData.spending_index * 100).toFixed(1) + '%' : 'N/A'}
                        </div>
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 12px; color: #6c757d; margin-bottom: 5px;">LITERACY RATE</div>
                        <div style="font-size: 24px; font-weight: bold;">
                            ${regionData.literacy_rate ? regionData.literacy_rate + '%' : 'N/A'}
                        </div>
                    </div>
                </div>

                <!-- Detailed Tables -->
                <h5 style="color: #17a2b8; border-bottom: 2px solid #17a2b8; padding-bottom: 5px;">💼 Economic Indicators</h5>
                <table class="table table-sm table-hover">
                    <tbody>
                        <tr>
                            <td><strong>Average Income</strong></td>
                            <td class="text-end">₹${regionData.avg_income ? parseInt(regionData.avg_income).toLocaleString() : 'N/A'}</td>
                        </tr>
                        <tr>
                            <td><strong>Average Spending</strong></td>
                            <td class="text-end">₹${regionData.avg_spending ? parseInt(regionData.avg_spending).toLocaleString() : 'N/A'}</td>
                        </tr>
                        <tr>
                            <td><strong>Employment Rate</strong></td>
                            <td class="text-end">${regionData.employment_rate ? regionData.employment_rate + '%' : 'N/A'}</td>
                        </tr>
                        ${regionData.avg_income && regionData.avg_spending ? `
                        <tr style="background: #e7f3ff;">
                            <td><strong>Savings Rate</strong></td>
                            <td class="text-end">${((1 - regionData.avg_spending / regionData.avg_income) * 100).toFixed(1)}%</td>
                        </tr>
                        ` : ''}
                    </tbody>
                </table>

                <h5 style="color: #6c757d; border-bottom: 2px solid #6c757d; padding-bottom: 5px; margin-top: 20px;">📍 Demographics</h5>
                <table class="table table-sm table-hover">
                    <tbody>
                        <tr>
                            <td><strong>Population Density</strong></td>
                            <td class="text-end">${regionData.population_density ? parseFloat(regionData.population_density).toFixed(1) + ' /km²' : 'N/A'}</td>
                        </tr>
                        <tr>
                            <td><strong>Literacy Rate</strong></td>
                            <td class="text-end">${regionData.literacy_rate ? regionData.literacy_rate + '%' : 'N/A'}</td>
                        </tr>
                    </tbody>
                </table>

                ${regionData.top_drivers && regionData.top_drivers.length > 0 ? `
                <h5 style="color: #28a745; border-bottom: 2px solid #28a745; padding-bottom: 5px; margin-top: 20px;">🎯 Success Drivers</h5>
                <div style="margin-top: 10px;">
                    ${regionData.top_drivers.map(driver => `
                        <div style="margin-bottom: 10px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                <span><strong>${driver.feature}</strong></span>
                                <span>${(driver.weight * 100).toFixed(0)}%</span>
                            </div>
                            <div style="background: #e9ecef; height: 8px; border-radius: 4px; overflow: hidden;">
                                <div style="background: linear-gradient(90deg, #28a745, #20c997); height: 100%; width: ${(driver.weight * 100).toFixed(0)}%; transition: width 0.3s;"></div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                ` : ''}

                <!-- Market Assessment -->
                <div style="margin-top: 20px; padding: 15px; background: ${marketScore >= 70 ? '#d4edda' : marketScore >= 50 ? '#fff3cd' : '#f8d7da'}; border-left: 4px solid ${marketScore >= 70 ? '#28a745' : marketScore >= 50 ? '#ffc107' : '#dc3545'}; border-radius: 4px;">
                    <strong style="color: ${marketScore >= 70 ? '#155724' : marketScore >= 50 ? '#856404' : '#721c24'};">
                        ${marketScore >= 70 ? '✅ Excellent Market' : marketScore >= 50 ? '⚠️ Moderate Market' : '❌ Challenging Market'}
                    </strong>
                    <p style="margin: 5px 0 0 0; font-size: 13px; color: #6c757d;">
                        Based on: ${scoreFactors.join(', ')}
                    </p>
                </div>
            </div>
        `;
    }

    generateComparisonHtml(regionName, currentData, neighbors, regionType) {
        // Calculate averages for comparison
        const neighborData = neighbors.map(n => {
            const data = regionType === 'state' ? this.stateMetrics[n.name] : this.districtMetrics[n.name];
            return { name: n.name, data: data, distance: n.distance };
        }).filter(n => n.data); // Only include neighbors with data

        const avgLiteracy = neighborData.length > 0 
            ? neighborData.reduce((sum, n) => sum + (n.data.literacy_rate || 0), 0) / neighborData.length 
            : 0;
        
        const avgEmployment = neighborData.length > 0 
            ? neighborData.reduce((sum, n) => sum + (n.data.employment_rate || 0), 0) / neighborData.length 
            : 0;

        return `
            <div style="font-family: Arial, sans-serif;">
                <!-- Comparison Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h4 style="margin: 0;">Regional Comparison Analysis</h4>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Comparing ${regionName} with ${neighborData.length} neighboring ${regionType}s</p>
                </div>

                <!-- Quick Stats Comparison -->
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 20px;">
                    <div style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 8px;">
                        <div style="font-size: 11px; color: #6c757d;">YOUR REGION</div>
                        <div style="font-size: 20px; font-weight: bold; color: #667eea;">${regionName}</div>
                    </div>
                    <div style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 8px;">
                        <div style="font-size: 11px; color: #6c757d;">LITERACY RATE</div>
                        <div style="font-size: 20px; font-weight: bold;">
                            ${currentData.literacy_rate || 'N/A'}
                            ${currentData.literacy_rate && avgLiteracy ? `
                                <span style="font-size: 12px; color: ${currentData.literacy_rate > avgLiteracy ? '#28a745' : '#dc3545'};">
                                    ${currentData.literacy_rate > avgLiteracy ? '▲' : '▼'} ${Math.abs(currentData.literacy_rate - avgLiteracy).toFixed(1)}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                    <div style="text-align: center; padding: 10px; background: #f8f9fa; border-radius: 8px;">
                        <div style="font-size: 11px; color: #6c757d;">EMPLOYMENT RATE</div>
                        <div style="font-size: 20px; font-weight: bold;">
                            ${currentData.employment_rate || 'N/A'}
                            ${currentData.employment_rate && avgEmployment ? `
                                <span style="font-size: 12px; color: ${currentData.employment_rate > avgEmployment ? '#28a745' : '#dc3545'};">
                                    ${currentData.employment_rate > avgEmployment ? '▲' : '▼'} ${Math.abs(currentData.employment_rate - avgEmployment).toFixed(1)}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                </div>

                <!-- Detailed Comparison Table -->
                <h5 style="color: #17a2b8; border-bottom: 2px solid #17a2b8; padding-bottom: 5px;">Neighboring Regions</h5>
                <div style="max-height: 300px; overflow-y: auto;">
                    <table class="table table-sm table-hover">
                        <thead style="position: sticky; top: 0; background: white;">
                            <tr>
                                <th>Region</th>
                                <th class="text-center">Literacy</th>
                                <th class="text-center">Employment</th>
                                <th class="text-center">Pop. Density</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${neighborData.map(neighbor => {
                                const literacyDiff = currentData.literacy_rate && neighbor.data.literacy_rate 
                                    ? (neighbor.data.literacy_rate - currentData.literacy_rate).toFixed(1) 
                                    : null;
                                const empDiff = currentData.employment_rate && neighbor.data.employment_rate 
                                    ? (neighbor.data.employment_rate - currentData.employment_rate).toFixed(1) 
                                    : null;
                                
                                return `
                                    <tr style="cursor: pointer;" onclick="georearchMap.highlightRegionOnMap('${neighbor.name}')">
                                        <td>
                                            <strong>${neighbor.name}</strong>
                                            <br><small class="text-muted">~${neighbor.distance.toFixed(0)}km away</small>
                                        </td>
                                        <td class="text-center">
                                            ${neighbor.data.literacy_rate || 'N/A'}
                                            ${literacyDiff ? `<br><small style="color: ${literacyDiff > 0 ? '#28a745' : '#dc3545'};">${literacyDiff > 0 ? '+' : ''}${literacyDiff}</small>` : ''}
                                        </td>
                                        <td class="text-center">
                                            ${neighbor.data.employment_rate || 'N/A'}
                                            ${empDiff ? `<br><small style="color: ${empDiff > 0 ? '#28a745' : '#dc3545'};">${empDiff > 0 ? '+' : ''}${empDiff}</small>` : ''}
                                        </td>
                                        <td class="text-center">
                                            ${neighbor.data.population_density ? parseFloat(neighbor.data.population_density).toFixed(0) : 'N/A'}
                                        </td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>

                <!-- Regional Average Summary -->
                <div style="margin-top: 20px; padding: 15px; background: #e7f3ff; border-radius: 8px;">
                    <h6 style="margin: 0 0 10px 0;">📊 Regional Averages</h6>
                    <div style="display: flex; justify-content: space-around;">
                        <div style="text-align: center;">
                            <div style="font-size: 11px; color: #6c757d;">AVG LITERACY</div>
                            <div style="font-size: 18px; font-weight: bold;">${avgLiteracy.toFixed(1)}%</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 11px; color: #6c757d;">AVG EMPLOYMENT</div>
                            <div style="font-size: 18px; font-weight: bold;">${avgEmployment.toFixed(1)}%</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 11px; color: #6c757d;">RANK</div>
                            <div style="font-size: 18px; font-weight: bold;">
                                ${this.calculateRank(currentData, neighborData)}/${neighborData.length + 1}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Competitive Analysis -->
                <div style="margin-top: 15px; padding: 15px; background: ${currentData.literacy_rate > avgLiteracy && currentData.employment_rate > avgEmployment ? '#d4edda' : '#fff3cd'}; border-radius: 8px;">
                    <strong style="color: ${currentData.literacy_rate > avgLiteracy && currentData.employment_rate > avgEmployment ? '#155724' : '#856404'};">
                        ${currentData.literacy_rate > avgLiteracy && currentData.employment_rate > avgEmployment 
                            ? '🏆 Above Regional Average' 
                            : '📈 Growth Potential Area'}
                    </strong>
                    <p style="margin: 5px 0 0 0; font-size: 13px; color: #6c757d;">
                        ${currentData.literacy_rate > avgLiteracy && currentData.employment_rate > avgEmployment 
                            ? 'This region performs better than neighboring areas in key metrics.' 
                            : 'Consider strategies from higher-performing neighboring regions.'}
                    </p>
                </div>
            </div>
        `;
    }

    calculateRank(currentData, neighborData) {
        const score = (currentData.literacy_rate || 0) + (currentData.employment_rate || 0);
        const allScores = neighborData.map(n => (n.data.literacy_rate || 0) + (n.data.employment_rate || 0));
        allScores.push(score);
        allScores.sort((a, b) => b - a);
        return allScores.indexOf(score) + 1;
    }

    getNeighboringRegions(regionName, regionType) {
        // Get the feature collection for the appropriate level
        const features = regionType === 'state' ? this.stateFeatures : this.districtFeatures;
        
        if (!features || Object.keys(features).length === 0) {
            console.warn('Features not loaded yet for neighbor detection');
            return [];
        }

        const targetFeature = features[regionName];
        if (!targetFeature) {
            console.warn(`Feature not found for ${regionName}`);
            return [];
        }

        // Calculate centroid of target region
        const targetCentroid = this.calculateCentroid(targetFeature.geometry);
        
        // Find neighbors by checking distance to centroids
        const neighbors = [];
        for (const [name, feature] of Object.entries(features)) {
            if (name === regionName) continue; // Skip self
            
            const centroid = this.calculateCentroid(feature.geometry);
            const distance = this.calculateDistance(targetCentroid, centroid);
            
            // Consider as neighbor if within reasonable distance
            // For states: within 500km, for districts: within 200km
            const maxDistance = regionType === 'state' ? 500 : 200;
            
            if (distance < maxDistance) {
                neighbors.push({ name, distance, feature });
            }
        }
        
        // Sort by distance and return top 5
        return neighbors.sort((a, b) => a.distance - b.distance).slice(0, 5);
    }

    calculateCentroid(geometry) {
        // Simple centroid calculation for polygons
        if (geometry.type === 'Polygon') {
            const coords = geometry.coordinates[0];
            const sum = coords.reduce((acc, coord) => {
                return [acc[0] + coord[0], acc[1] + coord[1]];
            }, [0, 0]);
            return [sum[0] / coords.length, sum[1] / coords.length];
        } else if (geometry.type === 'MultiPolygon') {
            // Use first polygon's centroid for simplicity
            const coords = geometry.coordinates[0][0];
            const sum = coords.reduce((acc, coord) => {
                return [acc[0] + coord[0], acc[1] + coord[1]];
            }, [0, 0]);
            return [sum[0] / coords.length, sum[1] / coords.length];
        }
        return [0, 0];
    }

    calculateDistance(coord1, coord2) {
        // Haversine formula for distance between two lat/lng points
        const R = 6371; // Earth's radius in km
        const dLat = this.toRad(coord2[1] - coord1[1]);
        const dLon = this.toRad(coord2[0] - coord1[0]);
        const lat1 = this.toRad(coord1[1]);
        const lat2 = this.toRad(coord2[1]);

        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.sin(dLon/2) * Math.sin(dLon/2) * Math.cos(lat1) * Math.cos(lat2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    toRad(degrees) {
        return degrees * Math.PI / 180;
    }

    highlightRegionOnMap(regionName) {
        console.log('Highlighting region on map:', regionName);
        
        // Find the layer and highlight it temporarily
        if (this.currentLayer) {
            this.currentLayer.eachLayer((layer) => {
                const name = layer.feature.properties.shapeName || 
                            layer.feature.properties.shapeGroup ||
                            layer.feature.properties.DISTRICT || 
                            layer.feature.properties.NAME_1;
                
                if (name === regionName) {
                    // Highlight the region
                    layer.setStyle({
                        weight: 4,
                        color: '#FF5722',
                        fillOpacity: 0.8
                    });
                    
                    // Center on the region
                    const bounds = layer.getBounds();
                    this.map.fitBounds(bounds);
                    
                    // Reset style after 2 seconds
                    setTimeout(() => {
                        layer.setStyle({
                            weight: 1.5,
                            color: "#2196F3",
                            fillOpacity: 0.6
                        });
                    }, 2000);
                    
                    // Open popup
                    layer.openPopup();
                }
            });
        }
    }

    highlightRegionInCharts(regionName) {
        console.log('Highlighting region in charts:', regionName);
        
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = 'alert alert-info position-fixed';
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; box-shadow: 0 4px 12px rgba(0,0,0,0.3); animation: slideIn 0.3s ease-out;';
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-info-circle" style="font-size: 20px;"></i>
                <div>
                    <strong>Viewing charts for:</strong><br>
                    <span style="font-size: 14px;">${regionName}</span>
                </div>
            </div>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    showModal(title, content) {
        // Create Bootstrap modal dynamically
        const modalHtml = `
            <div class="modal fade" id="regionModal" tabindex="-1">
                <div class="modal-dialog modal-xl modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="bi bi-graph-up-arrow me-2"></i>${title}
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${content}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="bi bi-x-circle me-2"></i>Close
                            </button>
                            <button type="button" class="btn btn-primary" onclick="window.print()">
                                <i class="bi bi-printer me-2"></i>Print Report
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('regionModal');
        if (existingModal) {
            const bootstrapModal = bootstrap.Modal.getInstance(existingModal);
            if (bootstrapModal) {
                bootstrapModal.dispose();
            }
            existingModal.remove();
        }
        
        // Add new modal
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('regionModal'));
        modal.show();
    }

    showToast(message, type = 'info') {
        const bgColors = {
            'success': '#28a745',
            'warning': '#ffc107',
            'info': '#17a2b8',
            'danger': '#dc3545'
        };
        
        const icons = {
            'success': 'bi-check-circle',
            'warning': 'bi-exclamation-triangle',
            'info': 'bi-info-circle',
            'danger': 'bi-x-circle'
        };
        
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            background: ${bgColors[type]};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: slideInUp 0.3s ease-out;
            display: flex;
            align-items: center;
            gap: 10px;
        `;
        toast.innerHTML = `
            <i class="bi ${icons[type]}" style="font-size: 18px;"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
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

        const loadingSpinner = document.createElement('div');
        loadingSpinner.id = 'map-loading';
        loadingSpinner.innerHTML = `
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 2000; background: rgba(255,255,255,0.9); padding: 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
                <div class="spinner-border text-primary" role="status">
                    <span class="sr-only">Loading...</span>
                </div>
                <div style="margin-top: 10px;">Loading ${isStateLevel ? 'states' : 'districts'}...</div>
            </div>
        `;
        document.getElementById('map').appendChild(loadingSpinner);
        
        fetch(`/static/${geojsonFile}`)
            .then(response => {
                // Remove spinner
                document.getElementById('map-loading')?.remove();
                
                // ...rest of existing code...
            })
            .catch(error => {
                document.getElementById('map-loading')?.remove();
                // ...existing error handling...
            });
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
                        
                        // === Hover ToolTip ===
                        let tooltipContent = `<b>${name}</b>`;
                        
                        if (isStateLevel) {
                            const stateData = this.stateMetrics[name];
                            if (stateData) {
                                if (stateData.avg_predicted_success) {
                                    tooltipContent += `<br>Success: ${(stateData.avg_predicted_success * 100).toFixed(1)}%`;
                                }
                                if (stateData.confidence_score) {
                                    const confidence = stateData.confidence_score >= 0.7 ? 'High' : 
                                                    stateData.confidence_score >= 0.5 ? 'Medium' : 'Low';
                                    tooltipContent += `<br>Confidence: ${confidence}`;
                                }
                                if (stateData.literacy_rate) {
                                    tooltipContent += `<br>Literacy: ${stateData.literacy_rate}%`;
                                }
                            }
                        } else {
                            const districtData = this.districtMetrics[name];
                            if (districtData && districtData.literacy_rate) {
                                tooltipContent += `<br>Literacy: ${districtData.literacy_rate}%`;
                                if (districtData.employment_rate) {
                                    tooltipContent += `<br>Employment: ${districtData.employment_rate}%`;
                                }
                            }
                        }
                        
                        layer.bindTooltip(tooltipContent, {
                            sticky: true,
                            direction: 'top',
                            className: 'custom-tooltip'
                        });

                        // Right-click context menu
                        layer.on('contextmenu', (e) => {
                            if (e.originalEvent) {
                                e.originalEvent.preventDefault();
                            }

                            L.popup()
                                .setLatLng(e.latlng)
                                .setContent(`
                                    <div style="font-family: Arial; min-width: 180px;">
                                        <b>${name}</b>
                                        <hr style="margin: 5px 0;">
                                        <button onclick="georearchMap.viewDetailedInsights('${name}', '${isStateLevel ? 'state' : 'district'}')" 
                                                style="width: 100%; margin: 3px 0; padding: 5px; cursor: pointer; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px;">
                                            🧾 View Detailed Insights
                                        </button>
                                        <button onclick="georearchMap.compareRegion('${name}')" 
                                                style="width: 100%; margin: 3px 0; padding: 5px; cursor: pointer; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px;">
                                            💬 Compare with Neighbors
                                        </button>
                                        <button onclick="georearchMap.viewChartForRegion('${name}')" 
                                                style="width: 100%; margin: 3px 0; padding: 5px; cursor: pointer; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px;">
                                            📊 View Charts
                                        </button>
                                        <button onclick="georearchMap.centerAndZoom(${e.latlng.lat}, ${e.latlng.lng}, 8)" 
                                                style="width: 100%; margin: 3px 0; padding: 5px; cursor: pointer; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px;">
                                            📍 Center & Zoom Here
                                        </button>
                                    </div>
                                `)
                                .openOn(this.map);
                            
                            L.DomEvent.stopPropagation(e);
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

                        // === Context Menu on Right-Click ===
                        layer.on('contextmenu', (e) => {
                            L.popup()
                                .setLatLng(e.latlng)
                                .setContent(`
                                    <div style="font-family: Arial; min-width: 180px;">
                                        <b>${name}</b>
                                        <hr style="margin: 5px 0;">
                                        <button onclick="viewDetailedInsights('${name}', '${isStateLevel ? 'state' : 'district'}')" 
                                                style="width: 100%; margin: 3px 0; padding: 5px; cursor: pointer; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px;">
                                            🧾 View Detailed Insights
                                        </button>
                                        <button onclick="compareRegion('${name}')" 
                                                style="width: 100%; margin: 3px 0; padding: 5px; cursor: pointer; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px;">
                                            💬 Compare with Neighbors
                                        </button>
                                        <button onclick="viewChartForRegion('${name}')" 
                                                style="width: 100%; margin: 3px 0; padding: 5px; cursor: pointer; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px;">
                                            📊 View Charts
                                        </button>
                                        <button onclick="georearchMap.map.setView([${e.latlng.lat}, ${e.latlng.lng}], 8)" 
                                                style="width: 100%; margin: 3px 0; padding: 5px; cursor: pointer; border: 1px solid #ddd; background: #f8f9fa; border-radius: 4px;">
                                            📍 Center & Zoom Here
                                        </button>
                                    </div>
                                `)
                                .openOn(this.map);
                            
                            L.DomEvent.stopPropagation(e);
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