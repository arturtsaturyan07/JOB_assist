const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const optionsContainer = document.getElementById('options-container');
const jobsPanelContent = document.getElementById('jobs-panel-content');

// Connect to WebSocket with Auto-Reconnect
let ws;
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

function connectWebSocket() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('Connected to chat server');
        const statusMsg = document.getElementById('connection-status');
        if (statusMsg) statusMsg.remove();

        // Enable input
        messageInput.disabled = false;
        messageInput.placeholder = "Type your answer...";
        document.getElementById('send-btn').disabled = false;
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WebSocket message received:', data);

        // Handle CV Analysis results
        if (data.type === 'cv_analysis') {
            // Processing logic
        }

        if (data.type === 'text' || data.type === 'choice') {
            addMessage(data.message, 'bot');
            if (data.options && data.options.length > 0) {
                showOptions(data.options);
            } else {
                optionsContainer.innerHTML = '';
            }
        }

        // Handle job data
        if (data.type === 'jobs' || (data.single_jobs && data.single_jobs.length > 0)) {
            console.log('Displaying jobs in panel:', data.single_jobs, data.pair_jobs);
            currentSingleJobs = data.single_jobs || [];
            currentPairJobs = data.pair_jobs || [];
            currentScheduleData = data.schedule_data || [];
            displayJobsInPanel();
        }
    };

    ws.onclose = () => {
        console.log('Connection lost. Reconnecting in 3s...');

        // Disable input
        messageInput.disabled = true;
        messageInput.placeholder = "Connecting to server...";
        document.getElementById('send-btn').disabled = true;

        // Show non-intrusive status
        if (!document.getElementById('connection-status')) {
            const status = document.createElement('div');
            status.id = 'connection-status';
            status.style.cssText = 'position: absolute; top: 10px; left: 50%; transform: translateX(-50%); background: #ef4444; color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.8rem; z-index: 1000;';
            status.textContent = 'Connection lost. Reconnecting...';
            document.body.appendChild(status);
        }
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
        console.error('WebSocket encountered error: ', err);
        ws.close();
    };
}

// Initial connection
connectWebSocket();

// Global state for jobs to support filtering
let currentSingleJobs = [];
let currentPairJobs = [];
let currentScheduleData = [];
let currentTab = 'single';



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
            jobsPanelContent.innerHTML = '<div class="schedule-container" style="display:flex; flex-direction:column; gap:20px; padding: 10px;"></div>';
            const container = jobsPanelContent.firstChild;

            const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
            days.forEach(day => {
                const dayBlock = document.createElement('div');
                dayBlock.className = 'schedule-day-block';
                dayBlock.style.cssText = 'background: white; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);';

                // Day Header
                const header = document.createElement('div');
                header.textContent = day;
                header.style.cssText = 'background: #f1f5f9; padding: 8px 16px; font-weight: 700; color: #334155; border-bottom: 1px solid #e2e8f0; font-size: 0.9rem;';
                dayBlock.appendChild(header);

                // Content Container
                const content = document.createElement('div');
                content.style.cssText = 'padding: 10px; display: flex; flex-direction: column; gap: 8px;';

                // Time Scale (Ruler)
                const ruler = document.createElement('div');
                ruler.style.cssText = 'display: flex; margin-left: 30%; height: 20px; border-bottom: 1px solid #cbd5e1; font-size: 0.7rem; color: #94a3b8; position: relative; margin-bottom: 5px;';
                [0, 6, 12, 18, 24].forEach(h => {
                    const mark = document.createElement('div');
                    mark.textContent = h;
                    mark.style.cssText = `position: absolute; left: ${(h / 24) * 100}%; transform: translateX(-50%); bottom: 2px;`;
                    ruler.appendChild(mark);
                });
                content.appendChild(ruler);

                let hasJobs = false;
                currentScheduleData.forEach((job, idx) => {
                    const block = job.schedule.find(b => b.day === day);
                    // Even if block is flexible/empty, we might want to show it? 
                    // For now only show if block exists or if it's "Flexible" (Remote)?
                    // My previous logic assigned [] to Remote.
                    // If block is undefined (empty schedule), we skip or show "Flexible"?

                    // Logic: If job has schedule, show bar. If flexible, show full width 'Flexible' text?
                    // Let's stick to showing active blocks for now to avoid clutter, or check if we want to show 'Flexible'

                    if (block || (job.schedule.length === 0)) { // Show even if flexible? 

                        hasJobs = true;
                        const row = document.createElement('div');
                        row.style.cssText = 'display: flex; align-items: center; height: 28px;';

                        // Job Title (Left)
                        const title = document.createElement('div');
                        title.textContent = job.title;
                        title.title = job.title; // Tooltip for full text
                        title.style.cssText = 'width: 30%; font-size: 0.75rem; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 10px;';
                        row.appendChild(title);

                        // Timeline Bar Area (Right)
                        const track = document.createElement('div');
                        track.style.cssText = 'width: 70%; height: 100%; position: relative; background: #f8fafc; border-radius: 4px; border: 1px solid #f1f5f9;';

                        // Render Bar
                        if (block) {
                            const startH = parseInt(block.start.split(':')[0]) + parseInt(block.start.split(':')[1]) / 60;
                            const endH = parseInt(block.end.split(':')[0]) + parseInt(block.end.split(':')[1]) / 60;
                            const left = (startH / 24) * 100;
                            const width = ((endH - startH) / 24) * 100;

                            const bar = document.createElement('div');
                            const color = idx % 2 === 0 ? '#3b82f6' : '#10b981';
                            bar.style.cssText = `position: absolute; left: ${left}%; width: ${width}%; top: 4px; bottom: 4px; background: ${color}; border-radius: 4px; opacity: 0.9; box-shadow: 0 1px 2px rgba(0,0,0,0.1);`;
                            bar.title = `${block.start} - ${block.end}`; // Tooltip
                            track.appendChild(bar);
                        } else {
                            // Flexible / Remote
                            const flex = document.createElement('div');
                            flex.textContent = "Flexible / Remote";
                            flex.style.cssText = 'width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; color: #94a3b8; font-style: italic; background: #f1f5f9;';
                            track.appendChild(flex);
                        }

                        row.appendChild(track);
                        content.appendChild(row);
                    }
                });

                if (!hasJobs) {
                    const empty = document.createElement('div');
                    empty.textContent = "No shifts scheduled";
                    empty.style.cssText = 'font-size: 0.8rem; color: #cbd5e1; text-align: center; padding: 10px;';
                    content.appendChild(empty);
                }

                dayBlock.appendChild(content);
                container.appendChild(dayBlock);
            });

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
        <a href="${job.apply_link || `https://www.google.com/search?q=${encodeURIComponent(job.title + ' ' + job.company + ' apply')}`}" target="_blank" rel="noopener noreferrer" class="job-card-button">
            <i class="fas fa-external-link-alt"></i> ${job.apply_link ? 'Apply Now' : 'Search to Apply'}
        </a>
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
            <a href="${jobA.apply_link || `https://www.google.com/search?q=${encodeURIComponent(jobA.title + ' ' + jobA.company + ' apply')}`}" target="_blank" rel="noopener noreferrer" class="job-card-button" style="font-size: 0.85rem; padding: 8px;">
                <i class="fas fa-link"></i> ${jobA.apply_link ? 'Apply Job 1' : 'Search Job 1'}
            </a>
            <a href="${jobB.apply_link || `https://www.google.com/search?q=${encodeURIComponent(jobB.title + ' ' + jobB.company + ' apply')}`}" target="_blank" rel="noopener noreferrer" class="job-card-button" style="font-size: 0.85rem; padding: 8px;">
                <i class="fas fa-link"></i> ${jobB.apply_link ? 'Apply Job 2' : 'Search Job 2'}
            </a>
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
