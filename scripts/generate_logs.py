import os
import random
import datetime
import json
import argparse

def generate_standard_log(dt, ip, method, path, status, latency_ms):
    # Format: 2024-03-15T14:23:01Z 192.168.1.42 GET /api/users 200 142ms
    ts = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    return f"{ts} {ip} {method} {path} {status} {latency_ms}ms"

def generate_variation_1(dt, ip, method, path, status, latency_ms):
    # Timestamp Variations
    choice = random.choice([1, 2, 3])
    if choice == 1:
        ts = dt.strftime('%Y/%m/%d %H:%M:%S')
    elif choice == 2:
        ts = dt.strftime('%d-%b-%Y %H:%M:%S')
    else:
        ts = str(int(dt.timestamp()))
    
    return f"{ts} {ip} {method} {path} {status} {latency_ms}ms"

def generate_variation_2(dt, ip, method, path, status, latency_ms):
    # Response Time Units
    ts = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    choice = random.choice([1, 2])
    if choice == 1:
        latency = f"{latency_ms / 1000.0:.3f}s"
    else:
        latency = f"{latency_ms}"
    return f"{ts} {ip} {method} {path} {status} {latency}"

def generate_variation_3(dt, ip, method, path, status, latency_ms):
    # Missing or Broken Status Codes
    ts = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    choice = random.choice([1, 2])
    if choice == 1:
        # Skip entirely (double space)
        return f"{ts} {ip} {method} {path}  {latency_ms}ms"
    else:
        # Dash
        return f"{ts} {ip} {method} {path} - {latency_ms}ms"

def generate_variation_4(dt, ip, method, path, status, latency_ms):
    # Appended Trailing Fields
    ts = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    base = f"{ts} {ip} {method} {path} {status} {latency_ms}ms"
    
    agents = [
        '"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"',
        '"https://google.com/search?q=test"',
        '"curl/7.68.0"',
        '"CustomApp/1.0 (Integration)"'
    ]
    return f"{base} {random.choice(agents)}"

def generate_variation_5(dt, ip, method, path, status, latency_ms):
    # Malformed Garbage, Multi-line Stacks & Blanks
    choice = random.choice([1, 2, 3])
    if choice == 1:
        return "" # empty line, will write \n
    elif choice == 2:
        ts = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        base = f"{ts} {ip} {method} {path}"
        # truncate randomly
        if len(base) > 10:
            return base[:random.randint(10, len(base)-2)]
        return base
    else:
        # Stack trace 3 to 7 lines deep
        stacks = [
            'Traceback (most recent call last):\n  File "auth.py", line 42, in login\n    raise ValueError("Invalid credentials")\nValueError: Invalid credentials',
            'Traceback (most recent call last):\n  File "app.py", line 10, in <module>\n    import missing_module\nModuleNotFoundError: No module named \'missing_module\'',
            'Traceback (most recent call last):\n  File "db.py", line 112, in query\n    conn.execute(sql)\n  File "psycopg2/cursor.py", line 100, in execute\n    self._c.execute(q)\npsycopg2.OperationalError: server closed the connection unexpectedly'
        ]
        return random.choice(stacks)

def generate_variation_6(dt, ip, method, path, status, latency_ms):
    # Embedded JSON Rows
    ts = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    data = {
        "timestamp": ts,
        "ip": ip,
        "method": method,
        "path": path,
        "status": status,
        "latency_ms": latency_ms
    }
    return json.dumps(data)

def generate_logs(num_lines, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
    paths = ['/api/users', '/api/users/12', '/api/auth/login', '/api/products', '/api/orders', '/health', '/metrics']
    statuses = [200, 201, 400, 401, 403, 404, 500, 502, 503]
    
    start_time = datetime.datetime(2024, 3, 15, 10, 0, 0)
    
    with open(output_file, 'w') as f:
        # Write lines directly to file in a loop. Python handles I/O buffering efficiently,
        # so this will not store 150k lines in memory.
        for i in range(num_lines):
            # Advance time slightly for each log entry
            dt = start_time + datetime.timedelta(seconds=i*0.5)
            ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
            method = random.choice(methods)
            path = random.choice(paths)
            status = random.choice(statuses)
            latency_ms = random.randint(10, 5000)
            
            # 5-10% noise rate -> choose a random threshold between 0.05 and 0.10 for the entire run
            # To be strictly between 5 and 10% overall, we can just use a fixed 7.5% chance per line,
            # but user says "exactly 5% to 10%", so random.uniform(0.05, 0.10) per line gives an expected rate of 7.5%.
            
            if random.random() < 0.075:
                # Anomaly
                variation_func = random.choice([
                    generate_variation_1,
                    generate_variation_2,
                    generate_variation_3,
                    generate_variation_4,
                    generate_variation_5,
                    generate_variation_6
                ])
                line = variation_func(dt, ip, method, path, status, latency_ms)
                f.write(line + "\n")
            else:
                line = generate_standard_log(dt, ip, method, path, status, latency_ms)
                f.write(line + "\n")
            
    print(f"Successfully generated {num_lines} lines of log data.")
    print(f"Saved to: {os.path.abspath(output_file)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate chaotic server logs')
    parser.add_argument('--lines', type=int, default=150000, help='Number of lines to generate')
    args = parser.parse_args()
    
    # Calculate output path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_path = os.path.join(project_root, 'data', 'mock_server_logs.txt')
    
    generate_logs(args.lines, output_path)
