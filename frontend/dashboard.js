// Global State
let metadata = { districts: [], commodities: [], min_date: null, max_date: null };
let selectedDistricts = [];
let selectedCommodities = [];
let currentDataset = [];

// Crop Metadata for Styling
const CROP_META = {
    "Tomato": { emoji: "🍅", color: "#f87171", class: "glass-card-tomato" },
    "Onion": { emoji: "🧅", color: "#c084fc", class: "glass-card-onion" },
    "Potato": { emoji: "🥔", color: "#fbbf24", class: "glass-card-potato" },
    "Wheat": { emoji: "🌾", color: "#fde047", class: "glass-card-wheat" },
    "Rice": { emoji: "🍚", color: "#60a5fa", class: "glass-card-generic" },
    "Maize": { emoji: "🌽", color: "#34d399", class: "glass-card-generic" },
    "Soybean": { emoji: "🫘", color: "#818cf8", class: "glass-card-generic" }
};

// Preset Question Templates
const PRESET_TEMPLATES = [
    "Why is {commodity} showing high volatility in {district} this period?",
    "How is rainfall affecting {commodity} prices in {district}?",
    "What is the price trend for {commodity} in {district} and should farmers sell now?",
    "Is the current temperature extreme likely to push {commodity} prices higher next week?"
];

// DOM Elements
const el = {
    districtMultiselect: document.getElementById('district-multiselect'),
    districtDisplay: document.getElementById('district-selected-display'),
    districtOptions: document.getElementById('district-options-container'),
    
    commodityMultiselect: document.getElementById('commodity-multiselect'),
    commodityDisplay: document.getElementById('commodity-selected-display'),
    commodityOptions: document.getElementById('commodity-options-container'),
    
    startDate: document.getElementById('start-date'),
    endDate: document.getElementById('end-date'),
    applyFiltersBtn: document.getElementById('apply-filters-btn'),
    
    avgPrice: document.getElementById('metric-avg-price'),
    maxVol: document.getElementById('metric-max-vol'),
    cumRain: document.getElementById('metric-cum-rain'),
    avgTemp: document.getElementById('metric-avg-temp'),
    
    tabTrendsBtn: document.getElementById('tab-trends-btn'),
    tabHeatmapBtn: document.getElementById('tab-heatmap-btn'),
    tabTrends: document.getElementById('tab-trends'),
    tabHeatmap: document.getElementById('tab-heatmap'),
    
    alertsContainer: document.getElementById('alerts-list-container'),
    
    analystPresets: document.getElementById('analyst-presets'),
    analystCropFocus: document.getElementById('analyst-crop-focus'),
    analystCustomQuery: document.getElementById('analyst-custom-query'),
    runAnalystBtn: document.getElementById('run-analyst-btn'),
    analystResponseBox: document.getElementById('analyst-response-box'),
    analystResponseText: document.getElementById('analyst-response-text'),
    analystResponseMeta: document.getElementById('analyst-response-meta'),
    
    forecastingDistrict: document.getElementById('forecasting-district'),
    predictionCardsContainer: document.getElementById('prediction-cards-container')
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
    setupCustomMultiselects();
    setupTabSwitching();
    await fetchMetadata();
    setupEventHandlers();
    
    // Initial fetch of data and render
    await updateDashboard();
});

// Setup multiselect dropdown custom controls
function setupCustomMultiselects() {
    // Toggle dropdowns
    el.districtMultiselect.addEventListener('click', (e) => {
        e.stopPropagation();
        el.districtMultiselect.classList.toggle('open');
        el.commodityMultiselect.classList.remove('open');
    });
    
    el.commodityMultiselect.addEventListener('click', (e) => {
        e.stopPropagation();
        el.commodityMultiselect.classList.toggle('open');
        el.districtMultiselect.classList.remove('open');
    });
    
    // Close when clicking outside
    document.addEventListener('click', () => {
        el.districtMultiselect.classList.remove('open');
        el.commodityMultiselect.classList.remove('open');
    });
    
    // Prevent close when clicking inside options container
    el.districtOptions.addEventListener('click', (e) => e.stopPropagation());
    el.commodityOptions.addEventListener('click', (e) => e.stopPropagation());
}

// Handle Tab Switching
function setupTabSwitching() {
    const tabs = [
        { btn: el.tabTrendsBtn, panel: el.tabTrends },
        { btn: el.tabHeatmapBtn, panel: el.tabHeatmap }
    ];
    
    tabs.forEach(tab => {
        tab.btn.addEventListener('click', () => {
            tabs.forEach(t => {
                t.btn.classList.remove('active');
                t.btn.setAttribute('aria-selected', 'false');
                t.panel.classList.remove('active');
            });
            
            tab.btn.classList.add('active');
            tab.btn.setAttribute('aria-selected', 'true');
            tab.panel.classList.add('active');
            
            // Resize Plotly charts to ensure full layout fit
            setTimeout(() => {
                const charts = document.querySelectorAll('.plotly-chart-canvas');
                charts.forEach(c => {
                    if (c.id && document.getElementById(c.id).data) {
                        Plotly.Plots.resize(c.id);
                    }
                });
            }, 50);
        });
    });
}

// Fetch metadata from backend
async function fetchMetadata() {
    try {
        const res = await fetch('/api/metadata');
        if (!res.ok) throw new Error("Metadata fetch failed");
        metadata = await res.json();
        
        // Build option items in lists
        buildMultiselectOptions(el.districtOptions, metadata.districts, 'district');
        buildMultiselectOptions(el.commodityOptions, metadata.commodities, 'commodity');
        
        // Select defaults
        selectedDistricts = metadata.districts.slice(0, 3);
        selectedCommodities = metadata.commodities.slice(0, 2);
        
        updateMultiselectDisplay(el.districtDisplay, selectedDistricts, 'District');
        updateMultiselectDisplay(el.commodityDisplay, selectedCommodities, 'Commodity');
        
        // Check checkboxes
        checkMultiselectBoxes(el.districtOptions, selectedDistricts);
        checkMultiselectBoxes(el.commodityOptions, selectedCommodities);
        
        // Populate date range fields
        if (metadata.max_date) {
            el.endDate.value = metadata.max_date;
            
            // Default start date is 30 days prior to max date
            const maxDt = new Date(metadata.max_date);
            maxDt.setDate(maxDt.getDate() - 30);
            const startStr = maxDt.toISOString().split('T')[0];
            el.startDate.value = startStr < metadata.min_date ? metadata.min_date : startStr;
        }
        
        // Set dates boundaries
        if (metadata.min_date) {
            el.startDate.min = metadata.min_date;
            el.endDate.min = metadata.min_date;
        }
        if (metadata.max_date) {
            el.startDate.max = metadata.max_date;
            el.endDate.max = metadata.max_date;
        }
        
        // Populate forecasting district dropdown
        el.forecastingDistrict.innerHTML = '';
        metadata.districts.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            el.forecastingDistrict.appendChild(opt);
        });
        if (metadata.districts.length > 0) {
            el.forecastingDistrict.value = metadata.districts[0];
        }
        
        // Populate Analyst crop focus dropdown
        updateAnalystCropDropdown();
        
    } catch (err) {
        console.error("Error setting metadata:", err);
    }
}

// Helper to build list check elements
function buildMultiselectOptions(container, items, prefix) {
    container.innerHTML = '';
    items.forEach(item => {
        const label = document.createElement('label');
        label.className = 'multiselect-option';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = item;
        checkbox.id = `${prefix}-${item.toLowerCase().replace(/\s+/g, '-')}`;
        
        checkbox.addEventListener('change', () => {
            handleOptionChange(prefix);
        });
        
        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(item));
        container.appendChild(label);
    });
}

function checkMultiselectBoxes(container, selectedList) {
    const checkboxes = container.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(box => {
        box.checked = selectedList.includes(box.value);
    });
}

function handleOptionChange(prefix) {
    if (prefix === 'district') {
        const checked = Array.from(el.districtOptions.querySelectorAll('input:checked')).map(box => box.value);
        selectedDistricts = checked;
        updateMultiselectDisplay(el.districtDisplay, selectedDistricts, 'District');
    } else {
        const checked = Array.from(el.commodityOptions.querySelectorAll('input:checked')).map(box => box.value);
        selectedCommodities = checked;
        updateMultiselectDisplay(el.commodityDisplay, selectedCommodities, 'Commodity');
        updateAnalystCropDropdown();
    }
    updateAnalystPresets();
}

function updateMultiselectDisplay(displayEl, selectedList, labelType) {
    if (selectedList.length === 0) {
        displayEl.textContent = `Select ${labelType}s`;
    } else if (selectedList.length <= 2) {
        displayEl.textContent = selectedList.join(', ');
    } else {
        displayEl.textContent = `${selectedList.length} Selected`;
    }
}

function updateAnalystCropDropdown() {
    el.analystCropFocus.innerHTML = '';
    const activeCrops = selectedCommodities.length > 0 ? selectedCommodities : (metadata.commodities.slice(0, 1) || ["Tomato"]);
    activeCrops.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        el.analystCropFocus.appendChild(opt);
    });
}

// Update preset Q list based on active crop and district selection
function updateAnalystPresets() {
    const focusCrop = el.analystCropFocus.value || selectedCommodities[0] || "Tomato";
    const focusDistrict = selectedDistricts[0] || "Nashik";
    
    // Remember currently selected preset
    const currentVal = el.analystPresets.value;
    
    el.analystPresets.innerHTML = '';
    const defaultOpt = document.createElement('option');
    defaultOpt.value = '';
    defaultOpt.textContent = '(Type your own below)';
    el.analystPresets.appendChild(defaultOpt);
    
    PRESET_TEMPLATES.forEach((tpl, idx) => {
        const qText = tpl.replace('{commodity}', focusCrop).replace('{district}', focusDistrict);
        const opt = document.createElement('option');
        opt.value = qText;
        opt.textContent = `💡 Preset ${idx + 1}: ${qText.substring(0, 50)}...`;
        opt.setAttribute('data-full-text', qText);
        el.analystPresets.appendChild(opt);
    });
    
    // Restore value if template matches
    if (currentVal) {
        // Find if template matches and set index accordingly
        const matchingOpt = Array.from(el.analystPresets.options).find(o => o.value === currentVal);
        if (matchingOpt) {
            el.analystPresets.value = currentVal;
        }
    }
}

// Setup static event handlers
function setupEventHandlers() {
    el.applyFiltersBtn.addEventListener('click', async () => {
        await updateDashboard();
    });
    
    el.analystCropFocus.addEventListener('change', () => {
        updateAnalystPresets();
    });
    
    el.analystPresets.addEventListener('change', () => {
        if (el.analystPresets.value) {
            el.analystCustomQuery.value = el.analystPresets.value;
        } else {
            el.analystCustomQuery.value = '';
        }
    });
    
    el.runAnalystBtn.addEventListener('click', async () => {
        await executeAnalyst();
    });
    
    el.forecastingDistrict.addEventListener('change', async () => {
        await renderForecastingCards();
    });
}

// Main update trigger
async function updateDashboard() {
    if (selectedDistricts.length === 0 || selectedCommodities.length === 0) {
        alert("Please select at least one district and one commodity.");
        return;
    }
    
    el.applyFiltersBtn.textContent = "Loading...";
    el.applyFiltersBtn.disabled = true;
    
    try {
        await fetchData();
        calculateMetrics();
        renderTrendsChart();
        
        // Always load alerts and heatmap in background or if tab is selected
        await fetchAndRenderAlerts();
        renderHeatmapChart();
        
        // Update analyst presets to match filters
        updateAnalystPresets();
        
        // Render forecasting cards
        await renderForecastingCards();
        
    } catch (err) {
        console.error("Dashboard update failed:", err);
    } finally {
        el.applyFiltersBtn.textContent = "Apply Filters";
        el.applyFiltersBtn.disabled = false;
    }
}

// Fetch historical dataset
async function fetchData() {
    const params = new URLSearchParams();
    selectedDistricts.forEach(d => params.append('district', d));
    selectedCommodities.forEach(c => params.append('commodity', c));
    if (el.startDate.value) params.append('start_date', el.startDate.value);
    if (el.endDate.value) params.append('end_date', el.endDate.value);
    
    const url = `/api/data?${params.toString()}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Data retrieval failed");
    currentDataset = await res.json();
}

// Compute key performance indicators from dataset
function calculateMetrics() {
    if (currentDataset.length === 0) {
        el.avgPrice.textContent = "₹0.00";
        el.maxVol.textContent = "0.000";
        el.cumRain.textContent = "0.0 mm";
        el.avgTemp.textContent = "0.0°C";
        return;
    }
    
    let sumPrice = 0;
    let countPrice = 0;
    let maxVolatility = 0;
    
    // Group rain by date to sum unique daily values across districts
    const dailyRain = {};
    let sumTemp = 0;
    let countTemp = 0;
    
    currentDataset.forEach(row => {
        if (row.modal_price) {
            sumPrice += row.modal_price;
            countPrice++;
        }
        if (row.volatility_score > maxVolatility) {
            maxVolatility = row.volatility_score;
        }
        
        // Sum rainfall per date (aggregate average daily rainfall)
        if (row.date) {
            if (!dailyRain[row.date]) dailyRain[row.date] = [];
            dailyRain[row.date].push(row.precipitation_mm || 0);
        }
        
        if (row.temp_max_c) {
            sumTemp += row.temp_max_c;
            countTemp++;
        }
    });
    
    // Compute total rainfall by sum of daily averages
    let totalRain = 0;
    Object.values(dailyRain).forEach(vals => {
        const avgDaily = vals.reduce((s, v) => s + v, 0) / vals.length;
        totalRain += avgDaily;
    });
    
    const avgPriceVal = countPrice > 0 ? (sumPrice / countPrice) : 0;
    const avgTempVal = countTemp > 0 ? (sumTemp / countTemp) : 0;
    
    el.avgPrice.textContent = `₹${avgPriceVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    el.maxVol.textContent = maxVolatility.toFixed(3);
    el.cumRain.textContent = `${totalRain.toFixed(1)} mm`;
    el.avgTemp.textContent = `${avgTempVal.toFixed(1)}°C`;
}

// Render Trends Chart using Plotly
function renderTrendsChart() {
    const traces = [];
    
    // Group records by commodity to create separate traces
    selectedCommodities.forEach(crop => {
        const cropRows = currentDataset
            .filter(r => r.commodity === crop)
            .sort((a, b) => new Date(a.date) - new Date(b.date));
            
        if (cropRows.length > 0) {
            traces.push({
                x: cropRows.map(r => r.date),
                y: cropRows.map(r => r.modal_price),
                name: `${crop} Price (₹)`,
                type: 'scatter',
                mode: 'lines+markers',
                line: { width: 3, color: CROP_META[crop]?.color || '#ffffff' },
                marker: { size: 6 },
                yaxis: 'y'
            });
        }
    });
    
    // Add rainfall aggregated bar trace
    // Group by date to average rainfall across districts
    const dateRainMap = {};
    currentDataset.forEach(row => {
        if (!dateRainMap[row.date]) dateRainMap[row.date] = [];
        dateRainMap[row.date].push(row.precipitation_mm || 0);
    });
    
    const sortedDates = Object.keys(dateRainMap).sort((a, b) => new Date(a) - new Date(b));
    const avgRainfall = sortedDates.map(d => {
        const vals = dateRainMap[d];
        return vals.reduce((s, v) => s + v, 0) / vals.length;
    });
    
    if (sortedDates.length > 0) {
        traces.push({
            x: sortedDates,
            y: avgRainfall,
            name: "Avg Rainfall (mm)",
            type: 'bar',
            opacity: 0.2,
            marker: { color: '#3b82f6' },
            yaxis: 'y2'
        });
    }
    
    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: 'Outfit' },
        xaxis: {
            showgrid: true,
            gridcolor: 'rgba(255,255,255,0.05)',
            tickfont: { color: '#94a3b8' },
            type: 'date'
        },
        yaxis: {
            title: { text: "Modal Price (₹/Quintal)", font: { color: '#c084fc' } },
            showgrid: true,
            gridcolor: 'rgba(255,255,255,0.05)',
            tickfont: { color: '#c084fc' }
        },
        yaxis2: {
            title: { text: "Precipitation (mm)", font: { color: '#3b82f6' } },
            overlaying: 'y',
            side: 'right',
            showgrid: false,
            tickfont: { color: '#3b82f6' }
        },
        legend: {
            orientation: "h",
            yanchor: "bottom",
            y: 1.05,
            xanchor: "right",
            x: 1
        },
        margin: { l: 60, r: 60, t: 80, b: 40 },
        hovermode: 'x unified'
    };
    
    const config = { responsive: true, displayModeBar: false };
    
    Plotly.newPlot('plotly-trends-chart', traces, layout, config);
}

// Render Volatility Heatmap using Plotly
function renderHeatmapChart() {
    // Collect all districts and commodities in the current dataset
    const districts = Array.from(new Set(currentDataset.map(r => r.district))).sort();
    const commodities = Array.from(new Set(currentDataset.map(r => r.commodity))).sort();
    
    if (districts.length === 0 || commodities.length === 0) {
        Plotly.newPlot('plotly-heatmap-chart', [], {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            xaxis: { visible: false },
            yaxis: { visible: false }
        });
        return;
    }
    
    // Group and average volatility scores by (district, commodity)
    // Initialize 2D grid matrix of size [commodities.length][districts.length] with nulls
    const zMatrix = Array(commodities.length).fill().map(() => Array(districts.length).fill(null));
    
    commodities.forEach((crop, cIdx) => {
        districts.forEach((dist, dIdx) => {
            const matches = currentDataset.filter(r => r.commodity === crop && r.district === dist);
            if (matches.length > 0) {
                const avgVol = matches.reduce((sum, r) => sum + (r.volatility_score || 0), 0) / matches.length;
                zMatrix[cIdx][dIdx] = avgVol;
            }
        });
    });
    
    const data = [{
        x: districts,
        y: commodities,
        z: zMatrix,
        type: 'heatmap',
        colorscale: [
            [0, '#10b981'],   // Stable Green
            [0.5, '#f59e0b'], // Warning Orange
            [1, '#ef4444']    // Danger Red
        ],
        showscale: true,
        colorbar: {
            title: 'Volatility',
            titlefont: { color: '#94a3b8' },
            tickfont: { color: '#94a3b8' }
        }
    }];
    
    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#94a3b8', family: 'Outfit' },
        margin: { l: 85, r: 20, t: 20, b: 40 },
        xaxis: { tickfont: { color: '#94a3b8' } },
        yaxis: { tickfont: { color: '#94a3b8' } }
    };
    
    const config = { responsive: true, displayModeBar: false };
    
    Plotly.newPlot('plotly-heatmap-chart', data, layout, config);
}

// Fetch and render High Volatility Alerts list
async function fetchAndRenderAlerts() {
    try {
        const params = new URLSearchParams();
        selectedDistricts.forEach(d => params.append('district', d));
        selectedCommodities.forEach(c => params.append('commodity', c));
        
        const res = await fetch(`/api/alerts?${params.toString()}`);
        if (!res.ok) throw new Error("Alerts retrieval failed");
        const alerts = await res.json();
        
        el.alertsContainer.innerHTML = '';
        
        if (alerts.length === 0) {
            el.alertsContainer.innerHTML = '<div class="no-alerts-msg">🟢 No active volatility alerts in selected area.</div>';
            return;
        }
        
        alerts.forEach(item => {
            const row = document.createElement('div');
            row.className = 'alert-row';
            
            const riskClass = item.volatility_label === 'HIGH' ? 'high' : 'medium';
            const riskText = `${item.volatility_label} RISK`;
            
            row.innerHTML = `
                <div class="alert-left">
                    <span class="risk-badge ${riskClass}">${riskText}</span>
                    <span class="alert-title">${item.commodity} &mdash; ${item.district}</span>
                </div>
                <div class="alert-right">
                    💧 ${item.precipitation_mm.toFixed(1)} mm Rain | 📈 Volatility: <b>${item.volatility_score.toFixed(3)}</b>
                </div>
            `;
            
            el.alertsContainer.appendChild(row);
        });
        
    } catch (err) {
        console.error("Failed to render alerts:", err);
    }
}

// Call Gemini AI Analyst
async function executeAnalyst() {
    const question = el.analystCustomQuery.value.trim();
    const focusCrop = el.analystCropFocus.value;
    const focusDistrict = selectedDistricts[0] || "Nashik";
    
    if (!question) {
        alert("Please select or type a question first.");
        return;
    }
    
    // Show spinner inside response box
    el.analystResponseBox.classList.remove('hidden');
    el.analystResponseText.innerHTML = '<div style="display:flex; align-items:center; gap:0.5rem;"><div class="spinner"></div> Consulting the AI market analyst...</div>';
    el.analystResponseMeta.textContent = `Context: ${focusCrop} in ${focusDistrict}`;
    
    el.runAnalystBtn.disabled = true;
    el.runAnalystBtn.textContent = "Analyzing...";
    
    try {
        const payload = {
            commodity: focusCrop,
            district: focusDistrict,
            question: question,
            districts: selectedDistricts,
            commodities: selectedCommodities,
            start_date: el.startDate.value || null,
            end_date: el.endDate.value || null
        };
        
        const res = await fetch('/api/analyst', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Analysis request failed");
        }
        
        const data = await res.json();
        
        // Set answer text securely using textContent
        el.analystResponseText.textContent = data.answer;
        el.analystResponseMeta.innerHTML = `Powered by Gemini 2.5 Flash &nbsp;·&nbsp; Context: ${focusCrop} in ${focusDistrict}`;
        
    } catch (err) {
        el.analystResponseText.innerHTML = `<span style="color: var(--color-danger);">⚠️ Error: ${err.message}</span>`;
    } finally {
        el.runAnalystBtn.disabled = false;
        el.runAnalystBtn.textContent = "🔍 Analyze";
    }
}

// Render Crop Predictor forecasting cards
async function renderForecastingCards() {
    const targetDistrict = el.forecastingDistrict.value;
    if (!targetDistrict) return;
    
    el.predictionCardsContainer.innerHTML = '';
    
    const activeCrops = selectedCommodities.length > 0 ? selectedCommodities : metadata.commodities;
    
    // We execute calls in parallel for speed
    const cardPromises = activeCrops.map(async (crop) => {
        const cropMeta = CROP_META[crop] || { emoji: "📦", color: "#60a5fa", class: "glass-card-generic" };
        
        // Container wrapper
        const card = document.createElement('div');
        card.className = `glass-card ${cropMeta.class}`;
        card.style.display = 'flex';
        card.style.flexDirection = 'column';
        card.style.justifyContent = 'space-between';
        
        // Unique canvas ID for sparkline
        const canvasId = `spark-${crop.toLowerCase().replace(/\s+/g, '-')}`;
        
        try {
            const res = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ commodity: crop, district: targetDistrict })
            });
            
            if (!res.ok) throw new Error("Prediction fetch failed");
            const data = await res.json();
            
            if (!data.model_exists) {
                // Render Untrained Card
                card.style.borderStyle = 'dashed';
                card.style.borderColor = `${cropMeta.color}40`;
                card.innerHTML = `
                    <div class="card-header-row">
                        <h4 class="card-title">${cropMeta.emoji} ${crop}</h4>
                        <span class="card-badge untrained">Untrained</span>
                    </div>
                    <p class="card-body-text">
                        No XGBoost model exists for <b>${crop}</b> in <b>${targetDistrict}</b>.
                    </p>
                    <button class="primary-btn predictor-train-btn" id="train-btn-${canvasId}">⚡ Train ${crop} Model</button>
                `;
                
                el.predictionCardsContainer.appendChild(card);
                
                // Add Train event listener
                document.getElementById(`train-btn-${canvasId}`).addEventListener('click', async (e) => {
                    e.currentTarget.disabled = true;
                    e.currentTarget.textContent = "Training...";
                    await trainModel(crop, targetDistrict);
                });
                
            } else {
                // Render Forecast pricing results
                const badgeClass = data.volatility_label === 'HIGH' ? 'high-vol' : 'stable';
                const badgeText = data.volatility_label === 'HIGH' ? 'High Volatility' : 'Stable';
                const swingClass = data.price_change_pct < 0 ? 'negative' : 'positive';
                const swingSign = data.price_change_pct > 0 ? '+' : '';
                
                card.innerHTML = `
                    <div class="card-header-row">
                        <h4 class="card-title">${cropMeta.emoji} ${crop}</h4>
                        <span class="card-badge ${badgeClass}">${badgeText}</span>
                    </div>
                    <div class="card-metrics-row">
                        <div>
                            <span class="forecast-label">Forecast (1W)</span>
                            <div class="forecast-val">₹${data.predicted_modal_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                        </div>
                        <div style="text-align: right;">
                            <span class="forecast-label">Expected Swing</span>
                            <div class="swing-val ${swingClass}">${swingSign}${data.price_change_pct.toFixed(2)}%</div>
                        </div>
                    </div>
                    <div class="forecast-label" style="font-size:0.7rem;">Recent Price Sparkline</div>
                    <div class="sparkline-container" id="${canvasId}"></div>
                    <div class="card-footer-row">
                        <span>Current: ₹${data.latest_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                        <span>XGBoost v2.0</span>
                    </div>
                `;
                
                el.predictionCardsContainer.appendChild(card);
                
                // Draw sparkline after mounting element
                drawSparkline(canvasId, crop, targetDistrict, cropMeta.color);
            }
            
        } catch (err) {
            console.error("Prediction card error:", err);
            card.innerHTML = `<p style="color:var(--color-danger); font-size:0.85rem;">Failed to fetch prediction for ${crop}.</p>`;
            el.predictionCardsContainer.appendChild(card);
        }
    });
    
    await Promise.all(cardPromises);
}

// Trigger XGBoost model training from UI
async function trainModel(commodity, district) {
    try {
        const res = await fetch('/api/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ commodity, district })
        });
        
        if (!res.ok) throw new Error("Training request failed");
        const data = await res.json();
        
        // Show success and reload predictor cards
        alert(`🎉 Model training complete: ${data.message}`);
        await renderForecastingCards();
        
    } catch (err) {
        alert(`❌ Training failed: ${err.message}`);
        await renderForecastingCards();
    }
}

// Draw a miniature sparkline chart in the card using Plotly
function drawSparkline(containerId, commodity, district, color) {
    // Filter records for the sparkline dataset
    const history = currentDataset
        .filter(r => r.commodity === commodity && r.district === district)
        .sort((a, b) => new Date(a.date) - new Date(b.date));
        
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (history.length <= 1) {
        container.innerHTML = "<div style='height:45px; display:flex; align-items:center; color:#64748b; font-size:0.75rem;'>No trend history available.</div>";
        return;
    }
    
    const trace = {
        x: history.map(r => r.date),
        y: history.map(r => r.modal_price),
        type: 'scatter',
        mode: 'lines',
        line: { color: color, width: 2.5 },
        hoverinfo: 'skip'
    };
    
    const layout = {
        xaxis: { visible: false },
        yaxis: { visible: false },
        showlegend: false,
        margin: { l: 0, r: 0, t: 0, b: 0 },
        height: 45,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)'
    };
    
    const config = { displayModeBar: false, responsive: true };
    
    Plotly.newPlot(containerId, [trace], layout, config);
}
