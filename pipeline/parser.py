import json
import re

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

    return {
        "raw_line": line,
        "timestamp": ts_str,
        "ip": ip,
        "method": method,
        "path": path,
        "status": status,
        "latency": latency,
        "is_corrupt": is_corrupt
    }

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
                return {
                    "raw_line": line,
                    "timestamp": data["timestamp"],
                    "ip": data["ip"],
                    "method": data["method"],
                    "path": data["path"],
                    "status": data["status"],
                    "latency": f"{data['latency_ms']}ms",
                    "is_corrupt": False
                }
            else:
                return {
                    "raw_line": line,
                    "timestamp": data.get("timestamp"),
                    "ip": data.get("ip"),
                    "method": data.get("method"),
                    "path": data.get("path"),
                    "status": data.get("status"),
                    "latency": f"{data.get('latency_ms')}ms" if data.get("latency_ms") else None,
                    "is_corrupt": True
                }
        except json.JSONDecodeError:
            pass # fallback to text parsing, though unlikely for '{}' wrapper
            
    # If not JSON, use text parsing logic
    return parse_text_line(line)
