import os
import glob
import subprocess
import json
import hashlib
from flask import Flask, jsonify, send_from_directory, request

# Configuration
SYNC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Sync'))
INBOX_DIR = os.path.join(SYNC_ROOT, 'inbox')
LOGS_DIR = os.path.join(SYNC_ROOT, 'logs')
COLLECTION_FILE = os.path.join(os.path.dirname(SYNC_ROOT), 'collection.json') # /home/craigpar/BandcampSync/collection.json
UI_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../ui'))

app = Flask(__name__, static_folder=UI_DIR)

# Music Dir
MUSIC_DIR = os.path.expanduser("~/Music/Bandcamp")

def get_systemd_status(units):
    """
    Check the status of systemd units using systemctl --user.
    Returns a dict {unit_name: status_string}.
    """
    statuses = {}
    for unit in units:
        try:
            # Check ActiveState and SubState
            cmd = ['systemctl', '--user', 'show', unit, '--property=ActiveState,SubState,LoadState']
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            props = {}
            for line in result.stdout.splitlines():
                if '=' in line:
                    k, v = line.split('=', 1)
                    props[k] = v.strip()
            
            # Synthesize a status
            if props.get('LoadState') == 'not-found':
                 statuses[unit] = 'not-found'
            elif props.get('ActiveState') == 'active':
                statuses[unit] = 'active'
            elif props.get('ActiveState') == 'failed':
                 statuses[unit] = 'failed'
            else:
                 statuses[unit] = props.get('ActiveState', 'unknown')

        except Exception as e:
            statuses[unit] = f"error: {str(e)}"
    return statuses

def count_jobs():
    """
    Count jobs in queue directories.
    """
    counts = {
        'pending': 0,
        'in_progress': 0,
        'failed': 0,
        'done': 0
    }
    
    # Simple file counting assuming *.job or similar. 
    # If jobs are files, count files. If directories, count directories?
    # User said "Job files (*.job) contain ONE album URL per file."
    
    for state in counts.keys():
        path = os.path.join(INBOX_DIR, state)
        if os.path.exists(path):
            # Count visible files only
            files = [f for f in os.listdir(path) if not f.startswith('.')]
            counts[state] = len(files)
            
    return counts

def get_current_job():
    """
    Attempt to find the currently running job.
    Assuming 'in_progress' contains the job being worked on.
    We'll pick the first one we find to show details.
    """
    in_progress_path = os.path.join(INBOX_DIR, 'in_progress')
    if not os.path.exists(in_progress_path):
        return None
        
    jobs = [f for f in os.listdir(in_progress_path) if f.endswith('.job')]
    if not jobs:
        return None
        
    # Just take the first one
    job_file = jobs[0]
    full_path = os.path.join(in_progress_path, job_file)
    
    # Read content
    try:
        with open(full_path, 'r') as f:
            content = f.read().strip()
    except:
        content = "Error reading file"

    # Get stats
    stats = os.stat(full_path)
    
    return {
        'filename': job_file,
        'content': content,
        'mtime': stats.st_mtime
    }

def tail_logs(lines=20):
    """
    Tail the worker and reconcile logs.
    We'll just cat them and take the last N lines combined? 
    Or separate? User asked for "Recent Activity (Read-only Log Tail)".
    Let's mix them and sort by time if possible, or just grab the latest chunk from each.
    Simplicity: Grab last N lines of worker.log and reconcile.log, merge and sort?
    Or just worker.log mostly.
    
    Let's look for *.log in Sync/logs
    """
    log_files = glob.glob(os.path.join(LOGS_DIR, '*.log'))
    entries = []
    
    for log_file in log_files:
        filename = os.path.basename(log_file)
        try:
            # Check size, if huge, seeking might be needed, but for "Recent Activity" 
            # on a small tool, reading last 10KB is usually fine.
            file_size = os.path.getsize(log_file)
            read_size = min(file_size, 20000) # 20KB
            
            with open(log_file, 'r', errors='replace') as f:
                if file_size > read_size:
                    f.seek(file_size - read_size)
                
                content = f.read()
                file_lines = content.splitlines()
                
                # Add to entries
                for line in file_lines:
                    if line.strip():
                        entries.append({
                            'source': filename,
                            'text': line.strip()
                        })
        except Exception:
            pass

    # This is a very rough "latest entries". 
    # Real log parsing for timestamps is fragile without a known format.
    # We will just return the raw lines to the frontend, maybe just the last N total.
    # Since we don't know the timestamp format for sure, we can't reliably sort merged logs.
    # We'll just return the last 15 lines of each log found.
    # A robust dashboard would use a structured logger. We settle for "whatever is there".
    
    # Better: return the data grouped by log file? 
    # Inspector View requirement: "See related logs".
    # Recent Activity: "worker -> picked job..."
    
    # Let's try to just return the last N lines of the largest/most active log?
    # Or just return a dict of {filename: [last lines]} and let frontend render.
    
    logs_data = {}
    for log_file in log_files:
         filename = os.path.basename(log_file)
         try:
            # efficient tail
            proc = subprocess.run(['tail', '-n', str(lines), log_file], capture_output=True, text=True)
            logs_data[filename] = proc.stdout.splitlines()
         except:
             logs_data[filename] = ["Error reading log"]
             
    return logs_data

def get_job_id(url):
    """
    Generate deterministic job_id from URL (sha1).
    Matches logic in Sync/bin/enqueue_owned.sh
    """
    if not url:
        return None
    # clean url logic from bash: echo "$1" | sed 's/&quot;//g' | cut -d',' -f1
    # python equivalent:
    url = url.replace('&quot;', '').split(',')[0]
    return hashlib.sha1(url.encode('utf-8')).hexdigest()

def get_collection_status():
    """
    Read collection.json and correlate with job queues and filesystem.
    """
    if not os.path.exists(COLLECTION_FILE):
        return {'status': 'missing_file', 'items': []}

    try:
        with open(COLLECTION_FILE, 'r') as f:
            items = json.load(f)
    except:
         return {'status': 'error', 'items': []}

    # Map job_id -> status from queues
    job_status_map = {}
    
    for state in ['pending', 'in_progress', 'failed', 'done']:
        path = os.path.join(INBOX_DIR, state)
        if os.path.exists(path):
            files = os.listdir(path)
            for f in files:
                if f.endswith('.job'):
                    job_id = f[:-4] # remove .job
                    job_status_map[job_id] = state.upper()

    # Annotate items
    results = []
    for item in items:
        url = item.get('item_url')
        artist = item.get('band_name', 'Unknown Artist')
        title = item.get('item_title', 'Unknown Title')
        
        job_id = get_job_id(url)
        
        # Determine status
        status = 'UNKNOWN'
        
        # 1. Check Filesystem (Highest Priority if done job is missing or just to be sure)
        # Structure: ~/Music/Bandcamp/Artist/Album
        # We need to sanitize names as yt-dlp/downloader does?
        # Downloader uses yt-dlp metdata, which might differ slightly from JSON.
        # But we can try a direct check if simple.
        # However, checking job_status 'DONE' is reliable for "we processed it".
        # Let's rely on job_status DONE first, but also check FS if unknown?
        # User requested: "I would like it to show Downloaded if I downloaded."
        
        # Check if job marked as DONE
        if job_id and job_status_map.get(job_id) == 'DONE':
             status = 'DOWNLOADED'
        elif job_id and job_id in job_status_map:
             status = job_status_map[job_id]
        
        # If still UNKNOWN, check FS? 
        # Risky without exact path match. Let's stick to job queue state for now as it is the "pipeline" truth.
        # If the user has "already have" in logs, it means the job went to DONE.
        # So checking DONE queue is correct.
        
        results.append({
            'artist': artist,
            'title': title,
            'status': status,
            'url': url
        })
        
    return {'status': 'ok', 'items': results}

@app.route('/')
def index():
    return send_from_directory(UI_DIR, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(UI_DIR, path)

@app.route('/api/status')
def api_status():
    units = [
        'bandcamp-sync-reconcile.service',
        'bandcamp-sync-worker.service',
        'bandcamp-sync.path',
        'bandcamp-sync-worker.path'
    ]
    return jsonify({
        'systemd': get_systemd_status(units)
    })

@app.route('/api/queue')
def api_queue():
    return jsonify({
        'counts': count_jobs(),
        'current_job': get_current_job()
    })

@app.route('/api/logs')
def api_logs():
    return jsonify({
        'logs': tail_logs(20)
    })

@app.route('/api/collection')
def api_collection():
    return jsonify(get_collection_status())

if __name__ == '__main__':
    print(f"Starting BandcampSync Dashboard on http://localhost:5000")
    print(f"Observing: {SYNC_ROOT}")
    app.run(host='0.0.0.0', port=5000, debug=True)
