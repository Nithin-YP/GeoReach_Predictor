class AdminCharts {
    constructor(chartData) {
        this.data = chartData;
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

        new Chart(ctx, {
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
                maintainAspectRatio: false
            }
        });
    }

    renderTopStates() {
        const ctx = document.getElementById('topStatesChart');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: this.data.top_states.labels,
                datasets: [{
                    label: 'Queries',
                    data: this.data.top_states.data,
                    backgroundColor: '#28a745'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y'
            }
        });
    }

    renderCategoryQueries() {
        const ctx = document.getElementById('categoryQueriesChart');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: this.data.category_queries.labels,
                datasets: [{
                    data: this.data.category_queries.data,
                    backgroundColor: this.data.category_queries.colors
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }

    renderModelAccuracy() {
        const ctx = document.getElementById('modelAccuracyChart');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.data.model_accuracy.labels,
                datasets: [{
                    label: 'Accuracy (%)',
                    data: this.data.model_accuracy.data,
                    borderColor: '#ffc107',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
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