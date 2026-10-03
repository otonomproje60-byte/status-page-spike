import os
import json
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, abort, make_response
import markdown

from .models import (
    init_db, now_iso, gen_id, verify_admin_token,
    create_service, get_service, list_services, update_service_status,
    create_component, get_component, list_components, update_component_status,
    create_incident, get_incident, list_incidents, update_incident, add_incident_update,
    create_maintenance, get_maintenance, list_maintenance, update_maintenance,
    log_webhook, list_webhook_logs,
    get_public_status
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-change-me")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me")

# Initialize DB on startup
with app.app_context():
    init_db()

# ============================================================
# Auth Helpers
# ============================================================

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Admin-Token") or request.args.get("admin_token")
        if not verify_admin_token(token):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ============================================================
# Public Status Page Routes
# ============================================================

@app.route("/")
def status_page():
    """Public status page"""
    data = get_public_status()
    # Compute overall status
    overall = "operational"
    for svc in data["services"]:
        if svc["status"] != "operational":
            overall = "degraded"
            break
        for comp in svc["components"]:
            if comp["status"] != "operational":
                overall = "degraded"
                break
    if data["incidents"]:
        # Check if any incident is critical/major
        for inc in data["incidents"]:
            if inc["impact"] in ("critical", "major"):
                overall = "major_outage"
                break
            elif inc["impact"] == "minor" and overall == "operational":
                overall = "degraded"
    return render_template("status.html", data=data, overall=overall, now_iso=now_iso())

@app.route("/api/status")
def api_status():
    """Public API: current status summary"""
    data = get_public_status()
    return jsonify(data)

@app.route("/api/services")
def api_services():
    """Public API: list all services with components"""
    return jsonify(list_services())

@app.route("/api/incidents")
def api_incidents():
    """Public API: list incidents"""
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 100)
    return jsonify(list_incidents(limit=limit, status=status))

@app.route("/api/maintenance")
def api_maintenance():
    """Public API: list maintenance windows"""
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 100)
    return jsonify(list_maintenance(limit=limit, status=status))

@app.route("/rss")
def rss_feed():
    """RSS feed for incidents and maintenance"""
    data = get_public_status()
    items = []
    for inc in data["incidents"]:
        for upd in inc["updates"]:
            items.append({
                "title": f"[{inc['impact'].upper()}] {inc['title']} - {upd['status']}",
                "description": markdown.markdown(upd["body"]),
                "link": request.url_root.rstrip("/") + f"#incident-{inc['id']}",
                "pubDate": upd["created_at"],
                "guid": f"incident-{inc['id']}-{upd['id']}"
            })
    for maint in data["maintenance"]:
        items.append({
            "title": f"Maintenance: {maint['title']} - {maint['status']}",
            "description": markdown.markdown(maint["description"] or ""),
            "link": request.url_root.rstrip("/") + f"#maintenance-{maint['id']}",
            "pubDate": maint["updated_at"],
            "guid": f"maintenance-{maint['id']}"
        })
    items.sort(key=lambda x: x["pubDate"], reverse=True)
    
    rss = render_template("rss.xml", items=items, title="Status Page Feed", link=request.url_root)
    response = make_response(rss)
    response.headers["Content-Type"] = "application/xml"
    return response

# ============================================================
# Admin API Routes
# ============================================================

# Services
@app.route("/api/admin/services", methods=["POST"])
@require_admin
def admin_create_service():
    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "name required"}), 400
    svc = create_service(data["name"], data.get("description", ""))
    return jsonify(svc), 201

@app.route("/api/admin/services", methods=["GET"])
@require_admin
def admin_list_services():
    return jsonify(list_services())

@app.route("/api/admin/services/<sid>", methods=["GET"])
@require_admin
def admin_get_service(sid):
    svc = get_service(sid)
    if not svc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(svc)

@app.route("/api/admin/services/<sid>", methods=["PATCH"])
@require_admin
def admin_update_service(sid):
    data = request.get_json() or {}
    if "status" in data:
        update_service_status(sid, data["status"])
    return jsonify(get_service(sid))

# Components
@app.route("/api/admin/services/<sid>/components", methods=["POST"])
@require_admin
def admin_create_component(sid):
    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "name required"}), 400
    comp = create_component(sid, data["name"], data.get("description", ""), data.get("status", "operational"))
    return jsonify(comp), 201

@app.route("/api/admin/components/<cid>", methods=["PATCH"])
@require_admin
def admin_update_component(cid):
    data = request.get_json() or {}
    if "status" in data:
        update_component_status(cid, data["status"])
    return jsonify(get_component(cid))

# Incidents
@app.route("/api/admin/incidents", methods=["POST"])
@require_admin
def admin_create_incident():
    data = request.get_json() or {}
    if not data.get("title"):
        return jsonify({"error": "title required"}), 400
    inc = create_incident(
        data["title"],
        data.get("status", "investigating"),
        data.get("impact", "minor"),
        data.get("started_at")
    )
    if data.get("initial_update"):
        add_incident_update(inc["id"], data.get("status", "investigating"), data["initial_update"])
    return jsonify(inc), 201

@app.route("/api/admin/incidents", methods=["GET"])
@require_admin
def admin_list_incidents():
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 100)
    return jsonify(list_incidents(limit=limit, status=status))

@app.route("/api/admin/incidents/<iid>", methods=["PATCH"])
@require_admin
def admin_update_incident(iid):
    data = request.get_json() or {}
    inc = update_incident(iid, **data)
    if not inc:
        return jsonify({"error": "Not found"}), 404
    if data.get("update_body"):
        add_incident_update(iid, data.get("status", inc["status"]), data["update_body"])
    return jsonify(get_incident(iid))

@app.route("/api/admin/incidents/<iid>/updates", methods=["POST"])
@require_admin
def admin_add_incident_update(iid):
    data = request.get_json() or {}
    if not data.get("body"):
        return jsonify({"error": "body required"}), 400
    upd = add_incident_update(iid, data.get("status", "monitoring"), data["body"])
    return jsonify(upd), 201

# Maintenance
@app.route("/api/admin/maintenance", methods=["POST"])
@require_admin
def admin_create_maintenance():
    data = request.get_json() or {}
    required = ["title", "starts_at", "ends_at"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} required"}), 400
    maint = create_maintenance(
        data["title"],
        data.get("description", ""),
        data["starts_at"],
        data["ends_at"],
        data.get("status", "scheduled")
    )
    return jsonify(maint), 201

@app.route("/api/admin/maintenance", methods=["GET"])
@require_admin
def admin_list_maintenance():
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 50)), 100)
    return jsonify(list_maintenance(limit=limit, status=status))

@app.route("/api/admin/maintenance/<mid>", methods=["PATCH"])
@require_admin
def admin_update_maintenance(mid):
    data = request.get_json() or {}
    maint = update_maintenance(mid, **data)
    if not maint:
        return jsonify({"error": "Not found"}), 404
    return jsonify(maint)

# Webhook Ingestion (for external monitors)
@app.route("/api/webhook/incident", methods=["POST"])
def webhook_incident():
    """Receive incident webhook from external monitors (Uptime Kuma, heartbeat-monitor, etc.)"""
    source = request.headers.get("X-Webhook-Source", "unknown")
    payload = request.get_json() or {}
    
    try:
        # Expected payload format:
        # {
        #   "title": "Service X is down",
        #   "status": "investigating",
        #   "impact": "major",
        #   "started_at": "2026-10-02T10:00:00Z",
        #   "service_id": "optional-service-id",
        #   "component_id": "optional-component-id"
        # }
        
        if not payload.get("title"):
            log_webhook(source, payload, False)
            return jsonify({"error": "title required"}), 400
        
        inc = create_incident(
            payload["title"],
            payload.get("status", "investigating"),
            payload.get("impact", "minor"),
            payload.get("started_at")
        )
        
        # Add initial update
        body = payload.get("body", f"Auto-created from {source} webhook")
        add_incident_update(inc["id"], payload.get("status", "investigating"), body)
        
        log_webhook(source, payload, True)
        return jsonify({"incident_id": inc["id"], "status": "created"}), 201
        
    except Exception as e:
        log_webhook(source, payload, False)
        return jsonify({"error": str(e)}), 500

@app.route("/api/webhook/maintenance", methods=["POST"])
def webhook_maintenance():
    """Receive maintenance webhook from external systems"""
    source = request.headers.get("X-Webhook-Source", "unknown")
    payload = request.get_json() or {}
    
    try:
        required = ["title", "starts_at", "ends_at"]
        for field in required:
            if not payload.get(field):
                log_webhook(source, payload, False)
                return jsonify({"error": f"{field} required"}), 400
        
        maint = create_maintenance(
            payload["title"],
            payload.get("description", ""),
            payload["starts_at"],
            payload["ends_at"],
            payload.get("status", "scheduled")
        )
        
        log_webhook(source, payload, True)
        return jsonify({"maintenance_id": maint["id"], "status": "created"}), 201
        
    except Exception as e:
        log_webhook(source, payload, False)
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/webhooks/logs", methods=["GET"])
@require_admin
def admin_webhook_logs():
    limit = min(int(request.args.get("limit", 50)), 100)
    return jsonify(list_webhook_logs(limit=limit))

# Comparison page (SEO/content)
@app.route("/compare")
def compare():
    """Serve the comparison page from docs/status-page-vs-cachet-statping-uptime.md."""
    import os
    comparison_path = os.path.join(os.path.dirname(__file__), "..", "docs", "status-page-vs-cachet-statping-uptime.md")
    try:
        with open(comparison_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        content = "Comparison page not found."
    return render_template("compare.html", content=content)


# Health check
@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "status-page-spike"})


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "service": "status-page-spike"})

# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5004"))
    app.run(host="0.0.0.0", port=port, debug=False)