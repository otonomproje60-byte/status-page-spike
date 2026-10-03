import os
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from contextlib import contextmanager
from functools import wraps

DATABASE_PATH = os.getenv("DB_PATH", "/data/status.db")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me")

# ============================================================
# Database Helpers
# ============================================================

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'operational',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL,  -- investigating, identified, monitoring, resolved
                impact TEXT NOT NULL,  -- none, minor, major, critical
                started_at TEXT NOT NULL,
                resolved_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS incident_updates (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                status TEXT NOT NULL,
                body TEXT NOT NULL,  -- markdown
                created_at TEXT NOT NULL,
                FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS maintenance_windows (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,  -- markdown
                status TEXT NOT NULL,  -- scheduled, in_progress, completed, cancelled
                starts_at TEXT NOT NULL,
                ends_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS components (
                id TEXT PRIMARY KEY,
                service_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'operational',  -- operational, degraded, partial_outage, major_outage
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS webhook_logs (
                id TEXT PRIMARY KEY,
                source TEXT,
                payload TEXT,
                processed_at TEXT NOT NULL,
                success INTEGER NOT NULL
            );
        """)

def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def gen_id():
    import uuid
    return uuid.uuid4().hex[:24]

# ============================================================
# Service Operations
# ============================================================

def create_service(name, description=""):
    sid = gen_id()
    now = now_iso()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO services (id, name, description, status, created_at, updated_at)
            VALUES (?, ?, ?, 'operational', ?, ?)
        """, (sid, name, description, now, now))
    return get_service(sid)

def get_service(sid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM services WHERE id = ?", (sid,)).fetchone()
    return dict(row) if row else None

def list_services():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM services ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]

def update_service_status(sid, status):
    with get_db() as conn:
        conn.execute("""
            UPDATE services SET status = ?, updated_at = ? WHERE id = ?
        """, (status, now_iso(), sid))

# ============================================================
# Component Operations
# ============================================================

def create_component(service_id, name, description="", status="operational"):
    cid = gen_id()
    now = now_iso()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO components (id, service_id, name, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (cid, service_id, name, description, status, now, now))
    return get_component(cid)

def get_component(cid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM components WHERE id = ?", (cid,)).fetchone()
    return dict(row) if row else None

def list_components(service_id):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM components WHERE service_id = ? ORDER BY created_at", (service_id,)).fetchall()
    return [dict(r) for r in rows]

def update_component_status(cid, status):
    with get_db() as conn:
        conn.execute("""
            UPDATE components SET status = ?, updated_at = ? WHERE id = ?
        """, (status, now_iso(), cid))

# ============================================================
# Incident Operations
# ============================================================

def create_incident(title, status="investigating", impact="minor", started_at=None):
    iid = gen_id()
    now = now_iso()
    if started_at is None:
        started_at = now
    with get_db() as conn:
        conn.execute("""
            INSERT INTO incidents (id, title, status, impact, started_at, resolved_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
        """, (iid, title, status, impact, started_at, now, now))
    return get_incident(iid)

def get_incident(iid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id = ?", (iid,)).fetchone()
    if not row:
        return None
    incident = dict(row)
    # Get updates
    with get_db() as conn:
        updates = conn.execute("""
            SELECT * FROM incident_updates WHERE incident_id = ? ORDER BY created_at
        """, (iid,)).fetchall()
    incident["updates"] = [dict(u) for u in updates]
    return incident

def list_incidents(limit=50, status=None):
    with get_db() as conn:
        if status:
            rows = conn.execute("""
                SELECT * FROM incidents WHERE status = ? ORDER BY started_at DESC LIMIT ?
            """, (status, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM incidents ORDER BY started_at DESC LIMIT ?
            """, (limit,)).fetchall()
    incidents = []
    for row in rows:
        incident = dict(row)
        with get_db() as conn:
            updates = conn.execute("""
                SELECT * FROM incident_updates WHERE incident_id = ? ORDER BY created_at
            """, (incident["id"],)).fetchall()
        incident["updates"] = [dict(u) for u in updates]
        incidents.append(incident)
    return incidents

def update_incident(iid, **kwargs):
    allowed = {"title", "status", "impact", "resolved_at"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return get_incident(iid)
    fields["updated_at"] = now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_db() as conn:
        conn.execute(f"UPDATE incidents SET {set_clause} WHERE id = ?", 
                     list(fields.values()) + [iid])
    return get_incident(iid)

def add_incident_update(iid, status, body):
    uid = gen_id()
    now = now_iso()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO incident_updates (id, incident_id, status, body, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (uid, iid, status, body, now))
    return get_incident_update(uid)

def get_incident_update(uid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM incident_updates WHERE id = ?", (uid,)).fetchone()
    return dict(row) if row else None

# ============================================================
# Maintenance Window Operations
# ============================================================

def create_maintenance(title, description, starts_at, ends_at, status="scheduled"):
    mid = gen_id()
    now = now_iso()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO maintenance_windows (id, title, description, status, starts_at, ends_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (mid, title, description, status, starts_at, ends_at, now, now))
    return get_maintenance(mid)

def get_maintenance(mid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM maintenance_windows WHERE id = ?", (mid,)).fetchone()
    return dict(row) if row else None

def list_maintenance(limit=50, status=None):
    with get_db() as conn:
        if status:
            rows = conn.execute("""
                SELECT * FROM maintenance_windows WHERE status = ? ORDER BY starts_at DESC LIMIT ?
            """, (status, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM maintenance_windows ORDER BY starts_at DESC LIMIT ?
            """, (limit,)).fetchall()
    return [dict(r) for r in rows]

def update_maintenance(mid, **kwargs):
    allowed = {"title", "description", "status", "starts_at", "ends_at"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return get_maintenance(mid)
    fields["updated_at"] = now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_db() as conn:
        conn.execute(f"UPDATE maintenance_windows SET {set_clause} WHERE id = ?", 
                     list(fields.values()) + [mid])
    return get_maintenance(mid)

# ============================================================
# Webhook Logging
# ============================================================

def log_webhook(source, payload, success):
    wid = gen_id()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO webhook_logs (id, source, payload, processed_at, success)
            VALUES (?, ?, ?, ?, ?)
        """, (wid, source, json.dumps(payload), now_iso(), int(success)))

def list_webhook_logs(limit=50):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM webhook_logs ORDER BY processed_at DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]

# ============================================================
# Admin Auth
# ============================================================

def verify_admin_token(token):
    return token == ADMIN_TOKEN

# ============================================================
# Public Status Data (for status page rendering)
# ============================================================

def get_public_status():
    """Get all data needed for public status page"""
    with get_db() as conn:
        services = conn.execute("SELECT * FROM services ORDER BY created_at").fetchall()
        result = {"services": [], "incidents": [], "maintenance": []}
        
        for svc in services:
            svc_dict = dict(svc)
            components = conn.execute("""
                SELECT * FROM components WHERE service_id = ? ORDER BY created_at
            """, (svc["id"],)).fetchall()
            svc_dict["components"] = [dict(c) for c in components]
            result["services"].append(svc_dict)
        
        # Open incidents (not resolved)
        incidents = conn.execute("""
            SELECT * FROM incidents WHERE status != 'resolved' ORDER BY started_at DESC LIMIT 10
        """).fetchall()
        for inc in incidents:
            inc_dict = dict(inc)
            updates = conn.execute("""
                SELECT * FROM incident_updates WHERE incident_id = ? ORDER BY created_at
            """, (inc["id"],)).fetchall()
            inc_dict["updates"] = [dict(u) for u in updates]
            result["incidents"].append(inc_dict)
        
        # Upcoming/active maintenance
        now = now_iso()
        maintenance = conn.execute("""
            SELECT * FROM maintenance_windows 
            WHERE status IN ('scheduled', 'in_progress') AND ends_at > ?
            ORDER BY starts_at
        """, (now,)).fetchall()
        result["maintenance"] = [dict(m) for m in maintenance]
        
    return result