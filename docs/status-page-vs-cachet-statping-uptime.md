# Status Page Spike: Lightweight Self-Hosted Status Page / Incident Communication

**Status Page Spike** is a minimal, Python-based status page for teams who need to communicate service health, incidents, and maintenance windows — without the bloat of legacy tools.

---

## The Problem: Cachet Is Abandoned, Alternatives Are Heavy or Wrong License

| Tool | Stack | RAM | Containers | License | Status |
|------|-------|-----|------------|---------|--------|
| **Cachet** | PHP + Laravel + MySQL + Redis | 200-300MB | 3+ | BSD-3 | **Abandoned (2021)** |
| **Statping** | Go + SQLite/MySQL | ~50MB | 1-2 | AGPL-3 | Limited dev since 2022 |
| **Upptime** | GitHub Actions + Issues | N/A | N/A | MIT | Not self-hosted on your VPS |
| **Uptime Kuma** | Node + SQLite | ~100MB | 1 | MIT | Monitoring-first, status page secondary |
| **Status Page Spike** | **Python + Flask + SQLite** | **~20MB** | **1** | **MIT** | **Active, API-first** |

---

## Why Status Page Spike?

### 1. **Python + SQLite + Flask = Hackable & Lightweight**
- Single container, ~20MB RAM idle
- No external databases, no Redis, no message queues
- Runs on a Raspberry Pi or smallest VPS
- Python = easy to customize for your workflow

### 2. **Focus on Communication, Not Monitoring**
- Built for **incident communication** and **maintenance scheduling**
- Integrates with your existing monitors via **webhooks** (Uptime Kuma, heartbeat-monitor, Prometheus Alertmanager, etc.)
- You monitor with Uptime Kuma / Prometheus / heartbeat-monitor; Spike communicates status to your users

### 3. **API-First Design**
- Full Admin API (Services, Components, Incidents, Maintenance CRUD)
- Public API for status display
- Webhook ingestion endpoints for automated incident creation
- RSS feed for subscribers

### 4. **MIT Licensed — No AGPL Concerns**
- Unlike Statping (AGPL-3), Spike is MIT — use it commercially, embed it, fork it, no viral license traps

---

## Feature Comparison

| Feature | Cachet | Statping | Upptime | Uptime Kuma | **Status Page Spike** |
|---------|--------|----------|---------|-------------|----------------------|
| Public Status Page | ✅ | ✅ | ✅ | ✅ | ✅ |
| Incident Timeline | ✅ | ✅ | ✅ | ✅ | ✅ |
| Maintenance Windows | ✅ | ✅ | ✅ | ✅ | ✅ |
| Markdown Incident Updates | ✅ | ✅ | ✅ | ✅ | ✅ |
| RSS/Atom Feed | ✅ | ❌ | ✅ | ❌ | ✅ |
| Webhook Ingestion | ✅ | ✅ | ❌ | ✅ | ✅ |
| API-First | Partial | Partial | No | Partial | **Yes** |
| Single Container | ❌ (3+) | ✅ | N/A | ✅ | ✅ |
| RAM Usage | 200-300MB | ~50MB | N/A | ~100MB | **~20MB** |
| Self-Hosted on Your VPS | ✅ | ✅ | ❌ (GitHub only) | ✅ | ✅ |
| License | BSD-3 | **AGPL-3** | MIT | MIT | **MIT** |
| Active Maintenance | **No (2021)** | Low (2022) | Active | Active | **Active** |
| Python Stack | ❌ (PHP) | ❌ (Go) | ❌ (JS) | ❌ (Node) | **✅ Python** |

---

## Core Features (Spike Complete, All Verified)

### Public Status Page
- Services with components (hierarchical)
- Overall status computation (operational / degraded / major_outage)
- Incident timeline with markdown updates
- Scheduled maintenance display
- Responsive, clean UI

### Admin API (Bearer Token Auth)
- `POST/GET/PATCH/DELETE /api/admin/services` — Service CRUD
- `POST/GET/PATCH /api/admin/services/<id>/components` — Component CRUD
- `POST/GET/PATCH /api/admin/incidents` — Incident CRUD + updates
- `POST/GET/PATCH /api/admin/maintenance` — Maintenance CRUD
- `GET /api/admin/webhooks/logs` — Webhook delivery audit log

### Public API
- `GET /api/status` — Full status summary
- `GET /api/services` — Services with components
- `GET /api/incidents` — Filterable incident list
- `GET /api/maintenance` — Filterable maintenance list
- `GET /rss` — RSS feed for incidents + maintenance

### Webhook Ingestion (For Monitor Integration)
```bash
# From Uptime Kuma, heartbeat-monitor, Prometheus Alertmanager, etc.
curl -X POST /api/webhook/incident \
  -H "X-Webhook-Source: uptime-kuma" \
  -d '{"title": "API latency elevated", "impact": "minor", "status": "investigating"}'

curl -X POST /api/webhook/maintenance \
  -H "X-Webhook-Source: custom" \
  -d '{"title": "Database upgrade", "starts_at": "2026-10-03T02:00:00Z", "ends_at": "2026-10-03T04:00:00Z"}'
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/yourorg/status-page-spike
cd status-page-spike

# 2. Configure
cp .env.example .env
# Edit ADMIN_TOKEN in .env

# 3. Deploy
docker compose up -d

# 4. Access
# Public status page: http://your-server:5004/
# Admin API: Bearer token from ADMIN_TOKEN
# Health check: http://your-server:5004/health
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Flask App (Python 3.11)             │   │
│  │  • Public routes (status page, API, RSS)         │   │
│  │  • Admin API (Bearer token)                      │   │
│  │  • Webhook ingestion (no auth, source header)    │   │
│  └──────────────────────────────────────────────────┘   │
│                           │                              │
│                           ▼                              │
│  ┌──────────────────────────────────────────────────┐   │
│  │            SQLite Database (/data/status.db)     │   │
│  │  • services, components, incidents, updates     │   │
│  │  • maintenance windows, webhook logs             │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
         ▲                    ▲
         │                    │
    Public/API          Admin (Bearer Token)
    Webhook (header)     Management
```

---

## Use Cases

### Homelab Status Page
Communicate status of your self-hosted services (Home Assistant, Plex, Nextcloud, custom apps) to family/housemates.

### Team/Startup Status Page
Free, self-hosted alternative to Atlassian Statuspage ($$$) or Better Uptime ($$$). Own your data, run on your infra.

### Project Status Page
Open source projects wanting a professional status page without SaaS costs.

### Monitoring Integration
Already using Uptime Kuma / Prometheus / heartbeat-monitor? Add Spike as the communication layer — webhooks auto-create incidents.

---

## Deployment Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 0.1 vCPU | 0.25 vCPU |
| RAM | 20MB | 30MB |
| Disk | 50MB | 100MB+ |
| OS | Linux (ARM64/AMD64) | Linux |
| Docker | 20.10+ | 24.0+ |

---

## Roadmap (If Validated)

- [ ] Subscriber notifications (email/webhook) for incidents
- [ ] Custom domain / subpath hosting
- [ ] i18n support
- [ ] Metrics charts on component pages
- [ ] Private status pages (auth required)
- [ ] Terraform/Ansible modules
- [ ] Helm chart for Kubernetes

---

## Demo

**Live Demo**: http://77.90.53.243:5004/
- Public status page with sample services, incidents, maintenance
- Health endpoint: http://77.90.53.243:5004/health
- API status: http://77.90.53.243:5004/api/status
- RSS feed: http://77.90.53.243:5004/rss

---

## Why Not Just Use Uptime Kuma's Status Page?

Uptime Kuma (92k stars) is excellent for **monitoring**. Its status page is a **feature**, not a dedicated product:

| Aspect | Uptime Kuma Status Page | Status Page Spike |
|--------|------------------------|-------------------|
| Primary purpose | Monitoring | **Communication** |
| Customization | Limited | **Full (Python/Flask)** |
| Incident workflow | Basic | **Rich (markdown, updates, impact)** |
| Maintenance windows | Basic | **Full scheduling + display** |
| RSS feed | No | **Yes** |
| API-first | No | **Yes** |
| Stack | Node.js | **Python** |
| Run alongside monitored services? | Separate or same | **Same tiny container** |

**Use both**: Uptime Kuma monitors → webhook → Spike communicates.

---

## Why Not Upptime?

Upptime (14k stars) is clever — uses GitHub Actions + Issues as backend.

| Aspect | Upptime | Status Page Spike |
|--------|---------|-------------------|
| Infrastructure | GitHub (required) | **Your VPS** |
| Cost | Free (GitHub) | Your VPS cost |
| Customization | Limited (GitHub Issues) | **Full control** |
| Private/Internal | No (public GitHub) | **Yes** |
| Real-time updates | GitHub Actions schedule | **Instant (webhook)** |
| Data ownership | GitHub | **Yours (SQLite file)** |

---

## Community & Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **License**: MIT
- **Contributions**: Welcome (PRs, issues, docs)

---

## Related Projects

- **heartbeat-monitor** — Lightweight cron/backup job monitoring (Python + Flask + SQLite, ~20MB RAM)
- **forms-builder** — Lightweight form endpoint/builder (Python + FastAPI + SQLite)
- **NanoAnalytics** — Lightweight privacy-friendly analytics (Python + Flask + SQLite, 9★ upstream)

---

*Status Page Spike is a technical spike proving the concept works. If you find this useful, star the repo and open issues for features you need. Validation signals determine if this becomes a full BUILD project.*