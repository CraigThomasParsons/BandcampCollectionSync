
// View Switching
function setView(viewName) {
    document.querySelectorAll('.view-panel').forEach(el => el.classList.remove('active'));
    document.getElementById('view-' + viewName).classList.add('active');
}

// Data Fetching
async function fetchStatus() {
    try {
        const [statusRes, queueRes, logsRes] = await Promise.all([
            fetch('/api/status'),
            fetch('/api/queue'),
            fetch('/api/logs')
        ]);

        const statusData = await statusRes.json();
        const queueData = await queueRes.json();
        const logsData = await logsRes.json();

        updateHeader(true);
        updateSystemd(statusData.systemd);
        updateQueue(queueData.counts);
        updateCurrentJob(queueData.current_job);
        updateQueue(queueData.counts);
        updateCurrentJob(queueData.current_job);
        updateLogs(logsData.logs);

        // Separate fetch for collection to not block essential pulse if it's heavy?
        // Actually, let's just do it here for simplicity.
        const collectionRes = await fetch('/api/collection');
        const collectionData = await collectionRes.json();
        updateCollection(collectionData);

    } catch (e) {
        console.error("Fetch failed", e);
        updateHeader(false);
    }
}

function updateHeader(alive) {
    const el = document.getElementById('header-status');
    if (alive) {
        el.textContent = "STATUS: ONLINE - " + new Date().toLocaleTimeString();
        el.style.color = "black";
    } else {
        el.textContent = "STATUS: OFFLINE";
        el.style.color = "red";
    }
}

function updateQueue(counts) {
    document.getElementById('count-pending').textContent = counts.pending;
    document.getElementById('count-in-progress').textContent = counts.in_progress;
    document.getElementById('count-failed').textContent = counts.failed;
    document.getElementById('count-done').textContent = counts.done;
}

function updateSystemd(units) {
    const container = document.getElementById('systemd-stats');
    container.innerHTML = '';

    for (const [unit, status] of Object.entries(units)) {
        const row = document.createElement('div');
        row.className = 'systemd-item';

        let colorClass = 'inactive';
        if (status === 'active') colorClass = 'active';
        if (status === 'failed') colorClass = 'failed';

        // Simplify name "bandcamp-sync-reconcile.service" -> "reconcile"
        let shortName = unit.replace('bandcamp-sync-', '').replace('.service', '').replace('.path', ' (path)');

        row.innerHTML = `
            <span>${shortName}</span>
            <div style="display:flex; align-items:center;">
                <span class="dot ${colorClass}"></span>
                <small>${status}</small>
            </div>
        `;
        container.appendChild(row);
    }
}

function updateCurrentJob(job) {
    const container = document.getElementById('job-details');
    if (!job) {
        container.innerHTML = "<p>IDLE. SENSORS DETECT NO ACTIVE JOBS.</p>";
        return;
    }

    // Parse content if possible (Assuming URL)
    container.innerHTML = `
        <div style="margin-bottom:10px;"><strong>FILE:</strong> ${job.filename}</div>
        <div style="margin-bottom:10px;"><strong>CONTENT:</strong> ${job.content}</div>
        <div><strong>MODIFIED:</strong> ${new Date(job.mtime * 1000).toLocaleString()}</div>
    `;
}

function updateLogs(logs) {
    // logs is dict {filename: [lines]}
    // Merge for "Recent Activity"

    let allLines = [];
    for (const [filename, lines] of Object.entries(logs)) {
        lines.forEach(line => {
            allLines.push(`[${filename}] ${line}`);
        });
    }

    // Naive display
    const miniConsole = document.getElementById('mini-logs');
    const fullConsole = document.getElementById('full-logs');

    // Just join them all for now, maybe slice last 10 for mini
    const text = allLines.join('\n');

    miniConsole.textContent = text; // CSS handles overflow
    fullConsole.textContent = text;
}

function updateCollection(data) {
    const targets = [
        { body: 'collection-list-body', warning: 'collection-warning' },
        { body: 'collection-list-body-dashboard', warning: 'collection-warning-dashboard' }
    ];

    targets.forEach(target => {
        const tbody = document.getElementById(target.body);
        const warning = document.getElementById(target.warning);

        if (!tbody) return; // specific view might not exist or be loaded? (though they are in DOM)

        if (data.status === 'missing_file') {
            if (warning) warning.style.display = 'block';
            tbody.innerHTML = '<tr><td colspan="3">No collection data available.</td></tr>';
            return;
        } else {
            if (warning) warning.style.display = 'none';
        }

        tbody.innerHTML = ''; // Clear existing

        data.items.forEach(item => {
            const row = document.createElement('tr');

            let colorClass = 'lcars-text-gray';
            if (item.status === 'DOWNLOADED') colorClass = 'lcars-text-orange';
            if (item.status === 'PENDING') colorClass = 'lcars-text-yellow';
            if (item.status === 'FAILED') colorClass = 'lcars-text-red';
            if (item.status === 'IN_PROGRESS') colorClass = 'lcars-text-blue';

            row.innerHTML = `
                <td class="${colorClass}">${item.status}</td>
                <td>${item.artist}</td>
                <td>${item.title}</td>
            `;
            tbody.appendChild(row);
        });
    });
}

// Init
setInterval(fetchStatus, 3000);
fetchStatus();
