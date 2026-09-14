# Home SIEM Lab

A live detection environment built for hands-on SOC analyst practice. Wazuh SIEM on a dedicated Ubuntu server, with Kali Linux and Metasploitable 3 VMs on an isolated Lab VLAN. The goal: run real attack scenarios, watch them land in the SIEM, tune detection rules, and document findings — the same loop a Tier 1 analyst runs on shift.

**Full writeup:** [chascarden.com/siem-lab.html](https://chascarden.com/siem-lab.html)

---

## Architecture

| Machine | Role | OS | IP |
|---|---|---|---|
| X1 Carbon (host) | Wazuh SIEM Server | Ubuntu Server 24.04 LTS | 10.0.30.10 (static) |
| Kali VM | Attacker + monitored node | Kali Linux | 10.0.30.81 |
| Metasploitable 3 VM | Attack target | Ubuntu 14.04 | 10.0.30.8 |
| Raspberry Pi 4 | Monitored endpoint | Raspberry Pi OS | pending |

All lab machines live on **Lab VLAN 30** (10.0.30.x), isolated from the main LAN and IoT network by UniFi firewall rules. Lab machines can reach the internet for updates but cannot touch other VLANs — except for one deliberate exception: Wazuh agents ship logs to the SIEM server on the same VLAN. Isolation + visibility.

```
Main LAN (192.168.1.x)
        │
        ▼
  UniFi Firewall
   [DROP all inter-VLAN]
   [EXCEPT: log traffic from Lab → Wazuh]
        │
        ▼
  Lab VLAN 30 (10.0.30.x)
  ┌─────────────────────────────────┐
  │  X1 Carbon        10.0.30.10   │  ← Wazuh Manager + Indexer + Dashboard
  │  Kali VM          10.0.30.81   │  ← Attacker (Wazuh agent installed)
  │  Metasploitable 3 10.0.30.8    │  ← Target (Wazuh agent installed)
  └─────────────────────────────────┘
```

---

## Stack

| Tool | Role |
|---|---|
| [Wazuh 4.9.2](https://wazuh.com) | SIEM — Manager, Indexer, Dashboard (all-in-one) |
| VirtualBox 7.0.16 | Hypervisor for Kali + Metasploitable VMs |
| Kali Linux | Attack platform |
| Metasploitable 3 | Intentionally vulnerable target |
| UniFi UCG Max | Firewall / VLAN management |

---

## Build Status

- [x] UniFi Lab VLAN 30 created and isolated
- [x] X1 Carbon: Ubuntu Server 24.04, static IP 10.0.30.10
- [x] Wazuh 4.9.2 all-in-one installed, dashboard accessible at https://10.0.30.10
- [x] VirtualBox 7.0.16 installed (MOK key enrolled for Secure Boot)
- [x] Kali VM: running, Wazuh agent 4.9.2 connected
- [x] Metasploitable 3 VM: running, Wazuh agent 4.9.2 connected
- [x] Wazuh dashboard showing 2 active agents
- [ ] Raspberry Pi: Wazuh agent install pending
- [ ] First attack cycle documented with real alert output
- [ ] Custom detection rules written
- [ ] DVWA (web app target) added via Docker

---

## Planned Attack Scenarios

| Scenario | Tool | Detection Target |
|---|---|---|
| Port scan | Nmap | Wazuh rule 40101 (scan detected) |
| Service exploit | Metasploit | File integrity + process alerts |
| Brute force SSH | Hydra | Wazuh rule 5710 (auth failure flood) |
| Web app attacks | DVWA + Burp | Web log anomaly rules |
| Privilege escalation | manual | Audit log alerts |

Results will be documented in [`detection-logs/`](./detection-logs/) as each scenario is run.

---

## Setup Notes

Full step-by-step setup documented in [`docs/setup.md`](./docs/setup.md), including the three issues that took real time to solve:

- **ProtonVPN blocking Lab VLAN access** from the Mac
- **Boot hang** on the X1 Carbon (`systemd-networkd-wait-online`)
- **Wazuh agent version mismatch** (must pin agent to match manager version)

---

## Repo Structure

```
siem-lab/
├── README.md               — this file
├── docs/
│   └── setup.md            — full setup guide with troubleshooting
├── configs/
│   └── wazuh-agent.conf    — sanitized agent config template
└── detection-logs/
    └── (attack results added as scenarios are run)
```

---

## Related

- [Portfolio writeup](https://chascarden.com/siem-lab.html) — architecture + findings, formatted for job applications
- [Network segmentation guide](https://chascarden.com/network-segmentation.html) — the VLAN setup this lab sits on
