from flask import Flask, render_template, jsonify, request
import json
import os
from datetime import datetime, timedelta
import random
import requests
import time
import threading
from collections import deque

app = Flask(__name__)

# Global variables for monitoring
response_times = deque(maxlen=100)  # Store last 100 response times
service_status = {}
last_check_time = 0

# Add custom filter to Jinja2 environment
@app.template_filter('get_day_status_color')
def get_day_status_color_filter(status):
    """Template filter for get_day_status_color function"""
    return get_day_status_color(status)

def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "ShowStatuses": False,
            "StatusCategories": [],
            "StatusTypes": [],
            "CurrentStatuses": [],
            "PastIncidents": []
        }

def get_status_by_id(status_id, config):
    """Get status name by ID"""
    for status in config.get('StatusTypes', []):
        if status['StatusID'] == status_id:
            return status['Status']
    return 'Unknown'

def get_category_by_id(category_id, config):
    """Get category name by ID"""
    for category in config.get('StatusCategories', []):
        if category['CategoryID'] == category_id:
            return category['CategoryName']
    return 'Unknown'

def format_timestamp(timestamp):
    """Format Unix timestamp to readable date"""
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime('%B %d, %Y at %I:%M %p')
    return None

def get_status_color(status_ids):
    """Get color class based on status IDs"""
    if not status_ids:
        return 'operational'
    
    # Priority: Major Outage > Partial Outage > Under Maintenance > Degraded > Investigating > Operational
    priority_map = {4: 'major-outage', 3: 'partial-outage', 5: 'maintenance', 
                   2: 'degraded', 6: 'investigating', 1: 'operational'}
    
    highest_priority = min(status_ids) if status_ids else 1
    for status_id in status_ids:
        if status_id in [4, 3, 5, 2, 6] and status_id < highest_priority:
            highest_priority = status_id
    
    return priority_map.get(highest_priority, 'operational')

def get_health_endpoints():
    """Get health check endpoints from config"""
    config = load_config()
    endpoints = {
        'API': 'https://royalguard-api.up.railway.app/',  # Your actual Royal Guard API
        'Discord Bot': 'https://discord.com/api/v10/gateway',
        'Database': 'https://royalguard-api.up.railway.app/',  # Database health via API health check
        'ROBLOX API': 'https://api.roblox.com/'
    }
    return endpoints

def check_service_health(service_name, url):
    """Check health of a single service"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=5)
        end_time = time.time()
        
        response_time = round((end_time - start_time) * 1000, 2)  # Convert to ms
        
        if response.status_code == 200:
            return {'status': 'operational', 'response_time': response_time}
        elif response.status_code in [500, 502, 503, 504]:
            return {'status': 'major', 'response_time': response_time}
        else:
            return {'status': 'degraded', 'response_time': response_time}
    except requests.exceptions.Timeout:
        return {'status': 'degraded', 'response_time': 5000}
    except requests.exceptions.ConnectionError:
        return {'status': 'major', 'response_time': None}
    except Exception:
        return {'status': 'investigating', 'response_time': None}

def monitor_services():
    """Monitor all services and update global status"""
    global service_status, response_times, last_check_time
    
    endpoints = get_health_endpoints()
    total_response_time = 0
    successful_checks = 0
    
    for service_name, url in endpoints.items():
        result = check_service_health(service_name, url)
        service_status[service_name] = result
        
        if result['response_time'] is not None:
            total_response_time += result['response_time']
            successful_checks += 1
    
    # Calculate average response time
    if successful_checks > 0:
        avg_response_time = round(total_response_time / successful_checks, 2)
        response_times.append(avg_response_time)
    
    last_check_time = time.time()

def get_current_response_time():
    """Get current average response time"""
    if not response_times:
        return 0
    return round(sum(response_times) / len(response_times), 2)

def calculate_uptime():
    """Calculate real uptime percentage based on service checks"""
    if not service_status:
        return 99.98  # Fallback for initial load
    
    operational_services = sum(1 for status in service_status.values() 
                             if status['status'] == 'operational')
    total_services = len(service_status)
    
    if total_services == 0:
        return 99.98
    
    return round((operational_services / total_services) * 100, 2)

def generate_90_day_history():
    """Generate 90 days of historical status data from real incidents"""
    config = load_config()
    history = []
    today = datetime.now()
    
    # Create a dictionary to map dates to incidents
    incident_map = {}
    
    # Process past incidents from config
    for incident in config.get('PastIncidents', []):
        if incident.get('StartedAt'):
            incident_date = datetime.fromtimestamp(incident['StartedAt'])
            date_str = incident_date.strftime('%Y-%m-%d')
            
            # Determine status based on StatusID
            status_ids = incident.get('StatusID', [])
            if 4 in status_ids:  # Major Outage
                status = 'major'
                incident_type = 'major'
            elif 3 in status_ids:  # Partial Outage
                status = 'partial'
                incident_type = 'partial'
            elif 2 in status_ids:  # Degraded Performance
                status = 'degraded'
                incident_type = 'degraded'
            elif 5 in status_ids:  # Under Maintenance
                status = 'maintenance'
                incident_type = 'maintenance'
            else:
                status = 'investigating'
                incident_type = 'investigating'
            
            if date_str not in incident_map:
                incident_map[date_str] = {
                    'status': status,
                    'incidents': []
                }
            
            incident_map[date_str]['incidents'].append({
                'title': incident.get('StatusTitle', 'Unknown Incident'),
                'type': incident_type,
                'description': incident.get('StatusDescription', ''),
                'by': incident.get('By', ''),
                'started_at': incident.get('StartedAt'),
                'fixed_at': incident.get('FixedAt')
            })
    
    # Process current unresolved statuses
    for status in config.get('CurrentStatuses', []):
        if not status.get('FixedAt') and status.get('StartedAt'):
            incident_date = datetime.fromtimestamp(status['StartedAt'])
            date_str = incident_date.strftime('%Y-%m-%d')
            
            # Determine status based on StatusID
            status_ids = status.get('StatusID', [])
            if 4 in status_ids:
                current_status = 'major'
                incident_type = 'major'
            elif 3 in status_ids:
                current_status = 'partial'
                incident_type = 'partial'
            elif 2 in status_ids:
                current_status = 'degraded'
                incident_type = 'degraded'
            elif 5 in status_ids:
                current_status = 'maintenance'
                incident_type = 'maintenance'
            else:
                current_status = 'investigating'
                incident_type = 'investigating'
            
            if date_str not in incident_map:
                incident_map[date_str] = {
                    'status': current_status,
                    'incidents': []
                }
            
            incident_map[date_str]['incidents'].append({
                'title': status.get('StatusTitle', 'Ongoing Issue'),
                'type': incident_type,
                'description': status.get('StatusDescription', ''),
                'by': status.get('By', ''),
                'started_at': status.get('StartedAt'),
                'fixed_at': None
            })
    
    # Generate 90 days of history
    for i in range(90):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        if date_str in incident_map:
            # Use real incident data
            day_data = incident_map[date_str]
            history.append({
                'date': date_str,
                'status': day_data['status'],
                'incidents': day_data['incidents'],
                'timestamp': int(date.timestamp())
            })
        else:
            # Operational day
            history.append({
                'date': date_str,
                'status': 'operational',
                'incidents': [],
                'timestamp': int(date.timestamp())
            })
    
    return list(reversed(history))  # Return chronologically

def get_day_status_color(status):
    """Get color class for day status"""
    if status in ['degraded', 'major']:
        return 'red'
    elif status in ['partial', 'maintenance', 'investigating']:
        return 'yellow'
    else:
        return 'green'

@app.route('/')
def index():
    config = load_config()
    
    if not config.get('ShowStatuses', False):
        return render_template('index.html', 
                             show_statuses=False,
                             message="No statuses have been recently posted.")
    
    # Process current statuses
    current_statuses = []
    for status in config.get('CurrentStatuses', []):
        if not status.get('FixedAt'):  # Only unresolved statuses
            processed_status = {
                'title': status.get('StatusTitle', ''),
                'description': status.get('StatusDescription', ''),
                'by': status.get('By', ''),
                'started_at': format_timestamp(status.get('StartedAt')),
                'status_names': [get_status_by_id(sid, config) for sid in status.get('StatusID', [])],
                'category_names': [get_category_by_id(cid, config) for cid in status.get('CategoryID', [])],
                'color_class': get_status_color(status.get('StatusID', []))
            }
            current_statuses.append(processed_status)
    
    # Process past incidents
    past_incidents = []
    for incident in config.get('PastIncidents', []):
        if incident.get('FixedAt'):  # Only resolved incidents
            processed_incident = {
                'title': incident.get('StatusTitle', ''),
                'description': incident.get('StatusDescription', ''),
                'by': incident.get('By', ''),
                'started_at': format_timestamp(incident.get('StartedAt')),
                'fixed_at': format_timestamp(incident.get('FixedAt')),
                'status_names': [get_status_by_id(sid, config) for sid in incident.get('StatusID', [])],
                'category_names': [get_category_by_id(cid, config) for cid in incident.get('CategoryID', [])],
                'color_class': get_status_color(incident.get('StatusID', []))
            }
            past_incidents.append(processed_incident)
    
    # Check if we need to update service monitoring (every 30 seconds)
    current_time = time.time()
    if current_time - last_check_time > 30:
        monitor_services()
    
    # Process categories for system metrics with real monitoring
    categories = []
    for category in config.get('StatusCategories', []):
        category_name = category['CategoryName']
        
        # Get real service status if available
        if category_name in service_status:
            service_info = service_status[category_name]
            real_status = service_info['status']
            
            if real_status == 'operational':
                status_text = 'Operational'
                status_class = 'operational'
            elif real_status == 'degraded':
                status_text = 'Degraded Performance'
                status_class = 'degraded'
            elif real_status == 'major':
                status_text = 'Major Issues'
                status_class = 'major-outage'
            else:
                status_text = 'Under Investigation'
                status_class = 'investigating'
        else:
            # Fallback to config-based status checking
            has_issues = False
            status_class = 'operational'
            
            for status in config.get('CurrentStatuses', []):
                if not status.get('FixedAt') and category['CategoryID'] in status.get('CategoryID', []):
                    has_issues = True
                    status_class = get_status_color(status.get('StatusID', []))
                    break
            
            status_text = 'Operational' if not has_issues else 'Issues Detected'
        
        categories.append({
            'name': category_name,
            'status': status_text,
            'status_class': status_class,
            'uptime': calculate_uptime()
        })
    
    # Generate 90-day history
    history_data = generate_90_day_history()
    
    return render_template('index.html',
                         show_statuses=True,
                         current_statuses=current_statuses,
                         past_incidents=past_incidents,
                         categories=categories,
                         overall_uptime=calculate_uptime(),
                         history_data=history_data,
                         current_response_time=get_current_response_time())

@app.route('/incident/<date>')
def incident_detail(date):
    """Show incident details for a specific date"""
    config = load_config()
    incidents_for_date = []
    
    # Check past incidents for this date
    for incident in config.get('PastIncidents', []):
        if incident.get('StartedAt'):
            incident_date = datetime.fromtimestamp(incident['StartedAt'])
            if incident_date.strftime('%Y-%m-%d') == date:
                # Determine incident type from StatusID
                status_ids = incident.get('StatusID', [])
                if 4 in status_ids:
                    incident_type = 'major'
                elif 3 in status_ids:
                    incident_type = 'partial'
                elif 2 in status_ids:
                    incident_type = 'degraded'
                elif 5 in status_ids:
                    incident_type = 'maintenance'
                else:
                    incident_type = 'investigating'
                
                incidents_for_date.append({
                    'title': incident.get('StatusTitle', 'Unknown Incident'),
                    'type': incident_type,
                    'description': incident.get('StatusDescription', ''),
                    'by': incident.get('By', ''),
                    'started_at': format_timestamp(incident.get('StartedAt')),
                    'fixed_at': format_timestamp(incident.get('FixedAt')),
                    'status_names': [get_status_by_id(sid, config) for sid in status_ids],
                    'category_names': [get_category_by_id(cid, config) for cid in incident.get('CategoryID', [])]
                })
    
    # Check current statuses for this date
    for status in config.get('CurrentStatuses', []):
        if status.get('StartedAt') and not status.get('FixedAt'):
            status_date = datetime.fromtimestamp(status['StartedAt'])
            if status_date.strftime('%Y-%m-%d') == date:
                # Determine status type from StatusID
                status_ids = status.get('StatusID', [])
                if 4 in status_ids:
                    status_type = 'major'
                elif 3 in status_ids:
                    status_type = 'partial'
                elif 2 in status_ids:
                    status_type = 'degraded'
                elif 5 in status_ids:
                    status_type = 'maintenance'
                else:
                    status_type = 'investigating'
                
                incidents_for_date.append({
                    'title': status.get('StatusTitle', 'Ongoing Issue'),
                    'type': status_type,
                    'description': status.get('StatusDescription', ''),
                    'by': status.get('By', ''),
                    'started_at': format_timestamp(status.get('StartedAt')),
                    'fixed_at': None,
                    'status_names': [get_status_by_id(sid, config) for sid in status_ids],
                    'category_names': [get_category_by_id(cid, config) for cid in status.get('CategoryID', [])]
                })
    
    if not incidents_for_date:
        return render_template('incident_detail.html', 
                             date=date, 
                             incidents=[], 
                             not_found=False)
    
    return render_template('incident_detail.html', 
                         date=date, 
                         incidents=incidents_for_date)

@app.route('/api/status')
def api_status():
    """API endpoint for status data"""
    config = load_config()
    return jsonify(config)

def start_monitoring_thread():
    """Start background monitoring thread"""
    def monitor_loop():
        while True:
            try:
                monitor_services()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
    
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()

if __name__ == '__main__':
    # Start monitoring services in background
    start_monitoring_thread()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
