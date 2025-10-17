class EntrepreneurCharts {
    constructor(chartData) {
        this.data = chartData;
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

        new Chart(ctx, {
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
                }
            }
        });
    }

    renderSuccessDistribution() {
        const ctx = document.getElementById('successDistributionChart');
        if (!ctx) return;

        new Chart(ctx, {
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
                maintainAspectRatio: false
            }
        });
    }

    renderPriceVsSuccess() {
        const ctx = document.getElementById('priceVsSuccessChart');
        if (!ctx) return;

        new Chart(ctx, {
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
                }
            }
        });
    }

    renderTrendOverTime() {
        const ctx = document.getElementById('trendOverTimeChart');
        if (!ctx) return;

        new Chart(ctx, {
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
                }
            }
        });
    }
}