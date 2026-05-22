import json
import re
from datetime import datetime, timezone

def parse_timestamp(ts):
    if not ts: return None
    ts_str = str(ts).strip()
    if ts_str.isdigit():
        return datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
    for fmt in ['%Y-%m-%dT%H:%M:%SZ', '%Y/%m/%d %H:%M:%S', '%d-%b-%Y %H:%M:%S']:
        try:
            dt = datetime.strptime(ts_str, fmt)
            if not dt.tzinfo: dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    return None

def format_values(parsed):
    if parsed is None:
        return None
        
    status = parsed.get("status")
    if status is not None and status != '-':
        try:
            parsed["status"] = int(status)
        except (ValueError, TypeError):
            parsed["status"] = None
    elif status == '-':
        parsed["status"] = None

    latency = parsed.get("latency")
    if latency is not None:
        latency_str = str(latency).strip().lower()
        try:
            if latency_str.endswith('ms'):
                parsed["latency"] = float(latency_str[:-2])
            elif latency_str.endswith('s'):
                parsed["latency"] = float(latency_str[:-1]) * 1000.0
            else:
                parsed["latency"] = float(latency_str)
        except ValueError:
            parsed["latency"] = None

    timestamp = parsed.get("timestamp")
    if timestamp is not None:
        parsed["timestamp"] = parse_timestamp(timestamp)

    return parsed


def parse_text_line(line):
    # Find IP to separate timestamp
    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', line)
    if not ip_match:
        return None # No IP, skip as random noise
        
    ip = ip_match.group(1)
    ip_start = ip_match.start()
    
    ts_str = line[:ip_start].strip()
    rest_str = line[ip_match.end():].strip()
    
    rest_parts = rest_str.split()
    if len(rest_parts) < 2:
        return None # Needs at least method and path
        
    method = rest_parts[0]
    path = rest_parts[1]
    
    if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
        return None
        
    status = None
    latency = None
    is_corrupt = False
    
    # Analyze parts after method and path
    if len(rest_parts) >= 3:
        if rest_parts[2] == '-':
            status = None
            if len(rest_parts) >= 4:
                latency = rest_parts[3]
            is_corrupt = True
        elif rest_parts[2].isdigit() and len(rest_parts[2]) == 3:
            status = int(rest_parts[2])
            if len(rest_parts) >= 4:
                latency = rest_parts[3]
        else:
            # Missing status (double space), so rest_parts[2] is actually latency
            status = None
            latency = rest_parts[2]
            is_corrupt = True
    else:
        # missing status and latency entirely
        is_corrupt = True

    # Validate timestamp format
    if not ts_str:
        is_corrupt = True
    elif not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', ts_str):
        is_corrupt = True
        
    # Validate latency format
    if latency:
        if not latency.endswith('ms'):
            is_corrupt = True
        elif not latency[:-2].isdigit():
            is_corrupt = True
            
    if status is None:
        is_corrupt = True

    return format_values({
        "raw_line": line,
        "timestamp": ts_str,
        "ip": ip,
        "method": method,
        "path": path,
        "status": status,
        "latency": latency,
        "is_corrupt": is_corrupt
    })

def parse_line(line):
    """
    Parses a log line.
    Returns a dict with parsed fields and 'is_corrupt' flag, or None if skipped (noise).
    """
    line = line.strip()
    if not line:
        return None # skip empty
    
    # Check if JSON
    if line.startswith('{') and line.endswith('}'):
        try:
            data = json.loads(line)
            required_keys = {"timestamp", "ip", "method", "path", "status", "latency_ms"}
            
            if required_keys.issubset(data.keys()):
                return format_values({
                    "raw_line": line,
                    "timestamp": data["timestamp"],
                    "ip": data["ip"],
                    "method": data["method"],
                    "path": data["path"],
                    "status": data["status"],
                    "latency": data["latency_ms"],
                    "is_corrupt": False
                })
            else:
                return format_values({
                    "raw_line": line,
                    "timestamp": data.get("timestamp"),
                    "ip": data.get("ip"),
                    "method": data.get("method"),
                    "path": data.get("path"),
                    "status": data.get("status"),
                    "latency": data.get("latency_ms"),
                    "is_corrupt": True
                })
        except json.JSONDecodeError:
            pass # fallback to text parsing, though unlikely for '{}' wrapper
            
    # If not JSON, use text parsing logic
    return parse_text_line(line)
