# Setup Guide

Full build notes for the home SIEM lab. This covers the actual steps taken, not an idealized walkthrough — including the three things that broke and how they were fixed.

---

## 1. Network — UniFi Lab VLAN 30

**Goal:** Isolate lab machines from the main LAN and IoT VLAN, while allowing Wazuh log traffic to flow within the lab.

1. In UniFi Network → Settings → Networks → Add New Network
   - Name: `Lab`
   - VLAN ID: `30`
   - Subnet: `10.0.30.1/24`
   - DHCP: enabled

2. Create firewall rules to block inter-VLAN traffic (Lab → Main LAN, Lab → IoT)

3. **Gotcha — UniFi 10.37.x rule ordering:** Accept rules always appear below Drop rules in the same policy table and cannot be reordered via drag or priority field. Don't add an Accept rule to allow specific traffic through a Drop — it will never fire. Instead, modify the Drop rule itself to exclude specific source/destination ranges.

---

## 2. X1 Carbon — Ubuntu Server 24.04

**Hardware:** Lenovo ThinkPad X1 Carbon 3rd gen, 16GB RAM

1. Install Ubuntu Server 24.04 LTS (standard install)
2. Set static IP via netplan:

```yaml
# /etc/netplan/00-installer-config.yaml
# chmod 600 required
network:
  version: 2
  renderer: NetworkManager
  wifis:
    wlp2s0:
      dhcp4: false
      addresses: [10.0.30.10/24]
      routes:
        - to: default
          via: 10.0.30.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
      access-points:
        "YOUR_SSID":
          password: "YOUR_PASSWORD"
```

**Notes:**
- Interface name is `wlp2s0` — looks like `wip2so` on screen (lowercase L, zero not O)
- Use `NetworkManager` renderer, not default `networkd`, for WiFi reliability
- File must be `chmod 600` or netplan will ignore it

Apply: `sudo netplan apply`

---

## 3. Fix — Boot Hang (`systemd-networkd-wait-online`)

**Problem:** After every reboot, the server hung at boot and required a physical console login before SSH would respond. Caused by `systemd-networkd-wait-online` timing out on the unused ethernet port while NetworkManager handled WiFi.

**Fix:**
```bash
sudo systemctl disable systemd-networkd-wait-online.service
sudo systemctl mask systemd-networkd-wait-online.service
```

SSH comes up immediately after reboot with no console login required.

---

## 4. Wazuh — All-in-One Install

```bash
curl -sO https://packages.wazuh.com/4.9/wazuh-install.sh
curl -sO https://packages.wazuh.com/4.9/config.yml
```

Edit `config.yml` — set the node IP to `10.0.30.10`, then:

```bash
sudo bash wazuh-install.sh -a
```

Dashboard is available at `https://10.0.30.10` after install. Save the generated admin credentials.

---

## 5. VirtualBox — Kali and Metasploitable 3 VMs

```bash
sudo apt install virtualbox
```

**Secure Boot note:** VirtualBox kernel modules require a MOK (Machine Owner Key) to be enrolled for Secure Boot. During install, set a MOK password, reboot, and enroll the key in the MOK manager that appears at boot.

**VM networking:** Set both VMs to use a Host-Only Adapter bridged to the Lab VLAN interface so they get IPs on 10.0.30.x and can reach the Wazuh server.

---

## 6. Wazuh Agent Install — Fix: Version Pin

**Problem:** Kali's apt repo installs the latest Wazuh agent. If the manager is 4.9.2 and the agent is newer (e.g. 4.14.7), the agent registers but immediately errors: "version must be lower or equal to manager."

**Fix — pin the agent to match the manager:**

```bash
# On each agent machine (Kali, Metasploitable, RPi)
curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | gpg --dearmor -o /usr/share/keyrings/wazuh.gpg
echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" | sudo tee /etc/apt/sources.list.d/wazuh.list
sudo apt update
sudo WAZUH_AGENT_VERSION='4.9.2-1' apt install wazuh-agent=4.9.2-1 -y

# Set manager IP
sudo sed -i 's/<address>.*<\/address>/<address>10.0.30.10<\/address>/' /var/ossec/etc/ossec.conf

# Start and enable agent
sudo systemctl enable wazuh-agent
sudo systemctl start wazuh-agent
```

Apply this same version pin to every agent added (RPi, any future machines).

---

## 7. Fix — ProtonVPN Blocking Lab VLAN Access from Mac

**Problem:** ProtonVPN on the Mac creates a `utun4` interface at `10.2.0.x` that intercepts all `10.x.x.x` traffic, including `10.0.30.x`. SSH to the X1 Carbon times out even though routing is otherwise correct.

**Fix — add a static route to bypass the VPN for Lab traffic:**

```bash
sudo route add -net 10.0.30.0/24 192.168.1.1
```

This survives until the Mac reboots. To make it permanent, add it to a login script or LaunchDaemon. Does not affect any other traffic.
