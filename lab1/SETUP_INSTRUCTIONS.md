# SPADE Agent Setup Instructions

## Permission Issue Resolution

The error "This command can only be run by root or the user ejabberd" means you need elevated privileges.

### Quick Setup (Run these commands):

```bash
# 1. Install Ejabberd (requires sudo)
sudo apt-get update
sudo apt-get install -y ejabberd

# 2. Start the service (requires sudo)
sudo service ejabberd start

# 3. Check status
sudo ejabberdctl status

# 4. Create agent credentials (requires sudo)
sudo ejabberdctl register testagent localhost password123

# 5. Run the SPADE agent (no sudo needed)
python3 agent1.py
```

## Alternative: Using Docker (Simpler)

If you want to avoid permission issues, use Docker with pre-configured Ejabberd:

```bash
docker run -d --name ejabberd -p 5222:5222 -p 5269:5269 -p 5280:5280 ejabberd/ejabberd:latest

# Wait a few seconds for the server to start, then:
docker exec ejabberd ejabberdctl register testagent localhost password123

# Run your agent
python3 agent1.py
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Permission denied on ejabberdctl | Prefix command with `sudo` |
| Port 5222 already in use | Change XMPP port in Ejabberd config or kill existing process |
| Connection timeout | Ensure Ejabberd service is running: `sudo service ejabberd start` |
| Agent can't connect | Verify credentials match what was registered: `sudo ejabberdctl registered_users localhost` |

## Expected Output

When you run `python3 agent1.py`, you should see:

```
============================================================
SPADE Agent Framework - Basic Agent Example
============================================================

[STARTING] Launching agent...
[RUNNING] Agent is active. Running for 10 seconds...
✓ Greeting: Hello! I am agent testagent@localhost and I am now active.
✓ Monitoring: Agent testagent@localhost is running...
✓ Monitoring: Agent testagent@localhost is running...
...
[STOPPING] Shutting down agent...
[SUCCESS] Agent stopped successfully!
============================================================
```
