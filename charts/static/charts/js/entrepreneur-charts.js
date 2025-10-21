// Lightweight, defensive EntrepreneurCharts helper
// Clean, defensive EntrepreneurCharts helper

(function(global){
    'use strict';

    function safeGet(obj, path, defaultVal){
        try{
            if(!obj || !path) return defaultVal;
            return path.split('.').reduce(function(acc, k){ return acc && acc[k] !== undefined ? acc[k] : undefined; }, obj) ?? defaultVal;
        }catch(e){ return defaultVal; }
    }

    function EntrepreneurCharts(data){
        this.data = data || {};
        this.charts = {};
        this._intervals = {};

        if(!global.Chart){
            console.warn('Chart.js not found; charts will not render.');
        }
    }

    EntrepreneurCharts.prototype.renderRadarChart = function(canvasId, opts){
        if(!global.Chart) return null;
        const el = document.getElementById(canvasId);
        if(!el) return null;
        const labels = opts && opts.labels ? opts.labels : safeGet(this.data, 'radar_chart.labels', []);
        const values = opts && opts.data ? opts.data : safeGet(this.data, 'radar_chart.data', []);
        try{
            const ctx = el.getContext('2d');
            const chart = new global.Chart(ctx, {
                type: 'radar',
                data: { labels: labels, datasets:[{ label: (opts && opts.label) || 'Metrics', data: values, backgroundColor: 'rgba(0,123,255,0.2)', borderColor: 'rgba(0,123,255,1)' }] },
                options: { responsive:true }
            });
            this.charts['radar'] = chart;
            return chart;
        }catch(e){ console.error('Error rendering radar chart', e); return null; }
    };

    EntrepreneurCharts.prototype.renderBubbleChart = function(canvasId, opts){
        if(!global.Chart) return null;
        const el = document.getElementById(canvasId);
        if(!el) return null;
        const data = (opts && opts.data) ? opts.data : safeGet(this.data, 'bubble_chart.data', []);
        try{
            const ctx = el.getContext('2d');
            const chart = new global.Chart(ctx, {
                type: 'bubble',
                data: { datasets: [{ label: (opts && opts.label) || 'Bubble Data', data: data, backgroundColor: 'rgba(40,167,69,0.6)' }] },
                options: { responsive:true }
            });
            this.charts['bubble'] = chart;
            return chart;
        }catch(e){ console.error('Error rendering bubble chart', e); return null; }
    };

    EntrepreneurCharts.prototype.renderSuccessDistribution = function(canvasId, opts){
        if(!global.Chart) return null;
        const el = document.getElementById(canvasId);
        if(!el) return null;
        const labels = (opts && opts.labels) ? opts.labels : safeGet(this.data, 'success_distribution.labels', []);
        const values = (opts && opts.data) ? opts.data : safeGet(this.data, 'success_distribution.data', []);
        const colors = (opts && opts.colors) ? opts.colors : safeGet(this.data, 'success_distribution.colors', []);
        try{
            const ctx = el.getContext('2d');
            const chart = new global.Chart(ctx, {
                type: 'doughnut',
                data: { labels: labels, datasets: [{ data: values, backgroundColor: colors }] },
                options: { responsive:true, maintainAspectRatio: false }
            });
            this.charts['successDistribution'] = chart;
            return chart;
        }catch(e){ console.error('Error rendering success distribution', e); return null; }
    };

    EntrepreneurCharts.prototype.updateChart = function(chartName, newData){
        const chart = this.charts[chartName];
        if (!chart) return;
        if (newData.labels) chart.data.labels = newData.labels;
        if (newData.datasets) chart.data.datasets = newData.datasets;
        else if (newData.data) chart.data.datasets[0].data = newData.data;
        chart.update();
    };

    EntrepreneurCharts.prototype.addDataPoint = function(chartName, label, value){
        const chart = this.charts[chartName];
        if (!chart) return;
        chart.data.labels.push(label);
        chart.data.datasets[0].data.push(value);
        chart.update();
    };

    EntrepreneurCharts.prototype.removeDataPoint = function(chartName, index){
        const chart = this.charts[chartName];
        if (!chart) return;
        chart.data.labels.splice(index, 1);
        chart.data.datasets[0].data.splice(index, 1);
        chart.update();
    };

    EntrepreneurCharts.prototype.exportChartAsImage = function(chartName, filename = 'chart.png'){
        const chart = this.charts[chartName];
        if (!chart) return;
        try{
            const url = chart.toBase64Image();
            const a = document.createElement('a');
            a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
        }catch(e){ console.error('Error exporting chart', e); }
    };

    EntrepreneurCharts.prototype.startRealTimeUpdate = function(chartName, interval = 2000, dataCallback){
        if (!this._intervals) this._intervals = {};
        if (this._intervals[chartName]) clearInterval(this._intervals[chartName]);
        this._intervals[chartName] = setInterval(()=>{
            try{
                const nd = (typeof dataCallback === 'function') ? dataCallback() : null;
                if (!nd) return;
                this.addDataPoint(chartName, nd.label, nd.value);
                const chart = this.charts[chartName];
                if (chart && chart.data && chart.data.labels && chart.data.labels.length > 100) {
                    this.removeDataPoint(chartName, 0);
                }
            }catch(e){ console.error('Realtime update error', e); }
        }, interval);
    };

    EntrepreneurCharts.prototype.stopRealTimeUpdate = function(chartName){
        if (this._intervals && this._intervals[chartName]){ clearInterval(this._intervals[chartName]); delete this._intervals[chartName]; }
    };

    EntrepreneurCharts.prototype.getDefaultColor = function(index){
        const colors = ['#007bff','#28a745','#ffc107','#dc3545','#17a2b8'];
        return colors[index % colors.length];
    };

    EntrepreneurCharts.prototype.resizeAllCharts = function(){
        Object.values(this.charts).forEach(c=>{ if (c && typeof c.resize === 'function') c.resize(); });
    };

    global.EntrepreneurCharts = EntrepreneurCharts;
})(typeof window !== 'undefined' ? window : this);