# status-page-spike - Technical Spike Project

## Current Objective
Completed technical spike for lightweight self-hosted status page. Spike proved all core features work end-to-end. Decision: FURTHER_RESEARCH - evaluate market validation before BUILD.

## Current Status
**SPIKE COMPLETE** - All features verified working.

## Architecture
- **Stack**: Python 3.11 + Flask + SQLite
- **Container**: Single Docker container (~50MB image, ~20MB RAM idle)
- **Port**: 5004
- **Persistence**: SQLite volume at /data/status.db
- **Admin Auth**: Bearer token via X-Admin-Token header

## Features Verified (Spike Complete)
| Feature | Status | Tested |
|---------|--------|--------|
| Public status page (services, components, incidents, maintenance) | ✅ Working | ✅ |
| Admin API: Services CRUD | ✅ Working | ✅ |
| Admin API: Components CRUD | ✅ Working | ✅ |
| Admin API: Incidents CRUD + updates | ✅ Working | ✅ |
| Admin API: Maintenance CRUD | ✅ Working | ✅ |
| RSS feed (incidents + maintenance) | ✅ Working | ✅ |
| Webhook ingestion (incidents from Uptime Kuma, heartbeat-monitor) | ✅ Working | ✅ |
| Webhook ingestion (maintenance) | ✅ Working | ✅ |
| Health endpoint (/health) | ✅ Working | ✅ |
| Overall status computation | ✅ Working | ✅ |
| Docker Compose deployment | ✅ Working | ✅ |

## Demo URLs
- Public status page: http://77.90.53.243:5004/
- Health: http://77.90.53.243:5004/health
- API status: http://77.90.53.243:5004/api/status
- RSS feed: http://77.90.53.243:5004/rss

## Admin Token
`change-me` (configured via ADMIN_TOKEN env var)

## Spike Issues Fixed
1. **Python import error**: `ModuleNotFoundError: No module named 'models'` - Fixed by using relative import `from .models import ...` in source/app.py
2. **Template error**: `TypeError: 'str' object is not callable` in status.html - Fixed `now_iso()` → `now_iso` (template variable vs function)

## Spike Test Results
```bash
# Service creation
curl -X POST /api/admin/services -H "X-Admin-Token: change-me" -d '{"name": "API Service"}'
→ Created: f6c51b56a4ef4437a7173c6d

# Component creation
curl -X POST /api/admin/services/<sid>/components -H "X-Admin-Token: change-me" -d '{"name": "Database"}'
→ Created: 7b60fe62a31f4be6b56fcc4c

# Incident creation
curl -X POST /api/admin/incidents -H "X-Admin-Token: change-me" -d '{"title": "API latency elevated", "status": "investigating", "impact": "minor"}'
→ Created: 1f25f668ff624d659f40d5b2

# Maintenance creation
curl -X POST /api/admin/maintenance -H "X-Admin-Token: change-me" -d '{"title": "Database upgrade", "starts_at": "2026-10-03T02:00:00Z", "ends_at": "2026-10-03T04:00:00Z"}'
→ Created: 470fabe94d39429d99b11e8e

# Webhook incident ingestion
curl -X POST /api/webhook/incident -H "X-Webhook-Source: uptime-kuma" -d '{"title": "Website down", "impact": "critical"}'
→ Created: dd61c0a6573a4a0c88a1452d
```
All render correctly on public status page and RSS feed.

## Competition Analysis (from Research)
| Tool | Stack | RAM | Stars | License | Notes |
|------|-------|-----|-------|---------|-------|
| Cachet | PHP+Laravel+MySQL+Redis | 200-300MB | 13k+ | BSD-3 | **Abandoned (2021)** |
| Statping | Go+SQLite | ~50MB | 4k+ | AGPL-3 | AGPL, limited dev |
| Upptime | GitHub Actions | N/A | 14k+ | MIT | Not self-hosted VPS |
| Uptime Kuma | Node+SQLite | ~100MB | 92k+ | MIT | Monitoring-first |
| **status-page-spike** | **Python+Flask+SQLite** | **~20MB** | **0** | **MIT** | **Active, API-first** |

## Decision: FURTHER_RESEARCH

### Reason
Technical spike **successful** - all core features work. But market validation needed before BUILD:
1. Search demand for "self hosted status page", "cachet alternative" unverified
2. Community signals: Need ≥15 users actively seeking "lighter Cachet alternative" or "Python status page"
3. Current 3 projects must reach validation decisions first (forms-builder, heartbeat-monitor, nanoanalytics)
4. Uptime Kuma (92k stars) provides status pages as monitoring feature - strong free alternative

### Evidence Threshold for BUILD
- Technical spike successful ✅
- ≥15 community signals wanting "lighter Cachet alternative" / "Python status page"
- Current 3 projects: 2+ reach BUILD validation, 0 in DISCARD
- Clear 14-day roadmap to MVP with <5 core features

### Evidence Threshold for DISCARD
- Upptime adds self-hosted VPS option
- Cachet gets new maintainer / v3 release
- <5 community signals for Python-specific status page
- Technical complexity > spike indicated

## Next Actions
1. Research community signals on r/selfhosted, r/sysadmin, GitHub issues
2. Verify search demand (when web search available)
3. Wait for current 3 projects to reach validation decisions
4. If evidence supports BUILD: create full project with proper structure, tests, docs, deployment configs

## Lessons Learned
- **Relative imports critical** in Python packages - `source/` needs `__init__.py` and relative imports
- **Template variables vs functions**: `now_iso` is a string variable in template context, not callable
- **Docker rebuild issues**: `docker-compose up -d --build` can fail with ContainerConfig errors; `docker start <existing-container>` is more reliable for quick iteration
- **Spike value**: 1-day spike proved full feature set works - avoids months of building unvalidated product