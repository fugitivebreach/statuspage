# Royal Guard Status Page

A modern, sleek status page with gold to crimson red gradient design for monitoring system status and incidents.

## Features

- **Modern UI**: Beautiful gradient design with gold to crimson red theme
- **Real-time Status**: Display current system status and incidents
- **Multi-category Support**: Track different service categories (API, Discord Bot, Web Dashboard, Database, ROBLOX Integration)
- **Incident Management**: Track past incidents with resolution timestamps
- **Responsive Design**: Works on all device sizes
- **Railway Ready**: Configured for easy Railway deployment

## Configuration

Edit `config.json` to customize your status page:

### Main Settings
- `ShowStatuses`: Set to `true` to show statuses, `false` to show "No statuses have been recently posted"

### Status Categories
Define service categories to monitor:
```json
"StatusCategories": [
  {
    "CategoryID": 1,
    "CategoryName": "API"
  }
]
```

### Status Types
Define different status types:
```json
"StatusTypes": [
  {
    "StatusID": 1,
    "Status": "Operational"
  },
  {
    "StatusID": 2,
    "Status": "Degraded Performance"
  }
]
```

### Current Statuses
Active status updates (unresolved issues):
```json
"CurrentStatuses": [
  {
    "StatusTitle": "Short descriptive title",
    "StatusDescription": "Detailed description of the status",
    "By": "Who reported/is handling this",
    "StatusID": [1, 2],
    "CategoryID": [1, 3],
    "StartedAt": 1725835530,
    "FixedAt": null
  }
]
```

### Past Incidents
Resolved incidents:
```json
"PastIncidents": [
  {
    "StatusTitle": "Incident title",
    "StatusDescription": "What happened",
    "By": "Who handled it",
    "StatusID": [3],
    "CategoryID": [4],
    "StartedAt": 1725749130,
    "FixedAt": 1725752730
  }
]
```

## Deployment on Railway

1. Create a new Railway project
2. Connect your GitHub repository
3. Railway will automatically detect the Python app and deploy it
4. The app will be available at your Railway-provided URL

### Environment Variables
No additional environment variables are required. The app runs on the PORT provided by Railway.

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Visit `http://localhost:5000` to view the status page

## API Endpoint

The status page also provides a JSON API endpoint at `/api/status` that returns the current configuration data.

## Status Priority System

The system automatically determines the overall status based on priority:
1. Major Outage (highest priority)
2. Partial Outage
3. Under Maintenance
4. Degraded Performance
5. Investigating
6. Operational (lowest priority)

## Customization

- Modify the CSS in `templates/index.html` to change colors and styling
- Update `config.json` to add/remove categories and statuses
- The uptime calculation can be customized in the `calculate_uptime()` function
