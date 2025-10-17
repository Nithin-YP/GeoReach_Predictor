class AdminCharts {
    constructor(chartData) {
        this.data = chartData;
        this.charts = {}; // Store chart instances for dynamic updates
        this.initCharts();
    }

    initCharts() {
        this.renderPredictionsTrend();
        this.renderTopStates();
        this.renderCategoryQueries();
        this.renderModelAccuracy();
    }

    renderPredictionsTrend() {
        const ctx = document.getElementById('predictionsTrendChart');
        if (!ctx) return;

        this.charts.predictionsTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.data.predictions_trend.labels,
                datasets: [{
                    label: 'Predictions',
                    data: this.data.predictions_trend.data,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                // Add click interactivity
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const date = this.data.predictions_trend.labels[index];
                        const value = this.data.predictions_trend.data[index];
                        console.log(`Date clicked: ${date} - ${value} predictions`);
                        this.onDateClick(date, value);
                    }
                },
                //Custom tooltips
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                return `Predictions: ${context.parsed.y}`;
                            },
                            afterLabel: (context) => {
                                return 'Click for details';
                            }
                        }
                    }
                },
                // Custom animations
                animation: {
                    duration: 2000,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }

    renderTopStates() {
        const ctx = document.getElementById('topStatesChart');
        if (!ctx) return;

        this.charts.topStates = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.data.top_states.labels,
                datasets: [{
                    label: 'Queries',
                    data: this.data.top_states.data,
                    backgroundColor: '#28a745',
                    borderColor: '#1e7e34',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                // Add click interactivity
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const state = this.data.top_states.labels[index];
                        const queries = this.data.top_states.data[index];
                        console.log(`State clicked: ${state} - ${queries} queries`);
                        this.onStateClick(state, queries);
                    }
                },
                // Hover callbacks
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                },
                // Custom tooltips
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                return `Queries: ${context.parsed.x}`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderCategoryQueries() {
        const ctx = document.getElementById('categoryQueriesChart');
        if (!ctx) return;

        this.charts.categoryQueries = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: this.data.category_queries.labels,
                datasets: [{
                    data: this.data.category_queries.data,
                    backgroundColor: this.data.category_queries.colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                // NEW: Add click interactivity
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const category = this.data.category_queries.labels[index];
                        const percentage = this.data.category_queries.data[index];
                        console.log(`Category clicked: ${category} - ${percentage}%`);
                        this.onCategoryClick(category, percentage);
                    }
                },
                // Custom legend
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            font: {
                                size: 12
                            }
                        },
                        onClick: (e, legendItem, legend) => {
                            const index = legendItem.index;
                            const chart = legend.chart;
                            const meta = chart.getDatasetMeta(0);
                            meta.data[index].hidden = !meta.data[index].hidden;
                            chart.update();
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderModelAccuracy() {
        const ctx = document.getElementById('modelAccuracyChart');
        if (!ctx) return;

        this.charts.modelAccuracy = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.data.model_accuracy.labels,
                datasets: [{
                    label: 'Accuracy (%)',
                    data: this.data.model_accuracy.data,
                    borderColor: '#ffc107',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointBackgroundColor: '#ffc107',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: (value) => value + '%'
                        }
                    }
                },
                // Add click interactivity
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const version = this.data.model_accuracy.labels[index];
                        const accuracy = this.data.model_accuracy.data[index];
                        console.log(`Version clicked: ${version} - ${accuracy}%`);
                        this.onVersionClick(version, accuracy);
                    }
                },
                // Custom animations
                animation: {
                    duration: 1500,
                    easing: 'easeInOutCubic'
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                return `Accuracy: ${context.parsed.y}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    // ============================================
    // OTHER CHART TYPES
    // ============================================

    renderRadarChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.charts.radar = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: data.label || 'Metrics',
                    data: data.data,
                    backgroundColor: 'rgba(0, 123, 255, 0.2)',
                    borderColor: '#007bff',
                    borderWidth: 2,
                    pointBackgroundColor: '#007bff',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#007bff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }

    renderPolarAreaChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.charts.polarArea = new Chart(ctx, {
            type: 'polarArea',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.data,
                    backgroundColor: data.colors || ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    renderBubbleChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.charts.bubble = new Chart(ctx, {
            type: 'bubble',
            data: {
                datasets: [{
                    label: data.label || 'Bubble Data',
                    data: data.data, // Format: [{x: 10, y: 20, r: 15}, ...]
                    backgroundColor: 'rgba(0, 123, 255, 0.5)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { title: { display: true, text: data.xLabel || 'X Axis' } },
                    y: { title: { display: true, text: data.yLabel || 'Y Axis' } }
                }
            }
        });
    }

    renderMixedChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.charts.mixed = new Chart(ctx, {
            data: {
                labels: data.labels,
                datasets: data.datasets // Array of datasets with different types
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    renderStackedBarChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.charts.stackedBar = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((ds, i) => ({
                    label: ds.label,
                    data: ds.data,
                    backgroundColor: ds.color || this.getDefaultColor(i)
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true }
                }
            }
        });
    }

    renderStackedAreaChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.charts.stackedArea = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: data.datasets.map((ds, i) => ({
                    label: ds.label,
                    data: ds.data,
                    fill: true,
                    backgroundColor: ds.backgroundColor || `rgba(0, 123, 255, ${0.3 - i * 0.1})`,
                    borderColor: ds.borderColor || this.getDefaultColor(i),
                    tension: 0.4
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        stacked: true,
                        beginAtZero: true 
                    }
                }
            }
        });
    }

    renderHeatmapChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        // For heatmap, we'll use a matrix-style bubble chart
        const heatmapData = [];
        data.matrix.forEach((row, y) => {
            row.forEach((value, x) => {
                heatmapData.push({
                    x: data.xLabels[x],
                    y: data.yLabels[y],
                    v: value
                });
            });
        });

        this.charts.heatmap = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: data.label || 'Heatmap',
                    data: heatmapData.map(d => ({ x: d.x, y: d.y, r: d.v })),
                    backgroundColor: (context) => {
                        const value = context.raw.r;
                        const max = Math.max(...heatmapData.map(d => d.v));
                        const intensity = value / max;
                        return `rgba(255, 99, 132, ${intensity})`;
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    // ============================================
    // ADVANCED FEATURES
    // ============================================

    // Dynamic Update - Update chart data without reload
    updateChart(chartName, newData) {
        const chart = this.charts[chartName];
        if (!chart) {
            console.warn(`Chart '${chartName}' not found`);
            return;
        }

        if (newData.labels) {
            chart.data.labels = newData.labels;
        }
        if (newData.datasets) {
            chart.data.datasets.forEach((dataset, i) => {
                if (newData.datasets[i]) {
                    dataset.data = newData.datasets[i].data;
                }
            });
        } else if (newData.data) {
            chart.data.datasets[0].data = newData.data;
        }

        chart.update();
    }

    // Add data point dynamically
    addDataPoint(chartName, label, value) {
        const chart = this.charts[chartName];
        if (!chart) return;

        chart.data.labels.push(label);
        chart.data.datasets[0].data.push(value);
        chart.update();
    }

    // Remove data point dynamically
    removeDataPoint(chartName, index) {
        const chart = this.charts[chartName];
        if (!chart) return;

        chart.data.labels.splice(index, 1);
        chart.data.datasets[0].data.splice(index, 1);
        chart.update();
    }

    // Export chart as image
    exportChartAsImage(chartName, filename = 'admin-chart.png') {
        const chart = this.charts[chartName];
        if (!chart) return;

        const url = chart.toBase64Image();
        const link = document.createElement('a');
        link.download = filename;
        link.href = url;
        link.click();
    }

    // Real-time data streaming (simulated)
    startRealTimeUpdate(chartName, interval = 2000, dataCallback) {
        if (this.realTimeIntervals && this.realTimeIntervals[chartName]) {
            clearInterval(this.realTimeIntervals[chartName]);
        }

        if (!this.realTimeIntervals) {
            this.realTimeIntervals = {};
        }

        this.realTimeIntervals[chartName] = setInterval(() => {
            const newData = dataCallback();
            this.addDataPoint(chartName, newData.label, newData.value);

            // Keep only last N points
            const chart = this.charts[chartName];
            if (chart.data.labels.length > 30) {
                this.removeDataPoint(chartName, 0);
            }
        }, interval);
    }

    stopRealTimeUpdate(chartName) {
        if (this.realTimeIntervals && this.realTimeIntervals[chartName]) {
            clearInterval(this.realTimeIntervals[chartName]);
            delete this.realTimeIntervals[chartName];
        }
    }

    // Stop all real-time updates
    stopAllRealTimeUpdates() {
        if (this.realTimeIntervals) {
            Object.keys(this.realTimeIntervals).forEach(chartName => {
                this.stopRealTimeUpdate(chartName);
            });
        }
    }

    // Custom animation
    animateChart(chartName, animationOptions = {}) {
        const chart = this.charts[chartName];
        if (!chart) return;

        const defaultOptions = {
            duration: 1000,
            easing: 'easeInOutQuart'
        };

        chart.options.animation = { ...defaultOptions, ...animationOptions };
        chart.update();
    }

    // Destroy chart
    destroyChart(chartName) {
        if (this.charts[chartName]) {
            this.charts[chartName].destroy();
            delete this.charts[chartName];
        }
    }

    // Destroy all charts
    destroyAllCharts() {
        this.stopAllRealTimeUpdates();
        Object.keys(this.charts).forEach(chartName => {
            this.destroyChart(chartName);
        });
    }

    // ============================================
    // UTILITY METHODS
    // ============================================

    getDefaultColor(index) {
        const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6f42c1'];
        return colors[index % colors.length];
    }

    // Custom callbacks for clicks (override these in implementation)
    onDateClick(date, value) {
        console.log(`Date clicked: ${date} with value ${value}`);
    }

    onStateClick(state, queries) {
        console.log(`State clicked: ${state} with ${queries} queries`);
    }

    onCategoryClick(category, percentage) {
        console.log(`Category clicked: ${category} with ${percentage}%`);
    }

    onVersionClick(version, accuracy) {
        console.log(`Version clicked: ${version} with ${accuracy}% accuracy`);
    }

    // Resize all charts
    resizeAllCharts() {
        Object.values(this.charts).forEach(chart => {
            chart.resize();
        });
    }

    // Get chart instance
    getChart(chartName) {
        return this.charts[chartName];
    }

    // Check if chart exists
    hasChart(chartName) {
        return !!this.charts[chartName];
    }

    // Get all chart names
    getChartNames() {
        return Object.keys(this.charts);
    }
}