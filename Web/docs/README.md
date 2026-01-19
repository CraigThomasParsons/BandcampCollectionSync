# BandcampSync Web Dashboard

A read-only, LCARS-style observability dashboard for the BandcampSync system.

## Philosophy

This tool adheres to the same "boring code" philosophy as the core pipeline:

- **No Database**: Reads directly from filesystem (`Sync/inbox`, `Sync/logs`).
- **No Background Daemons**: It observes, it doesn't manage lifecycle.
- **Fail-Safe**: If this dashboard crashes, the sync pipeline is unaffected.

## Architecture

- **Backend**: Python (Flask). Exposes read-only JSON endpoints.
- **Frontend**: Vanilla HTML/CSS/JS. No frameworks, no build step.
- **State**: Derived entirely from `systemctl --user` and directory listings.

## Visuals

The interface is styled after STAR TREK LCARS (Library Computer Access and Retrieval System) to provide a clear, high-contrast status overview.

## Running the Dashboard

### Prerequisites

- Python 3
- Flask (`pip install flask`)
- Access to the same user session as the systemd units (for `systemctl --user` status).

### usage

```bash
# Install dependencies
pip install flask

# Run the server
python3 Web/server/app.py
```

The dashboard will be available at [http://localhost:5000](http://localhost:5000).

## Endpoints

- `GET /api/status`: Systemd unit states.
- `GET /api/queue`: Counts of jobs in inbox directories.
- `GET /api/logs`: Tailed content of log files.

## Troubleshooting

- **Status says "offline"**: Check if the Flask server is running.
- **Systemd units show "error"**: Ensure you are running the dashboard as the same user that owns the systemd services.
