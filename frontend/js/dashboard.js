const API_URL = 'https://fairaid.onrender.com/api';

// Auth Check
const token = localStorage.getItem('fairaid_token');
const ngoName = localStorage.getItem('fairaid_ngo');

if (!token) {
    window.location.href = 'index.html';
}

document.getElementById('userNgoName').textContent = ngoName || 'NGO';

document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem('fairaid_token');
    localStorage.removeItem('fairaid_ngo');
    window.location.href = 'index.html';
});

// UI Elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadAlert = document.getElementById('uploadAlert');
const controlsSection = document.getElementById('controlsSection');
const resultsSection = document.getElementById('resultsSection');
const analyzeBtn = document.getElementById('analyzeBtn');
const thresholdSlider = document.getElementById('thresholdSlider');
const thresholdValue = document.getElementById('thresholdValue');
const aiInsightBtn = document.getElementById('aiInsightBtn');
const aiInsightResult = document.getElementById('aiInsightResult');
const aiRecBtn = document.getElementById('aiRecBtn');
const aiRecResult = document.getElementById('aiRecResult');
const firebaseStatus = document.getElementById('firebaseStatus');

let currentAnalysisData = null;

// Utility
function getHeaders() {
    return {
        'Authorization': `Bearer ${token}`
    };
}

// Initial Check - see if data exists
async function checkStatus() {
    try {
        const res = await fetch(`${API_URL}/status`, { headers: getHeaders() });
        if (res.status === 401) {
            localStorage.removeItem('fairaid_token');
            window.location.href = 'index.html';
            return;
        }
        const data = await res.json();
        if (data.has_data) {
            controlsSection.classList.remove('hidden');
            // Auto run analysis
            runAnalysis();
        }
    } catch (e) {
        console.error("Status check failed", e);
    }
}

checkStatus();

// Upload Logic
uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--primary)';
    uploadArea.style.backgroundColor = 'rgba(79, 70, 229, 0.05)';
});

uploadArea.addEventListener('dragleave', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--border-color)';
    uploadArea.style.backgroundColor = 'transparent';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = 'var(--border-color)';
    uploadArea.style.backgroundColor = 'transparent';
    
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        handleUpload();
    }
});

fileInput.addEventListener('change', handleUpload);

async function handleUpload() {
    if (!fileInput.files.length) return;
    
    const file = fileInput.files[0];
    if (!file.name.endsWith('.csv')) {
        showUploadAlert('Please upload a valid CSV file.', false);
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    uploadArea.innerHTML = '<div class="upload-icon">⏳</div><h3>Uploading...</h3>';

    try {
        const res = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            headers: getHeaders(),
            body: formData
        });
        
        const data = await res.json();
        
        if (res.ok) {
            showUploadAlert('Data uploaded successfully!', true);
            controlsSection.classList.remove('hidden');
            runAnalysis();
        } else {
            showUploadAlert(data.message || 'Upload failed', false);
        }
    } catch (err) {
        showUploadAlert('Server error during upload.', false);
    } finally {
        uploadArea.innerHTML = `
            <div class="upload-icon">📂</div>
            <h3>Click to upload CSV</h3>
            <p class="text-muted mt-2">${file.name}</p>
        `;
    }
}

function showUploadAlert(msg, isSuccess) {
    uploadAlert.textContent = msg;
    uploadAlert.className = `alert ${isSuccess ? 'bg-success status-success' : 'bg-error status-error'} show`;
}

// Slider Logic
thresholdSlider.addEventListener('input', (e) => {
    thresholdValue.textContent = parseFloat(e.target.value).toFixed(1);
});

// Analyze Logic
analyzeBtn.addEventListener('click', runAnalysis);

async function runAnalysis() {
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Analyzing...';
    
    const threshold = parseFloat(thresholdSlider.value);

    try {
        const res = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            headers: {
                ...getHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ threshold })
        });
        
        const data = await res.json();
        
        if (res.ok) {
            currentAnalysisData = data;
            renderResults(data);
            resultsSection.classList.remove('hidden');
            aiInsightResult.classList.add('hidden'); 
            aiInsightResult.innerHTML = '';
            aiRecResult.classList.add('hidden');
            aiRecResult.innerHTML = '';
            
            if (data.firebase_synced) {
                firebaseStatus.classList.remove('hidden');
            } else {
                firebaseStatus.classList.add('hidden');
            }
        } else {
            alert(data.message || "Analysis failed");
        }
    } catch (err) {
        alert("Server error during analysis.");
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Run Analysis';
    }
}

function renderResults(data) {
    // Metrics
    document.getElementById('metricTotal').textContent = data.total_people;
    document.getElementById('metricHighNeed').textContent = data.high_need_count;
    document.getElementById('metricSatisfaction').textContent = `${(data.satisfaction_rate * 100).toFixed(0)}%`;

    // Status Box
    const statusAlert = document.getElementById('statusAlert');
    statusAlert.className = `alert bg-${data.status_type} status-${data.status_type} show border-left-4`;
    statusAlert.innerHTML = `<strong>Status:</strong> ${data.status_msg}`;

    // Tables
    renderTable('topPeopleTable', data.top_people, row => `
        <tr>
            <td>#${row.ID}</td>
            <td><strong>${row.NeedScore.toFixed(2)}</strong></td>
            <td><span class="badge ${row.ReceivedHelp.toLowerCase() === 'yes' ? 'badge-green' : 'badge-red'}">${row.ReceivedHelp}</span></td>
        </tr>
    `);

    renderTable('unfairCasesTable', data.unfair_cases, row => `
        <tr>
            <td>#${row.ID}</td>
            <td class="status-error"><strong>${row.NeedScore.toFixed(2)}</strong></td>
        </tr>
    `);

    renderTable('predictionsTable', data.predictions, row => `
        <tr>
            <td>#${row.ID}</td>
            <td>${row.NeedScore.toFixed(2)}</td>
            <td><span class="badge ${row.HelpNumeric === 1 ? 'badge-green' : 'badge-red'}">${row.HelpNumeric === 1 ? 'Yes' : 'No'}</span></td>
            <td><span class="badge ${row.PredictedHelp === 1 ? 'badge-green' : 'badge-red'}">${row.PredictedHelp === 1 ? 'Yes' : 'No'}</span></td>
        </tr>
    `);

    // Recommendations
    const recList = document.getElementById('recommendationList');
    recList.innerHTML = data.recommendations.map(r => `<li>${r}</li>`).join('');
}

function renderTable(tableId, dataArray, rowHtmlFn) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!dataArray || dataArray.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No data available</td></tr>';
        return;
    }
    tbody.innerHTML = dataArray.map(rowHtmlFn).join('');
}

// AI Insight Logic
if(aiInsightBtn) {
    aiInsightBtn.addEventListener('click', async () => {
        if (!currentAnalysisData) return;

        aiInsightBtn.disabled = true;
        aiInsightBtn.textContent = 'Generating...';
        aiInsightResult.classList.remove('hidden');
        aiInsightResult.innerHTML = '<span class="text-muted">Analyzing data with OpenRouter... ⏳</span>';

        try {
            const payload = {
                satisfaction: `${(currentAnalysisData.satisfaction_rate * 100).toFixed(0)}%`,
                high_need_count: currentAnalysisData.high_need_count,
                unfair_count: currentAnalysisData.unfair_cases.length
            };

            const res = await fetch(`${API_URL}/insights`, {
                method: 'POST',
                headers: {
                    ...getHeaders(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            if (res.ok) {
                const formattedText = data.insight.replace(/\n/g, '<br>');
                aiInsightResult.innerHTML = `<strong>Insights:</strong><br>${formattedText}`;
            } else {
                aiInsightResult.innerHTML = `<span class="status-error">${data.message || 'Failed to generate insights'}</span>`;
            }
        } catch (err) {
            aiInsightResult.innerHTML = `<span class="status-error">Server error during AI generation.</span>`;
        } finally {
            aiInsightBtn.disabled = false;
            aiInsightBtn.textContent = 'Generate AI Insights';
        }
    });
}

// AI Recommendation Logic
if(aiRecBtn) {
    aiRecBtn.addEventListener('click', async () => {
        if (!currentAnalysisData) return;

        aiRecBtn.disabled = true;
        aiRecBtn.textContent = 'Generating...';
        aiRecResult.classList.remove('hidden');
        aiRecResult.innerHTML = '<span class="text-muted">Analyzing data with OpenRouter... ⏳</span>';

        try {
            const payload = {
                satisfaction: `${(currentAnalysisData.satisfaction_rate * 100).toFixed(0)}%`,
                high_need_count: currentAnalysisData.high_need_count,
                unfair_count: currentAnalysisData.unfair_cases.length
            };

            const res = await fetch(`${API_URL}/recommendations`, {
                method: 'POST',
                headers: {
                    ...getHeaders(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            if (res.ok) {
                const formattedText = data.insight.replace(/\n/g, '<br>');
                aiRecResult.innerHTML = `<strong>Recommendations:</strong><br>${formattedText}`;
            } else {
                aiRecResult.innerHTML = `<span class="status-error">${data.message || 'Failed to generate recommendations'}</span>`;
            }
        } catch (err) {
            aiRecResult.innerHTML = `<span class="status-error">Server error during AI generation.</span>`;
        } finally {
            aiRecBtn.disabled = false;
            aiRecBtn.textContent = 'Generate AI Recommendations';
        }
    });
}
