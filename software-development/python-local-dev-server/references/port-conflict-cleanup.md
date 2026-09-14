# Port Conflict Cleanup — Detailed Patterns

Cross-platform commands for identifying and killing processes holding ports.

## macOS

### List all listening processes
```bash
lsof -i -P | grep LISTEN
```

### Find process on specific port
```bash
lsof -i :8000 | grep LISTEN
lsof -i :8001 | grep LISTEN
```

### Get PID only (for scripting)
```bash
lsof -t -i :8001
```

### Kill by PID
```bash
kill <PID>      # graceful
kill -9 <PID>   # force
```

### One-liner: free a port
```bash
PID=$(lsof -t -i :8001) && [ -n "$PID" ] && kill $PID
```

## Linux

### Using ss (modern replacement for netstat)
```bash
ss -tlnp | grep :8001
ss -tlnp sport = :8001
```

### Using netstat
```bash
netstat -tlnp | grep :8001
```

### Kill by port (requires fuser)
```bash
fuser -k 8001/tcp
```

## Identifying Zombie Python Processes

When a previous `terminal(background=true)` session leaves a Python process running:

```bash
# List all Python processes
ps aux | grep python

# Look for processes with long uptime (hours/days) — these are likely zombies
ps -eo pid,etime,comm,args | grep python

# The etime column shows elapsed time. A server started 5 minutes ago is current;
# one started 2 days ago is a zombie from a previous session.
```

## Background Process Zombie Scenario

**What happens:**
1. Session starts server with `terminal(background=true)` 
2. Session ends, but the background process keeps running
3. Next session tries to start server on same port → "address already in use"
4. `lsof` shows a Python process from hours/days ago

**Fix:**
```bash
# Find the old PID
lsof -i :8001 | grep LISTEN
# → Python  63636 user  10u  IPv4 ... TCP *:vcom-tunnel (LISTEN)

# Kill it
kill 63636

# Verify
lsof -i :8001 | grep LISTEN
# → (no output = port is free)
```

## Port Scanning for Alternatives

```bash
# Bash: find next free port in range
for port in $(seq 8000 8010); do
  if ! lsof -i :$port >/dev/null 2>&1; then
    echo "Port $port is free"
    break
  fi
done

# Python: find free port
python3 -c "import socket; s=socket.socket(); s.bind(('', 0)); print(s.getsockname()[1]); s.close()"
```

## Docker Conflicts

Docker containers can bind host ports even when no local process appears in `lsof`:

```bash
# List running containers
docker ps

# Check container port mappings
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Stop a container
docker stop <container_name>
```
