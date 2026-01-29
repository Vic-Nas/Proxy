"""Logging utilities with smart aggregation and deduplication."""
import sys
import re
from collections import deque, defaultdict
from datetime import datetime
from config import ENABLE_LOGS

# Simple in-memory log storage (last 1000 lines)
LOG_BUFFER = deque(maxlen=1000)

# Track asset batches per service
_asset_batch = defaultdict(lambda: defaultdict(int))

# Track consecutive similar messages
_last_message_key = None
_message_count = 1

# Batch timing
_batch_start_time = None


def _normalize_url(url):
    """Normalize URL for deduplication."""
    # Remove query params and hashes
    url = re.sub(r'[?#].*$', '', url)
    # Extract just domain and path structure
    match = re.search(r'https?://([^/]+)(/[^/]+)?', url)
    if match:
        return f"{match.group(1)}{match.group(2) or ''}"
    return url


def _get_message_key(msg):
    """Get a key for message deduplication."""
    # PROXY requests - group by service
    proxy_match = re.search(r'\[PROXY\] GET /([^/]+)/', msg)
    if proxy_match:
        return f"proxy:{proxy_match.group(1)}"
    
    # REWRITE processing - group by domain
    if '[REWRITE] Processing' in msg:
        url_match = re.search(r'https?://([^/]+)', msg)
        if url_match:
            return f"rewrite:{url_match.group(1)}"
    
    # Asset logs
    if '[ASSETS]' in msg:
        service_match = re.search(r'\[ASSETS\] ([^:]+):', msg)
        if service_match:
            return f"assets:{service_match.group(1)}"
    
    # Error/Warning - always show
    if '[err]' in msg.lower() or '[warn]' in msg.lower():
        return None
    
    # Generic dedup
    return msg[:50]


def _extract_asset_info(msg):
    """Extract service and file types from asset log."""
    # Match pattern: [ASSETS] service: Nx type
    match = re.search(r'\[ASSETS\] ([^:]+): (\d+)x (\w+)', msg)
    if match:
        return match.group(1), match.group(3), int(match.group(2))
    return None, None, None


def _flush_batch(force=False):
    """Flush accumulated asset batches."""
    global _asset_batch, _batch_start_time
    
    if not _asset_batch:
        return
    
    for service, types in _asset_batch.items():
        if not types:
            continue
            
        # Calculate totals
        total_count = sum(types.values())
        
        # Build compact summary
        type_summaries = [f"{count}{ftype}" for ftype, count in sorted(types.items())]
        summary = f"[ASSETS] {service}: {', '.join(type_summaries)} ({total_count} total)"
        
        _write_log(summary)
    
    _asset_batch.clear()
    _batch_start_time = None


def _should_suppress(msg):
    """Check if message should be completely suppressed."""
    suppressable = [
        '[REWRITE]   Found ',  # pathname reference counts
        '[REWRITE]   Content-Type:',
        '[REWRITE]   Contains pathname reads:',
        '[REWRITE]   Contains API calls:',
        '[REWRITE]   No changes made',
        '[REWRITE]   ✓ Modified',
    ]
    return any(s in msg for s in suppressable)


def _write_log(msg):
    """Write log to stdout and buffer."""
    sys.stdout.write(f"{msg}\n")
    sys.stdout.flush()
    
    if ENABLE_LOGS:
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        LOG_BUFFER.append(f"{timestamp} [inf] {msg}")


def log(msg):
    """Log with smart deduplication and aggregation."""
    global _last_message_key, _message_count, _batch_start_time
    
    # Completely suppress certain messages
    if _should_suppress(msg):
        return
    
    # Handle asset logs - aggregate them
    service, filetype, count = _extract_asset_info(msg)
    if service and filetype:
        _asset_batch[service][filetype] += count
        
        # Start batch timer
        if _batch_start_time is None:
            _batch_start_time = datetime.utcnow()
        
        # Flush if batch is getting old (>5 seconds) or large
        if _batch_start_time:
            age = (datetime.utcnow() - _batch_start_time).total_seconds()
            total_assets = sum(sum(t.values()) for t in _asset_batch.values())
            
            if age > 5 or total_assets > 100:
                _flush_batch()
        
        return
    
    # Flush any pending asset batch before logging other messages
    if _asset_batch:
        _flush_batch()
    
    # Get message key for deduplication
    msg_key = _get_message_key(msg)
    
    # If same as last message, increment counter
    if msg_key and msg_key == _last_message_key:
        _message_count += 1
        return
    
    # If we were counting duplicates, show the summary
    if _last_message_key and _message_count > 1:
        summary = f"[... repeated {_message_count} times]"
        _write_log(summary)
    
    # Reset counter and log new message
    _last_message_key = msg_key
    _message_count = 1
    
    # Shorten long URLs in PROXY logs
    if '[PROXY] GET' in msg:
        msg = re.sub(r'(https?://[^/]+/[^/]+/).*', r'\1...', msg)
    
    # Shorten long URLs in REWRITE logs
    if '[REWRITE] Processing' in msg:
        url = re.search(r'https?://[^\s]+', msg)
        if url:
            short_url = _normalize_url(url.group(0))
            msg = msg.replace(url.group(0), short_url + '...')
    
    _write_log(msg)


def get_log_buffer():
    """Get the log buffer for display."""
    # Flush any pending batches
    _flush_batch(force=True)
    
    # Flush any pending duplicate count
    global _last_message_key, _message_count
    if _last_message_key and _message_count > 1:
        summary = f"[... repeated {_message_count} times]"
        _write_log(summary)
        _last_message_key = None
        _message_count = 1
    
    return LOG_BUFFER