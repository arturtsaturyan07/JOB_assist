const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const optionsContainer = document.getElementById('options-container');
const jobsPanelContent = document.getElementById('jobs-panel-content');

// Connect to WebSocket
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
const ws = new WebSocket(wsUrl);

// Global state for jobs to support filtering
let currentSingleJobs = [];
let currentPairJobs = [];
let currentScheduleData = [];
let currentTab = 'single';

ws.onopen = () => {
    console.log('Connected to chat server');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    console.log('WebSocket message received:', data);

    // Handle CV Analysis results specifically
    if (data.type === 'cv_analysis') {
        const skills = data.skills.join(', ');
        // We handle the text message part separately, this just updates internal state if needed
        // But mainly the server sends a text message after this JSON
    }

    if (data.type === 'text' || data.type === 'choice') {
        addMessage(data.message, 'bot');

        if (data.options && data.options.length > 0) {
            showOptions(data.options);
        } else {
            optionsContainer.innerHTML = ''; // Clear options if none
        }
    }

    // Handle job data in side panel
    if (data.type === 'jobs' || (data.single_jobs && data.single_jobs.length > 0)) {
        console.log('Displaying jobs in panel:', data.single_jobs, data.pair_jobs);
        currentSingleJobs = data.single_jobs || [];
        currentPairJobs = data.pair_jobs || [];
        currentScheduleData = data.schedule_data || [];
        displayJobsInPanel(); // Refresh display with new data
    }
};

ws.onclose = () => {
    addMessage('Connection lost. Please refresh the page.', 'bot');
};

// --- UI Toggle Functions ---

function toggleCVUpload() {
    const modal = document.getElementById('cv-modal');
    modal.style.display = modal.style.display === 'block' ? 'none' : 'block';
}

function toggleMarketInsights() {
    const modal = document.getElementById('market-modal');
    modal.style.display = modal.style.display === 'block' ? 'none' : 'block';

    if (modal.style.display === 'block') {
        // Mock loading content
        const content = document.getElementById('market-insights-content');
        content.innerHTML = '<div class="market-loading">Fetching latest market data...</div>';

        // Simulating fetch
        setTimeout(() => {
            content.innerHTML = `
                <div class="insight-card">
                    <h4>🔥 Top Skills in Armenia</h4>
                    <p>Python, React, Node.js, English (C1)</p>
                </div>
                <div class="insight-card">
                    <h4>💰 Salary Trends (Junior/Mid)</h4>
                    <p>Dev: 400k - 800k AMD/mo</p>
                    <p>Service: 150k - 300k AMD/mo</p>
                </div>
            `;
        }, 1500);
    }
}

function submitCV() {
    const cvText = document.getElementById('cv-text').value.trim();
    const fileInput = document.getElementById('cv-file');
    const file = fileInput.files[0];

    if (!cvText && !file) {
        alert("Please paste your CV text or select a file.");
        return;
    }

    // Handle File Upload
    if (file) {
        const formData = new FormData();
        formData.append('file', file);

        addMessage(`📄 Uploading ${file.name}...`, "user");
        toggleCVUpload(); // Close modal

        fetch('/upload_cv', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    console.log("CV Upload parsed successfully");
                    // Relay the parsed text to the WebSocket conversation
                    ws.send(JSON.stringify({
                        type: "cv_upload",
                        content: data.text
                    }));
                } else {
                    addMessage("❌ CV Upload failed: " + data.error, "bot");
                }
            })
            .catch(error => {
                addMessage("❌ CV Upload error. Please try just pasting text.", "bot");
                console.error(error);
            });

        // Clear inputs
        document.getElementById('cv-text').value = "";
        fileInput.value = "";
        return;
    }

    // Handle Text Paste (Legacy)
    if (cvText.length < 50) {
        alert("Please paste a longer CV (at least 50 characters).");
        return;
    }

    // Close modal
    toggleCVUpload();

    // Show user action
    addMessage("📄 Uploaded CV (Text)", "user");

    // Send to backend
    ws.send(JSON.stringify({
        type: "cv_upload",
        content: cvText
    }));

    // Clear textarea
    document.getElementById('cv-text').value = "";
}

function switchJobTab(tabName) {
    currentTab = tabName;

    // Update active state of buttons
    document.querySelectorAll('.job-tab').forEach(btn => {
        if (btn.textContent.toLowerCase() === tabName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    displayJobsInPanel();
}

// --- Display Logic ---

function displayJobsInPanel(singleJobs = currentSingleJobs, pairJobs = currentPairJobs) {
    jobsPanelContent.innerHTML = '';

    if (singleJobs.length === 0 && pairJobs.length === 0) {
        jobsPanelContent.innerHTML = `
            <div class="jobs-panel-empty">
                <i class="fas fa-search"></i>
                <p>No jobs found yet.</p>
                <span>Chat with me to find your perfect match!</span>
            </div>
        `;
        return;
    }

    // Filter based on currentTab
    if (currentTab === 'single') {
        if (singleJobs.length > 0) {
            singleJobs.forEach((job, index) => {
                const card = createJobCardPanel(job, index + 1, 'single');
                jobsPanelContent.appendChild(card);
            });
        } else {
            jobsPanelContent.innerHTML = '<div class="jobs-panel-empty"><p>No single jobs found.</p></div>';
        }
    }
    else if (currentTab === 'pairs') {
        if (pairJobs.length > 0) {
            pairJobs.forEach((pair, index) => {
                const card = createJobPairCardPanel(pair, index + 1);
                jobsPanelContent.appendChild(card);
            });
        } else {
            jobsPanelContent.innerHTML = '<div class="jobs-panel-empty"><p>No job pairs found.</p></div>';
        }
    }
    else if (currentTab === 'schedule') {
        if (currentScheduleData && currentScheduleData.length > 0) {
            jobsPanelContent.innerHTML = '<div class="schedule-container" style="display:flex; flex-direction:column; gap:10px;"></div>';
            const container = jobsPanelContent.firstChild;

            // Group by Day
            const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
            days.forEach(day => {
                const dayRow = document.createElement('div');
                dayRow.style.cssText = 'background: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;';

                const header = document.createElement('div');
                header.textContent = day;
                header.style.cssText = 'font-weight: bold; margin-bottom: 8px; color: #475569;';
                dayRow.appendChild(header);

                const timeline = document.createElement('div');
                timeline.style.cssText = 'position: relative; height: 40px; background: #e2e8f0; border-radius: 20px; overflow: hidden;';

                // Add hour markers (simplified)

                // Add Job Blocks
                currentScheduleData.forEach((job, idx) => {
                    const block = job.schedule.find(b => b.day === day);
                    if (block) {
                        const startH = parseInt(block.start.split(':')[0]) + parseInt(block.start.split(':')[1]) / 60;
                        const endH = parseInt(block.end.split(':')[0]) + parseInt(block.end.split(':')[1]) / 60;

                        // Normalize 0-24h to 0-100%
                        const left = ((startH) / 24) * 100;
                        const width = ((endH - startH) / 24) * 100;

                        const bar = document.createElement('div');
                        const color = idx % 2 === 0 ? '#3b82f6' : '#10b981';
                        bar.style.cssText = `position: absolute; left: ${left}%; width: ${width}%; top: 5px; bottom: 5px; background: ${color}; border-radius: 4px; font-size: 10px; color: white; display: flex; align-items: center; justify-content: center; overflow: hidden; white-space: nowrap; padding: 0 4px; cursor: title;`;
                        bar.title = `${job.title} (${block.start}-${block.end})`;
                        bar.textContent = job.title;
                        timeline.appendChild(bar);
                    }
                });

                dayRow.appendChild(timeline);
                container.appendChild(dayRow);
            });

            // Legend
            const legend = document.createElement('div');
            legend.style.cssText = "margin-top: 10px; font-size: 12px; color: #64748b; text-align: center;";
            legend.textContent = "Time: 00:00 - 24:00";
            container.appendChild(legend);

        } else {
            jobsPanelContent.innerHTML = `
                <div class="jobs-panel-empty">
                    <i class="fas fa-calendar-alt"></i>
                    <p>No schedule data yet.</p>
                </div>
            `;
        }
    }
}

function createJobCardPanel(job, number, type) {
    const card = document.createElement('div');
    card.className = `job-card ${type}`;

    const rate = job.hourly_rate ? `$${job.hourly_rate.toFixed(0)}` : 'TBD';
    const weeklyIncome = job.weekly_pay ? `$${job.weekly_pay.toFixed(0)}` : 'TBD';

    card.innerHTML = `
        <div class="job-card-header">
            <div class="job-card-title">${escapeHtml(job.title)}</div>
            <span class="job-card-badge">#${number}</span>
        </div>
        <div class="job-card-company">
            <i class="fas fa-building"></i>
            ${escapeHtml(job.company || 'Company')}
        </div>
        <div class="job-card-location">
            <i class="fas fa-map-marker-alt"></i>
            ${escapeHtml(job.location)}
        </div>
        <div class="job-card-meta">
            <div class="job-meta-item">
                <div class="job-meta-label">Rate</div>
                <div class="job-meta-value">${rate}/hr</div>
            </div>
            <div class="job-meta-item">
                <div class="job-meta-label">Weekly</div>
                <div class="job-meta-value">${job.hours_per_week}h</div>
            </div>
        </div>
        <div class="job-card-meta">
            <div class="job-meta-item" style="grid-column: 1 / -1;">
                <div class="job-meta-label">Income</div>
                <div class="job-meta-value" style="color: #10b981;">${weeklyIncome}/week</div>
            </div>
        </div>
        ${job.apply_link ? `
        <a href="${job.apply_link}" target="_blank" rel="noopener noreferrer" class="job-card-button">
            <i class="fas fa-external-link-alt"></i> Apply Now
        </a>
        ` : ''}
    `;

    return card;
}

function createJobPairCardPanel(pair, number) {
    const card = document.createElement('div');
    card.className = 'job-card pair';

    const jobA = pair.jobs[0];
    const jobB = pair.jobs[1];
    const totalIncome = pair.total_pay ? `$${pair.total_pay.toFixed(0)}` : 'TBD';

    card.innerHTML = `
        <div class="job-card-header">
            <div class="job-card-title">Job Pair ${number}</div>
            <span class="job-card-badge pair">COMBO</span>
        </div>
        
        <div class="job-card-pair-info">
            <div class="job-pair-job"><strong>${escapeHtml(jobA.title)}</strong></div>
            <div class="job-pair-job">${escapeHtml(jobA.company)} • ${escapeHtml(jobA.location)}</div>
        </div>
        
        <div class="job-card-pair-info">
            <div class="job-pair-job"><strong>${escapeHtml(jobB.title)}</strong></div>
            <div class="job-pair-job">${escapeHtml(jobB.company)} • ${escapeHtml(jobB.location)}</div>
        </div>
        
        <div class="job-card-meta" style="margin-top: 12px;">
            <div class="job-meta-item">
                <div class="job-meta-label">Total Hours</div>
                <div class="job-meta-value">${pair.total_hours}h</div>
            </div>
            <div class="job-meta-item">
                <div class="job-meta-label">Combined</div>
                <div class="job-meta-value" style="color: #10b981;">${totalIncome}</div>
            </div>
        </div>
        
        <div style="margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            ${jobA.apply_link ? `
            <a href="${jobA.apply_link}" target="_blank" rel="noopener noreferrer" class="job-card-button" style="font-size: 0.85rem; padding: 8px;">
                <i class="fas fa-link"></i> Job 1
            </a>
            ` : ''}
            ${jobB.apply_link ? `
            <a href="${jobB.apply_link}" target="_blank" rel="noopener noreferrer" class="job-card-button" style="font-size: 0.85rem; padding: 8px;">
                <i class="fas fa-link"></i> Job 2
            </a>
            ` : ''}
        </div>
    `;

    return card;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;

    // Convert newlines to <br> for bot messages
    if (sender === 'bot') {
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = text.replace(/\n/g, '<br>');
        msgDiv.appendChild(contentDiv);

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        msgDiv.appendChild(timeDiv);
    } else {
        msgDiv.textContent = text;
    }

    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function sendMessage() {
    const text = messageInput.value.trim();
    if (text) {
        addMessage(text, 'user');
        ws.send(text);
        messageInput.value = '';
        optionsContainer.innerHTML = ''; // Clear options after sending
    }
}

function showOptions(options) {
    optionsContainer.innerHTML = '';
    options.forEach(option => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.textContent = option;
        btn.onclick = () => {
            messageInput.value = option;
            sendMessage();
        };
        optionsContainer.appendChild(btn);
    });
}

sendBtn.onclick = sendMessage;

messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Close modals when clicking outside
window.onclick = function (event) {
    const cvModal = document.getElementById('cv-modal');
    const marketModal = document.getElementById('market-modal');
    if (event.target == cvModal) {
        cvModal.style.display = "none";
    }
    if (event.target == marketModal) {
        marketModal.style.display = "none";
    }
}
