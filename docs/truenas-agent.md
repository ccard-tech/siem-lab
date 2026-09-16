# TrueNAS Wazuh Agent

Deploying a Wazuh agent on TrueNAS SCALE to monitor a production homelab server alongside the lab VMs.

---

## Why Docker

TrueNAS SCALE has a read-only root filesystem. `apt install` works but gets wiped on every system update — packages installed directly don't survive reboots or upgrades. Docker containers persist because they live on the ZFS data pool (`tank_2`), not the system partition.

There is no official standalone Wazuh agent image on Docker Hub. The solution is a custom Dockerfile built from `debian:12-slim`.

---

## Files

Three files go in `/mnt/tank_2/docker/stacks/wazuh-agent/`:

### Dockerfile

```dockerfile
FROM debian:12-slim

RUN apt-get update && apt-get install -y curl gnupg && \
    curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | \
      gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import && \
    chmod 644 /usr/share/keyrings/wazuh.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
      > /etc/apt/sources.list.d/wazuh.list && \
    apt-get update && \
    apt-get install -y wazuh-agent=4.9.2-1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

Pin `wazuh-agent` to the exact manager version or the agent will fail to register ("version must be lower or equal to manager").

### entrypoint.sh

```sh
#!/bin/sh
sed -i "s|<address>.*</address>|<address>${WAZUH_MANAGER}</address>|" /var/ossec/etc/ossec.conf
/var/ossec/bin/wazuh-execd
/var/ossec/bin/wazuh-agentd
/var/ossec/bin/wazuh-logcollector
/var/ossec/bin/wazuh-syscheckd
/var/ossec/bin/wazuh-modulesd
tail -f /var/ossec/logs/ossec.log
```

Start each daemon explicitly. `wazuh-control start` does not reliably restart all daemons inside a container — only `wazuh-execd` and `wazuh-agentd` come back consistently. Calling each binary directly ensures the full stack runs on every container start.

Use `#!/bin/sh` not `#!/bin/bash` — bash is not installed in `debian:12-slim`.

### compose.yaml

```yaml
services:
  wazuh-agent:
    build: .
    container_name: wazuh-agent
    hostname: truenas
    restart: unless-stopped
    network_mode: host
    pid: host
    privileged: true
    environment:
      - WAZUH_MANAGER=10.0.30.10
      - WAZUH_AGENT_NAME=truenas
    volumes:
      - /var/log:/var/log:ro
      - /etc:/host/etc:ro
```

`privileged: true` + `network_mode: host` + `pid: host` lets Wazuh see through the container into the actual TrueNAS host. Without these, it only monitors container internals.

---

## Build and Start

```bash
cd /mnt/tank_2/docker/stacks/wazuh-agent
sudo docker compose build --no-cache
sudo docker compose up -d
sudo docker exec wazuh-agent cat /var/ossec/logs/ossec.log | tail -20
```

Look for `Connected to the server ([10.0.30.10]:1514/tcp)` in the log.

`wazuh-control status` will report all daemons as "not running" even when they are — it checks PID files which don't work correctly in Docker. Use the ossec.log to verify instead.

---

## Firewall

TrueNAS (main LAN) and the Wazuh manager (Lab VLAN 30) are on different VLANs separated by UniFi firewall rules. The agent needs outbound access to the manager on port 1514 TCP.

**Option A (simpler):** Exclude TrueNAS's IP from the Lab VLAN drop rule entirely. TrueNAS is a trusted device — acceptable for a home lab.

**Option B (tighter):** Create a specific allow policy above the drop rule:
- Source: TrueNAS IP
- Destination: Wazuh manager IP, port 1514 TCP
- Action: Allow

Test connectivity before starting the agent:

```bash
timeout 3 bash -c 'cat < /dev/null > /dev/tcp/10.0.30.10/1514' && echo "port open" || echo "port blocked"
```

Traffic is one-way outbound only — the agent ships logs to the manager. Nothing on the lab network can initiate a connection back to TrueNAS.

---

## What Gets Monitored

With `/var/log` mounted from the host, the agent collects:

- SSH authentication events (auth.log)
- PAM session open/close
- Cron job execution
- Package manager activity (dpkg.log)

Wazuh also runs an automatic **CIS Debian Family Linux Benchmark** compliance scan on connect and maps all events to **MITRE ATT&CK** tactics automatically.

---

## Gotchas

**CRLF line endings in entrypoint.sh**
If you create the file with nano and paste content from a clipboard, the shell script may get Windows-style line endings (CRLF) which cause `exec format error` on container start. Use `tee` with a heredoc instead:

```bash
sudo tee /mnt/tank_2/docker/stacks/wazuh-agent/entrypoint.sh << 'EOF'
#!/bin/sh
...
EOF
```

The single quotes around `'EOF'` prevent the shell from expanding variables before writing — `${WAZUH_MANAGER}` stays as a literal string to be expanded at container runtime.

**Docker cache doesn't pick up file edits**
If you edit `entrypoint.sh` after a build, the `COPY` layer will be cached and the fix won't apply. Always use `--no-cache` after editing:

```bash
sudo docker compose build --no-cache
```

**Do not install wazuh-agent on the X1 Carbon**
`wazuh-agent` and `wazuh-manager` conflict — installing the agent removes the manager. The X1 Carbon (Wazuh server) is already monitored as agent 000 built into the manager. No separate agent install needed.
