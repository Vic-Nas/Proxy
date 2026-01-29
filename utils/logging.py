"""Logging utilities with ultra-compact time-windowed aggregation."""
import sys
import re
from collections import deque, defaultdict
from datetime import datetime
## No ENABLE_LOGS needed; logs always available if template exists

# Simple in-memory log storage (last 1000 lines)
LOG_BUFFER = deque(maxlen=1000)

# Track all activity in time windows
_activity_window = {
    'start_time': None,
    'services': defaultdict(lambda: {
        'proxy': 0,
        'rewrite': 0,
        'assets': defaultdict(int)
    }),
    'errors': [],
    'warnings': [],
    'other': []
}

# Configuration
WINDOW_DURATION = 5.0  # seconds - aggregate everything in 5-second windows
MAX_QUIET_TIME = 2.0  # seconds - flush if quiet for 2 seconds


def _get_service_from_message(msg):
    """Extract service name from log message."""
    # PROXY: /service/path
    proxy_match = re.search(r'\[PROXY\] GET /([^/]+)/', msg)
    if proxy_match:
        service = proxy_match.group(1)
        # Map to friendly names
        if service == 'mdn':
            return 'MDN Web Docs'
        elif service == 'club':
            return 'Calculum Club'
        return service
    
    # REWRITE: domain
    rewrite_match = re.search(r'\[REWRITE\] Processing ([^/\s]+)', msg)
    if rewrite_match:
        domain = rewrite_match.group(1)
        if 'developer.mozilla.org' in domain:
            return 'MDN Web Docs'
        elif 'calculum' in domain:
            return 'Calculum Club'
        return domain.split('.')[0]
    
    return None


def _extract_asset_info(msg):
    """Extract service and file types from asset log."""
    match = re.search(r'\[ASSETS\] ([^:]+): (\d+)x (\w+)', msg)
    if match:
        return match.group(1), match.group(3), int(match.group(2))
    return None, None, None


def _should_suppress(msg):
    """Check if message should be completely suppressed."""
    suppressable = [
        '[REWRITE]   Found ',
        '[REWRITE]   Content-Type:',
        '[REWRITE]   Contains pathname reads:',
        '[REWRITE]   Contains API calls:',
        '[REWRITE]   No changes made',
        '[REWRITE]   ✓ Modified',
        'Not Found: /robots.txt',
        '[... repeated',  # Suppress old-style repeat messages
    ]
    return any(s in msg for s in suppressable)


def _flush_window(force=False):
    """Flush the current activity window."""
    global _activity_window
    
    window = _activity_window
    
    # Check if window should be flushed
    if window['start_time']:
        elapsed = (datetime.utcnow() - window['start_time']).total_seconds()
        should_flush = force or elapsed >= WINDOW_DURATION
        
        if not should_flush:
            # Check for quiet time
            if not window['services'] and elapsed >= MAX_QUIET_TIME:
                should_flush = True
        
        if not should_flush:
            return
    
    # Nothing to flush
    if not window['services'] and not window['errors'] and not window['warnings'] and not window['other']:
        return
    
    # Flush errors first (always show these immediately)
    for error_msg in window['errors']:
        _write_log(f"❌ {error_msg}")
    
    # Flush warnings
    for warn_msg in window['warnings']:
        _write_log(f"⚠️  {warn_msg}")
    
    # Flush aggregated service activity
    if window['services']:
        # Sort by total activity
        service_activity = []
        for service, data in window['services'].items():
            total = data['proxy'] + data['rewrite'] + sum(data['assets'].values())
            service_activity.append((total, service, data))
        
        service_activity.sort(reverse=True)
        
        for _, service, data in service_activity:
            parts = []
            
            if data['proxy'] > 0:
                parts.append(f"{data['proxy']} request")
            
            if data['rewrite'] > 0:
                parts.append(f"{data['rewrite']} rewrite")
            
            if data['assets']:
                total_assets = sum(data['assets'].values())
                # Group similar asset types
                asset_types = {}
                for ftype, count in data['assets'].items():
                    # Simplify asset type names
                    if ftype in ['css', 'js', 'html']:
                        category = 'code'
                    elif ftype in ['svg', 'png', 'jpg', 'jpeg', 'gif', 'webp']:
                        category = 'img'
                    elif ftype in ['woff', 'woff2', 'ttf', 'otf']:
                        category = 'font'
                    else:
                        category = ftype
                    
                    asset_types[category] = asset_types.get(category, 0) + count
                
                asset_str = '+'.join(f"{count}{cat}" for cat, count in sorted(asset_types.items()))
                parts.append(f"{total_assets} assets ({asset_str})")
            
            if parts:
                _write_log(f"📊 {service}: {' | '.join(parts)}")
    
    # Flush other messages
    for other_msg in window['other']:
        _write_log(other_msg)
    
    # Reset window
    _activity_window = {
        'start_time': None,
        'services': defaultdict(lambda: {
            'proxy': 0,
            'rewrite': 0,
            'assets': defaultdict(int)
        }),
        'errors': [],
        'warnings': [],
        'other': []
    }


def _write_log(msg):
    """Write log to stdout and buffer."""
    sys.stdout.write(f"{msg}\n")
    sys.stdout.flush()
    
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    LOG_BUFFER.append(f"{timestamp} [inf] {msg}")


def log(msg):
    """Log with smart deduplication and aggregation."""
    global _activity_window
    
    # Completely suppress certain messages
    if _should_suppress(msg):
        return
    
    # Initialize window if needed
    if _activity_window['start_time'] is None:
        _activity_window['start_time'] = datetime.utcnow()
    
    # Categorize the message
    msg_lower = msg.lower()
    
    # Check for errors - always show immediately
    if '[err]' in msg_lower or 'error' in msg_lower:
        _flush_window(force=True)
        _write_log(f"❌ {msg}")
        return
    
    # Check for warnings
    if '[warn]' in msg_lower or 'warning' in msg_lower:
        _activity_window['warnings'].append(msg)
        _flush_window()
        return
    
    # Handle asset logs
    service, filetype, count = _extract_asset_info(msg)
    if service and filetype:
        _activity_window['services'][service]['assets'][filetype] += count
        _flush_window()
        return
    
    # Handle PROXY requests
    if '[PROXY] GET' in msg:
        service = _get_service_from_message(msg)
        if service:
            _activity_window['services'][service]['proxy'] += 1
            _flush_window()
            return
    
    # Handle REWRITE processing
    if '[REWRITE] Processing' in msg:
        service = _get_service_from_message(msg)
        if service:
            _activity_window['services'][service]['rewrite'] += 1
            _flush_window()
            return
    
    # Other messages - flush window first, then log
    _flush_window(force=True)
    _write_log(msg)


def get_log_buffer():
    """Get the log buffer for display."""
    # Flush any pending window
    _flush_window(force=True)
    return LOG_BUFFER