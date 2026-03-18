/* ========================================
   AgriSmart AI - Frontend Logic + SSE
   ======================================== */

const API_BASE = '/api';

// ---- Tab Navigation ----
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`content-${tab.dataset.tab}`).classList.add('active');
    });
});

// ---- Utility Functions ----
function getFormData(formId) {
    const form = document.getElementById(formId);
    const formData = new FormData(form);
    const data = {};
    formData.forEach((value, key) => { data[key] = parseFloat(value); });
    return data;
}

function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    const textEl = btn.querySelector('.btn-text');
    const loadEl = btn.querySelector('.btn-loading');
    btn.disabled = loading;
    textEl.style.display = loading ? 'none' : 'inline';
    loadEl.style.display = loading ? 'inline' : 'none';
}

function renderPredictionCards(prediction) {
    return `
        <div class="prediction-cards">
            <div class="prediction-card tempmax">
                <div class="label">Nhiệt độ tối đa dự đoán</div>
                <div class="value">${prediction.tempmax}°C</div>
            </div>
            <div class="prediction-card tempmin">
                <div class="label">Nhiệt độ tối thiểu dự đoán</div>
                <div class="value">${prediction.tempmin}°C</div>
            </div>
        </div>
    `;
}

function renderRiskBadge(riskLevel) {
    const level = (riskLevel || 'unknown').toLowerCase();
    const riskMap = { low: 'Thấp', medium: 'Trung bình', high: 'Cao', critical: 'Nghiêm trọng', unknown: 'Không xác định' };
    const label = riskMap[level] || level;
    return `<span class="risk-badge ${level}">${label}</span>`;
}

function renderAdvisory(advisory) {
    let html = '';

    if (advisory.risk_level) {
        html += renderRiskBadge(advisory.risk_level);
    }

    if (advisory.analysis) {
        html += `<div class="advisory-section">
            <h3>📊 Phân tích</h3>
            <div class="streaming-text">${advisory.analysis}</div>
        </div>`;
    }

    if (advisory.recommendations && advisory.recommendations.length > 0) {
        html += `<div class="advisory-section">
            <h3>💡 Khuyến nghị</h3>
            <ul>${advisory.recommendations.map(r => `<li>${r}</li>`).join('')}</ul>
        </div>`;
    }

    if (advisory.suitable_crops && advisory.suitable_crops.length > 0) {
        html += `<div class="advisory-section">
            <h3>🌱 Cây trồng phù hợp</h3>
            <ul>${advisory.suitable_crops.map(c => `<li class="crop">${c}</li>`).join('')}</ul>
        </div>`;
    }

    if (advisory.warnings && advisory.warnings.length > 0) {
        html += `<div class="advisory-section">
            <h3>⚠️ Cảnh báo</h3>
            <ul>${advisory.warnings.map(w => `<li class="warning">${w}</li>`).join('')}</ul>
        </div>`;
    }

    return html;
}

function renderError(message) {
    return `<div class="error-box">❌ Lỗi: ${message}</div>`;
}

function renderShapChart(contributions, title) {
    const sorted = Object.entries(contributions)
        .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
    const maxVal = Math.max(...sorted.map(([, v]) => Math.abs(v)), 0.001);

    let html = `<h3 style="font-size:0.9rem;font-weight:600;color:#3b82f6;margin-bottom:12px;">📊 ${title}</h3>`;

    sorted.forEach(([feature, value]) => {
        const pct = (Math.abs(value) / maxVal) * 45;
        const isPos = value >= 0;
        const fillClass = isPos ? 'positive' : 'negative';
        const fillStyle = isPos
            ? `right:50%;width:${pct}%;`
            : `left:50%;width:${pct}%;`;
        const valueColor = isPos ? '#ef4444' : '#3b82f6';

        html += `
            <div class="shap-bar">
                <span class="shap-label">${feature}</span>
                <div class="shap-bar-track">
                    <div class="shap-center-line"></div>
                    <div class="shap-bar-fill ${fillClass}" style="${fillStyle}"></div>
                </div>
                <span class="shap-value" style="color:${valueColor}">${value >= 0 ? '+' : ''}${value.toFixed(4)}</span>
            </div>
        `;
    });

    return `<div class="shap-chart-container">${html}</div>`;
}


// ---- Weather Auto-Fill Logic ----
async function fetchAndPopulateWeather(lat, lon, locationName) {
    const statusEl = document.getElementById('location-status');
    statusEl.style.display = 'block';
    statusEl.style.color = '#3b82f6';
    statusEl.textContent = `Đang tải thời tiết cho ${locationName}...`;

    try {
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=relative_humidity_2m&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_direction_10m_dominant,shortwave_radiation_sum,precipitation_probability_max&timezone=auto`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Không thể tải dữ liệu thời tiết');

        const data = await res.json();

        const forms = ['predict-form', 'explain-form', 'scenario-form-a', 'scenario-form-b'];
        forms.forEach(formId => {
            const form = document.getElementById(formId);
            if (form) {
                form.querySelector('[name="humidity"]').value = data.current.relative_humidity_2m;
                form.querySelector('[name="precip"]').value = data.daily.precipitation_sum[0] || 0;
                form.querySelector('[name="tempmax"]').value = data.daily.temperature_2m_max[0];
                form.querySelector('[name="tempmin"]').value = data.daily.temperature_2m_min[0];
                form.querySelector('[name="winddir"]').value = data.daily.wind_direction_10m_dominant[0];
                form.querySelector('[name="windspeed"]').value = data.daily.wind_speed_10m_max[0];
                form.querySelector('[name="precipcover"]').value = data.daily.precipitation_probability_max[0] || 0;
                form.querySelector('[name="solarenergy"]').value = data.daily.shortwave_radiation_sum[0] || 0;
            }
        });

        statusEl.style.color = '#10b981';
        statusEl.textContent = `✅ Lấy dữ liệu thành công: ${locationName} (${lat.toFixed(2)}, ${lon.toFixed(2)})`;
    } catch (err) {
        statusEl.style.color = '#ef4444';
        statusEl.textContent = `❌ Lỗi: ${err.message}`;
    }
}

document.getElementById('btn-get-gps').addEventListener('click', async () => {
    setLoading('btn-get-gps', true);
    try {
        const pos = await new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 10000 }));
        await fetchAndPopulateWeather(pos.coords.latitude, pos.coords.longitude, 'Vị trí của bạn');
    } catch (err) {
        const statusEl = document.getElementById('location-status');
        statusEl.style.display = 'block';
        statusEl.style.color = '#ef4444';
        statusEl.textContent = err.code === 1 ? '❌ Vui lòng cấp quyền truy cập vị trí.' : `❌ Lỗi GPS: ${err.message}`;
    } finally {
        setLoading('btn-get-gps', false);
    }
});

document.getElementById('btn-search-city').addEventListener('click', async () => {
    const city = document.getElementById('city-input').value.trim();
    if (!city) return;

    setLoading('btn-search-city', true);
    const statusEl = document.getElementById('location-status');
    statusEl.style.display = 'block';
    statusEl.style.color = '#3b82f6';
    statusEl.textContent = `Đang tìm tọa độ cho "${city}"...`;

    try {
        const geocodeRes = await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1&language=vi`);
        const geocodeData = await geocodeRes.json();

        if (!geocodeData.results || geocodeData.results.length === 0) {
            throw new Error('Không tìm thấy địa điểm này');
        }

        const loc = geocodeData.results[0];
        await fetchAndPopulateWeather(loc.latitude, loc.longitude, `${loc.name}, ${loc.country || ''}`);
    } catch (err) {
        statusEl.style.color = '#ef4444';
        statusEl.textContent = `❌ ${err.message}`;
    } finally {
        setLoading('btn-search-city', false);
    }
});

// ---- Predict Tab ----
document.getElementById('predict-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = getFormData('predict-form');
    const resultEl = document.getElementById('predict-result');

    setLoading('predict-btn', true);
    resultEl.innerHTML = '<div class="result-placeholder"><div class="placeholder-icon">⏳</div><p>Đang chạy dự đoán XGBoost + phân tích Gemini...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/predict/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let predictionData = null;
        let streamedText = '';
        let hasStartedStreaming = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    var currentEvent = line.substring(6).trim();
                } else if (line.startsWith('data:') && currentEvent) {
                    const jsonData = line.substring(5).trim();
                    try {
                        const parsed = JSON.parse(jsonData);

                        if (currentEvent === 'prediction') {
                            predictionData = parsed;
                            resultEl.innerHTML = renderPredictionCards(predictionData) +
                                '<div class="advisory-section"><h3>🤖 Tư vấn AI (đang tải...)</h3>' +
                                '<div class="streaming-text streaming-cursor" id="streaming-advisory"></div></div>';
                        } else if (currentEvent === 'advisory') {
                            hasStartedStreaming = true;
                            streamedText += parsed.text || '';
                            const el = document.getElementById('streaming-advisory');
                            if (el) el.textContent = streamedText;
                        } else if (currentEvent === 'done') {
                            const el = document.getElementById('streaming-advisory');
                            if (el) el.classList.remove('streaming-cursor');

                            try {
                                let cleaned = streamedText.trim();
                                if (cleaned.startsWith('```json')) cleaned = cleaned.substring(7);
                                if (cleaned.startsWith('```')) cleaned = cleaned.substring(3);
                                if (cleaned.endsWith('```')) cleaned = cleaned.slice(0, -3);
                                const advisory = JSON.parse(cleaned.trim());
                                resultEl.innerHTML = renderPredictionCards(predictionData) + renderAdvisory(advisory);
                            } catch {
                                // Keep streamed text as-is if not JSON
                            }
                        }
                    } catch { /* ignore parse errors */ }
                }
            }
        }
    } catch (err) {
        resultEl.innerHTML = renderError(err.message);
    } finally {
        setLoading('predict-btn', false);
    }
});


// ---- Explain Tab ----
document.getElementById('explain-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = getFormData('explain-form');
    const resultEl = document.getElementById('explain-result');

    setLoading('explain-btn', true);
    resultEl.innerHTML = '<div class="result-placeholder"><div class="placeholder-icon">⏳</div><p>Đang tính giá trị SHAP + giải thích từ Gemini...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/explain/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let predictionData = null;
        let shapData = null;
        let streamedText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    var currentEvent = line.substring(6).trim();
                } else if (line.startsWith('data:') && currentEvent) {
                    const jsonData = line.substring(5).trim();
                    try {
                        const parsed = JSON.parse(jsonData);

                        if (currentEvent === 'prediction') {
                            predictionData = parsed;
                            resultEl.innerHTML = renderPredictionCards(predictionData) +
                                '<div id="shap-section"></div>' +
                                '<div class="advisory-section"><h3>🧠 Giải thích từ LLM (đang tải...)</h3>' +
                                '<div class="streaming-text streaming-cursor" id="streaming-explain"></div></div>';
                        } else if (currentEvent === 'shap') {
                            shapData = parsed.data;
                            const shapEl = document.getElementById('shap-section');
                            if (shapEl && shapData) {
                                shapEl.innerHTML =
                                    renderShapChart(shapData.tempmax_contributions, 'SHAP — Đóng góp TempMax') +
                                    renderShapChart(shapData.tempmin_contributions, 'SHAP — Đóng góp TempMin');
                            }
                        } else if (currentEvent === 'text') {
                            streamedText += parsed.data || '';
                            const el = document.getElementById('streaming-explain');
                            if (el) el.textContent = streamedText;
                        } else if (currentEvent === 'done') {
                            const el = document.getElementById('streaming-explain');
                            if (el) el.classList.remove('streaming-cursor');
                        }
                    } catch { /* ignore */ }
                }
            }
        }
    } catch (err) {
        resultEl.innerHTML = renderError(err.message);
    } finally {
        setLoading('explain-btn', false);
    }
});


// ---- Scenario Tab ----
document.getElementById('scenario-btn').addEventListener('click', async () => {
    const dataA = getFormData('scenario-form-a');
    const dataB = getFormData('scenario-form-b');
    const resultPanel = document.getElementById('scenario-result-panel');
    const resultEl = document.getElementById('scenario-result');

    setLoading('scenario-btn', true);
    resultPanel.style.display = 'block';
    resultEl.innerHTML = '<div class="result-placeholder"><div class="placeholder-icon">⏳</div><p>Đang chạy cả hai kịch bản + so sánh từ Gemini...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/scenario/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario_a: dataA, scenario_b: dataB }),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let predictionsData = null;
        let streamedText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('event:')) {
                    var currentEvent = line.substring(6).trim();
                } else if (line.startsWith('data:') && currentEvent) {
                    const jsonData = line.substring(5).trim();
                    try {
                        const parsed = JSON.parse(jsonData);

                        if (currentEvent === 'predictions') {
                            predictionsData = parsed.data;
                            const predA = predictionsData.scenario_a.prediction;
                            const predB = predictionsData.scenario_b.prediction;
                            const diff = predictionsData.differences;

                            const diffMaxClass = diff.tempmax_diff > 0 ? 'positive' : diff.tempmax_diff < 0 ? 'negative' : 'neutral';
                            const diffMinClass = diff.tempmin_diff > 0 ? 'positive' : diff.tempmin_diff < 0 ? 'negative' : 'neutral';

                            resultEl.innerHTML = `
                                <div class="scenario-diff">
                                    <div class="diff-card">
                                        <div class="label">Kịch bản A — Nhiệt độ Tối đa / Tối thiểu</div>
                                        <div class="value" style="color:#ef4444">${predA.tempmax}°C</div>
                                        <div class="value" style="color:#3b82f6;font-size:1.2rem">${predA.tempmin}°C</div>
                                    </div>
                                    <div class="diff-card">
                                        <div class="label">Kịch bản B — Nhiệt độ Tối đa / Tối thiểu</div>
                                        <div class="value" style="color:#ef4444">${predB.tempmax}°C</div>
                                        <div class="value" style="color:#3b82f6;font-size:1.2rem">${predB.tempmin}°C</div>
                                    </div>
                                </div>
                                <div class="scenario-diff">
                                    <div class="diff-card">
                                        <div class="label">Thay đổi Nhiệt độ Tối đa (B - A)</div>
                                        <div class="value ${diffMaxClass}">${diff.tempmax_diff > 0 ? '+' : ''}${diff.tempmax_diff}°C</div>
                                    </div>
                                    <div class="diff-card">
                                        <div class="label">Thay đổi Nhiệt độ Tối thiểu (B - A)</div>
                                        <div class="value ${diffMinClass}">${diff.tempmin_diff > 0 ? '+' : ''}${diff.tempmin_diff}°C</div>
                                    </div>
                                </div>
                                <div class="advisory-section">
                                    <h3>🔄 Phân tích Kịch bản AI (đang tải...)</h3>
                                    <div class="streaming-text streaming-cursor" id="streaming-scenario"></div>
                                </div>
                            `;
                        } else if (currentEvent === 'text') {
                            streamedText += parsed.data || '';
                            const el = document.getElementById('streaming-scenario');
                            if (el) el.textContent = streamedText;
                        } else if (currentEvent === 'done') {
                            const el = document.getElementById('streaming-scenario');
                            if (el) el.classList.remove('streaming-cursor');
                        }
                    } catch { /* ignore */ }
                }
            }
        }
    } catch (err) {
        resultEl.innerHTML = renderError(err.message);
    } finally {
        setLoading('scenario-btn', false);
    }
});
