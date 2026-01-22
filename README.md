# BandcampSync

BandcampSync is a file-backed, stage-driven pipeline for syncing Bandcamp albums.
Helpers live in `bin/` and only observe/trigger stages.

## Setup

**Quick Install** (Recommended):

```bash
chmod +x install.sh
./install.sh
```

This script automates all setup steps: creates a Python virtual environment, installs dependencies, installs Playwright chromium, links all systemd services, and starts them.

**Manual Setup** (Alternative):

1. **Install Dependencies**:

   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt # flask, requests, playwright, yt-dlp
   playwright install chromium
   ```

2. **Add Cookies**:
   - Save your Netscape-formatted Bandcamp cookies to `~/.config/bandcamp/cookies.txt`.
   - You can use an extension like "Get cookies.txt LOCALLY".

3. **Discover Fan ID**:

   ```bash
   # Navigates to your profile to find your ID
   python3 bin/capture_fan_id.py
   ```

4. **Install Systemd Services**:

   ```bash
   cp systemd/*.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now bandcamp-dashboard bandcamp-sync-worker
   ```

## Usage

### Web Dashboard

Open `http://localhost:5000` to view:

- System status (Queue counts, Worker activity)
- Complete Collection List (with sync status)
- Real-time logs

### Synchronization Loop

1. **Refresh Library**:
   Scrapes your latest collection items to `collection.json`.

   ```bash
   venv/bin/python capture_collection_api.py
   ```

2. **Reconcile & Download**:
   Parses `collection.json`, finds new items, and queues them.

   ```bash
   python3 extract_owned.py && Sync/bin/enqueue_owned.sh
   ```

   *The background worker (`bandcamp-sync-worker`) handles the actual downloading.*

## File Locations

- **Downloaded Music**: `~/Music/Bandcamp/<Artist>/<Album>/`
- **Configuration**: `~/BandcampSync/config/`
- **Logs**: `~/BandcampSync/Sync/logs/`
- **Queue State**: `~/BandcampSync/Sync/inbox/`

## Troubleshooting

### Manual Fan ID Extraction

If `capture_fan_id.py` fails:

1. Open Bandcamp in your browser.
2. Go to your profile page.
3. Open Developer Console (F12).
4. Type `window.FanData.fan_id`.
5. Save the number to `~/BandcampSync/config/fan_id.txt`.

### Scraper Issues

If the scraper stops early:

- Check `debug.html` to see what the scraper saw.
- Ensure your internet connection is stable.
- Run manually with `venv/bin/python capture_collection_api.py` to watch stdout.

## Features

The dashboard will be available at [http://localhost:5000](http://localhost:5000).

### The LCARS-style dashboard provides a high-contrast overview of system status.
Track active timers, workers, and recent actions at a glance. The LCARS layout mirrors systemd health so you can quickly confirm that `bandcamp-sync.service`, the worker, and timers are all green without tailing logs. Color blocks also surface retry timers and reconcile jobs, making it obvious when the pipeline is paused or recovering.
![alt text](Assets/LCARS-BandCampSync.png "Dashboard")

### The collections view shows all albums in your Bandcamp collection, with sync status indicators.
Rows include album title, artist, and a state badge (queued, downloading, synced, failed). Filters let you narrow to unsynced items, and a hover reveals the filesystem target path for quick inspection. The panel ties directly to `collection.json`, so refreshes reflect the latest scrape and reconcile run.
![alt text](Assets/BandCamp_Collections.png "Collections")

### The logs view shows real-time logs from the sync worker.
Live tail output from the worker and reconcile services keeps you aware of download progress, retries, and error traces. Use it to verify cookie/session validity, detect rate limits, and see `yt-dlp` output without opening a terminal. The view automatically follows new lines so you can leave it open during long syncs.
![alt text](Assets/BandCamp_Logs.png "Logs")

## API Endpoints

- `GET /api/status`: Systemd unit states. Example curl (expects dashboard running locally):

   ```bash
   curl -s http://localhost:5000/api/status | jq
   ```

- `GET /api/queue`: Counts of jobs in inbox directories. Helpful to confirm backlog size and worker throughput:

   ```bash
   curl -s http://localhost:5000/api/queue | jq
   ```

- `GET /api/logs`: Tailed content of log files. Include `?lines=200` to increase the tail length:

   ```bash
   curl -s "http://localhost:5000/api/logs?lines=200" | jq -r .logs
   ```
