const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const optionsContainer = document.getElementById('options-container');
const jobsPanelContent = document.getElementById('jobs-panel-content');

// Connect to WebSocket
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
const ws = new WebSocket(wsUrl);

ws.onopen = () => {
    console.log('Connected to chat server');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    console.log('WebSocket message received:', data); // Debug log
    
    if (data.type === 'text' || data.type === 'choice') {
        addMessage(data.message, 'bot');
        
        if (data.options && data.options.length > 0) {
            showOptions(data.options);
        } else {
            optionsContainer.innerHTML = ''; // Clear options if none
        }
    }
    
    // Handle job data in side panel - check for type === 'jobs' OR direct single_jobs property
    if (data.type === 'jobs' || (data.single_jobs && data.single_jobs.length > 0)) {
        console.log('Displaying jobs in panel:', data.single_jobs, data.pair_jobs); // Debug log
        displayJobsInPanel(data.single_jobs || [], data.pair_jobs || []);
    }
};

ws.onclose = () => {
    addMessage('Connection lost. Please refresh the page.', 'bot');
};

function toggleJobsPanel() {
    const panel = document.getElementById('jobs-panel');
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
}

function displayJobsInPanel(singleJobs, pairJobs) {
    jobsPanelContent.innerHTML = '';
    
    if (singleJobs.length === 0 && pairJobs.length === 0) {
        jobsPanelContent.innerHTML = `
            <div class="jobs-panel-empty">
                <i class="fas fa-briefcase"></i>
                <p>No jobs found yet</p>
            </div>
        `;
        return;
    }
    
    // Add single jobs
    if (singleJobs.length > 0) {
        const singleHeader = document.createElement('div');
        singleHeader.style.cssText = 'font-weight: 700; color: #667eea; margin-bottom: 12px; font-size: 1rem;';
        singleHeader.textContent = '💼 Single Jobs';
        jobsPanelContent.appendChild(singleHeader);
        
        singleJobs.forEach((job, index) => {
            const card = createJobCardPanel(job, index + 1, 'single');
            jobsPanelContent.appendChild(card);
        });
    }
    
    // Add pair jobs
    if (pairJobs.length > 0) {
        const pairHeader = document.createElement('div');
        pairHeader.style.cssText = 'font-weight: 700; color: #f59e0b; margin-top: 20px; margin-bottom: 12px; font-size: 1rem;';
        pairHeader.textContent = '👥 Job Pairs';
        jobsPanelContent.appendChild(pairHeader);
        
        pairJobs.forEach((pair, index) => {
            const card = createJobPairCardPanel(pair, index + 1);
            jobsPanelContent.appendChild(card);
        });
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
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    
    // Convert newlines to <br> for bot messages
    if (sender === 'bot') {
        msgDiv.innerHTML = text.replace(/\n/g, '<br>');
    } else {
        msgDiv.textContent = text;
    }
    
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function addJobsDisplay(jobs) {
    const container = document.createElement('div');
    container.className = 'jobs-container';
    
    // Summary header
    const summary = document.createElement('div');
    summary.className = 'jobs-summary';
    summary.innerHTML = `
        <span class="summary-text">✨ Found ${jobs.length} amazing opportunities</span>
        <span class="summary-count">${jobs.length}</span>
    `;
    container.appendChild(summary);
    
    // Job cards
    jobs.forEach((job, index) => {
        const card = createJobCard(job, index + 1);
        container.appendChild(card);
    });
    
    chatContainer.appendChild(container);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function createJobCard(job, number) {
    const card = document.createElement('div');
    card.className = 'job-card ' + getJobCategory(job.title);
    
    // Get salary display
    const salary = job.hourly_rate ? `$${job.hourly_rate.toFixed(0)}/hr` : 'Negotiable';
    
    // Get remote status
    const isRemote = job.location.toLowerCase().includes('remote');
    const remoteIcon = isRemote ? '🌍' : '📍';
    
    card.innerHTML = `
        <div class="job-header">
            <div class="job-title">${escapeHtml(job.title)}</div>
            <div class="job-number">#${number}</div>
        </div>
        <div class="job-company">
            <i class="fas fa-building"></i>
            ${escapeHtml(job.company || 'Company')}
        </div>
        <div class="job-details">
            <div class="detail-badge salary">
                <i class="fas fa-dollar-sign"></i>
                ${salary}
            </div>
            <div class="detail-badge location">
                <i class="fas fa-map-marker-alt"></i>
                ${escapeHtml(job.location)}
            </div>
            ${job.hours_per_week ? `
            <div class="detail-badge hours">
                <i class="fas fa-clock"></i>
                ${job.hours_per_week}h/week
            </div>
            ` : ''}
            ${isRemote ? `
            <div class="detail-badge remote">
                <i class="fas fa-laptop"></i>
                Remote
            </div>
            ` : ''}
        </div>
        ${job.description ? `
        <div class="job-description">
            ${escapeHtml(job.description.substring(0, 150))}${job.description.length > 150 ? '...' : ''}
        </div>
        ` : ''}
        <div class="job-footer">
            <a href="${job.apply_link || '#'}" target="_blank" rel="noopener noreferrer" class="apply-btn">
                <i class="fas fa-external-link-alt"></i> Apply Now
            </a>
        </div>
    `;
    
    return card;
}

function getJobCategory(title) {
    const titleLower = title.toLowerCase();
    if (titleLower.includes('doctor') || titleLower.includes('physician') || titleLower.includes('surgeon')) return 'doctor';
    if (titleLower.includes('engineer') || titleLower.includes('architect')) return 'engineer';
    if (titleLower.includes('teacher') || titleLower.includes('instructor')) return 'teacher';
    if (titleLower.includes('nurse') || titleLower.includes('healthcare')) return 'nurse';
    if (titleLower.includes('developer') || titleLower.includes('programmer')) return 'developer';
    return '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
