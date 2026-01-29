"""Logs view and utilities with enhanced formatting."""
from django.http import HttpResponse
from config import ENABLE_LOGS
from utils.logging import get_log_buffer
from utils.templates import render_template


def _classify_log_line(line):
    """Classify log line and return CSS class."""
    lower_line = line.lower()
    
    # Priority order matters
    if '[err]' in lower_line or 'error' in lower_line or 'not found' in lower_line:
        return 'error'
    
    if '[warn]' in lower_line or 'warning' in lower_line:
        return 'warning'
    
    if '[assets]' in lower_line:
        return 'assets'
    
    if '[proxy]' in lower_line:
        return 'proxy'
    
    if '[rewrite]' in lower_line:
        return 'rewrite'
    
    if 'repeated' in lower_line:
        return 'duplicate'
    
    return 'info'


def _format_log_line(line):
    """Format log line for better readability."""
    # Extract timestamp if present
    import re
    timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)', line)
    
    if timestamp_match:
        timestamp = timestamp_match.group(1)
        # Convert to readable format
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            readable_time = dt.strftime('%H:%M:%S')
            line = line.replace(timestamp, readable_time)
        except:
            pass
    
    return line


def render_logs():
    """Render logs page with enhanced formatting."""
    if not ENABLE_LOGS:
        return HttpResponse(
            "Logs service not enabled. Set LOGS=true to enable.",
            status=404
        )
    
    # Build log lines with CSS classes and formatting
    log_lines = []
    log_buffer = get_log_buffer()
    
    for line in log_buffer:
        formatted_line = _format_log_line(line)
        css_class = _classify_log_line(line)
        
        log_lines.append({
            'text': formatted_line,
            'css_class': css_class
        })
    
    # Generate summary statistics
    stats = {
        'total': len(log_lines),
        'errors': sum(1 for l in log_lines if l['css_class'] == 'error'),
        'warnings': sum(1 for l in log_lines if l['css_class'] == 'warning'),
        'assets': sum(1 for l in log_lines if l['css_class'] == 'assets'),
        'proxy': sum(1 for l in log_lines if l['css_class'] == 'proxy'),
    }
    
    html = render_template('logs.html', {
        'log_lines': log_lines,
        'stats': stats,
    })
    
    response = HttpResponse(html)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response