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

    getGeoJsonFile(zoom) {
        if (zoom < this.mapConfig.zoom_thresholds.state_to_district) {
            return this.mapConfig.geojson_paths.adm1;
        } else {
            return this.mapConfig.geojson_paths.adm2;
        }
    }

    showGeoJsonLayer(zoom) {
        const geojsonFile = this.getGeoJsonFile(zoom);

        // Remove all active boundary layers
        Object.values(this.geojsonLayerCache).forEach(layer => {
            if (this.map.hasLayer(layer)) this.map.removeLayer(layer);
        });

        // Don't show boundaries only when zoomed too far OUT (but still show states)
        if (zoom < 4) {  // Only hide when REALLY zoomed out
            return;
        }

        if (this.geojsonLayerCache[geojsonFile]) {
            this.currentLayer = this.geojsonLayerCache[geojsonFile];
            this.currentLayer.addTo(this.map);
            return;
        }

        // Add error handling for fetch
        fetch(`/static/${geojsonFile}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('GeoJSON loaded:', geojsonFile, 'Features:', data.features?.length); // Debug log
                const layer = L.geoJSON(data, {
                    style: () => ({
                        color: "#3388ff",
                        weight: 2,
                        fillOpacity: 0.2,
                        fillColor: "#3388ff"  // Add explicit fill color
                    }),
                    onEachFeature: (feature, layer) => {
                        layer.on('mouseover', () => layer.setStyle({fillColor: 'yellow'}));
                        layer.on('mouseout', () => layer.setStyle({fillColor: '#3388ff'}));
                        
                        const name = feature.properties.shapeName || feature.properties.DISTRICT || feature.properties.NAME_1 || "Unknown";
                        const popupContent = `<b>${name}</b><br>
                            Average Income: ₹${Math.floor(Math.random() * 100000 + 80000)}<br>
                            Employment Rate: ${Math.floor(Math.random() * 20 + 70)}%<br>
                            Population Density: ${Math.floor(Math.random() * 900 + 100)}/km²<br>
                            Interest Index: ${Math.floor(Math.random() * 45 + 40)}`;
                        
                        layer.bindPopup(popupContent);
                    }
                });
                this.geojsonLayerCache[geojsonFile] = layer;
                this.currentLayer = layer;
                layer.addTo(this.map);
            })
            .catch(error => {
                console.error('Error loading GeoJSON:', error, 'File:', geojsonFile);
            });
    }
}