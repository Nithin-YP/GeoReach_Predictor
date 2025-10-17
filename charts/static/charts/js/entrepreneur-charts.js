class EntrepreneurCharts {
    constructor(chartData) {
        this.data = chartData;
        this.charts = {}; // Store chart instances for dynamic updates
        this.initCharts();
    }

    initCharts() {
        this.renderSuccessByCategory();
        this.renderSuccessDistribution();
        this.renderPriceVsSuccess();
        this.renderTrendOverTime();
    }

    renderSuccessByCategory() {
        const ctx = document.getElementById('successByCategoryChart');
        if (!ctx) return;

        this.charts.successByCategory = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.data.success_by_category.labels,
                datasets: [{
                    label: 'Success Rate (%)',
                    data: this.data.success_by_category.data,
                    backgroundColor: '#007bff',
                    borderColor: '#0056b3',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },

                //  Add click interactivity
                onClick: (e, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const category = this.data.success_by_category.labels[index];
                        const value = this.data.success_by_category.data[index];
                        console.log(`Clicked: ${category} - ${value}%`);
                        // You can trigger custom actions here
                        this.onCategoryClick(category, value);
                    }
                },
                // Custom tooltips
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                return `Success Rate: ${context.parsed.y}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderSuccessDistribution() {
        const ctx = document.getElementById('successDistributionChart');
        if (!ctx) return;

        this.charts.successDistribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: this.data.success_distribution.labels,
                datasets: [{
                    data: this.data.success_distribution.data,
                    backgroundColor: this.data.success_distribution.colors
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                // Custom legend
                plugins: {
                    legend: {
                        position: 'bottom',
                        onClick: (e, legendItem, legend) => {
                            // Custom legend click behavior
                            const index = legendItem.index;
                            const chart = legend.chart;
                            const meta = chart.getDatasetMeta(0);
                            meta.data[index].hidden = !meta.data[index].hidden;
                            chart.update();
                        }
                    }
                }
            }
        });
    }

    renderPriceVsSuccess() {
        const ctx = document.getElementById('priceVsSuccessChart');
        if (!ctx) return;

        this.charts.priceVsSuccess = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Price vs Success',
                    data: this.data.price_vs_success,
                    backgroundColor: 'rgba(0, 123, 255, 0.5)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: { display: true, text: 'Price (₹)' }
                    },
                    y: {
                        title: { display: true, text: 'Success Rate (%)' },
                        beginAtZero: true,
                        max: 100
                    }
                },
                // Hover callbacks
                onHover: (event, elements) => {
                    event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                }
            }
        });
    }

    renderTrendOverTime() {
        const ctx = document.getElementById('trendOverTimeChart');
        if (!ctx) return;

        this.charts.trendOverTime = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.data.trend_over_time.labels,
                datasets: [{
                    label: 'Success Trend',
                    data: this.data.trend_over_time.data,
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                // NEW: Custom animations
                animation: {
                    duration: 2000,
                    easing: 'easeInOutQuart'
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
                    borderWidth: 2
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

    renderAreaChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        this.charts.area = new Chart(ctx, {
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
                    y: { beginAtZero: true }
                }
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
    exportChartAsImage(chartName, filename = 'chart.png') {
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
            if (chart.data.labels.length > 20) {
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
        Object.keys(this.charts).forEach(chartName => {
            this.destroyChart(chartName);
        });
    }

    // ============================================
    // UTILITY METHODS
    // ============================================

    getDefaultColor(index) {
        const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8'];
        return colors[index % colors.length];
    }

    // Custom callback for category click (override this in implementation)
    onCategoryClick(category, value) {
        // Default: log to console
        // You can override this method for custom behavior
        console.log(`Category clicked: ${category} with value ${value}`);
    }

    // Resize all charts
    resizeAllCharts() {
        Object.values(this.charts).forEach(chart => {
            chart.resize();
        });
    }
}