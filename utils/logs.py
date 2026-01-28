"""Logs view and utilities."""
from django.http import HttpResponse
from config import ENABLE_LOGS
from utils.logging import get_log_buffer
from utils.templates import render_template


def render_logs():
    """Render logs page."""
    if not ENABLE_LOGS:
        return HttpResponse("Logs service not enabled. Set LOGS=true to enable.", status=404)
    
    # Build log lines with CSS classes
    log_lines = []
    log_buffer = get_log_buffer()
    
    for line in log_buffer:
        css_class = ""
        if "[PROXY]" in line:
            css_class = "proxy"
        elif "[REWRITE]" in line:
            css_class = "rewrite"
        elif "[ERROR]" in line:
            css_class = "error"
        elif "[WARNING]" in line:
            css_class = "warning"
        
        log_lines.append({
            'text': line,
            'css_class': css_class
        })
    
    html = render_template('logs.html', {
        'log_lines': log_lines,
    })
    response = HttpResponse(html)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    return response
