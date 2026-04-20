/**
 * Intake IQ Worker - API for synthetic call center analytics dashboard
 * Bindings: DB (D1) - intakeiq-db
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}

function err(msg, status = 500) {
  return json({ error: msg }, status);
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    try {
      // ================================================================
      // GET /api/firms - all firms with call counts
      // ================================================================
      if (path === "/api/firms" && request.method === "GET") {
        const { results } = await env.DB.prepare(`
          SELECT f.id, f.name, f.city, f.state, f.lat, f.lng, f.ai_enabled, f.size_tier,
                 COUNT(c.id) as call_count,
                 COUNT(CASE WHEN c.outcome='Booked Consultation' THEN 1 END) as booked,
                 MAX(c.timestamp) as last_call
          FROM firms f
          LEFT JOIN calls c ON c.firm_id = f.id
          GROUP BY f.id
          ORDER BY f.name
        `).all();
        return json({ firms: results });
      }

      // ================================================================
      // GET /api/firms/:id - single firm detail
      // ================================================================
      const firmMatch = path.match(/^\/api\/firms\/(\d+)$/);
      if (firmMatch && request.method === "GET") {
        const id = parseInt(firmMatch[1]);
        const firm = await env.DB.prepare(
          "SELECT * FROM firms WHERE id = ?"
        ).bind(id).first();
        if (!firm) return err("Firm not found", 404);

        const { results: recentCalls } = await env.DB.prepare(`
          SELECT id, timestamp, lead_type, duration_seconds, ai_summary, outcome, caller_phone_masked
          FROM calls WHERE firm_id = ?
          ORDER BY timestamp DESC LIMIT 20
        `).bind(id).all();

        const stats = await env.DB.prepare(`
          SELECT COUNT(*) as total_calls,
                 COUNT(CASE WHEN outcome='Booked Consultation' THEN 1 END) as booked,
                 AVG(duration_seconds) as avg_duration
          FROM calls WHERE firm_id = ?
        `).bind(id).first();

        return json({ firm, recentCalls, stats });
      }

      // ================================================================
      // GET /api/calls - paginated call list
      // Query params: ?limit=50&offset=0&firm_id=5&lead_type=DUI&outcome=Booked%20Consultation
      // ================================================================
      if (path === "/api/calls" && request.method === "GET") {
        const limit = Math.min(parseInt(url.searchParams.get("limit") || "50"), 200);
        const offset = parseInt(url.searchParams.get("offset") || "0");
        const firmId = url.searchParams.get("firm_id");
        const leadType = url.searchParams.get("lead_type");
        const outcome = url.searchParams.get("outcome");

        let where = [];
        let binds = [];
        if (firmId) { where.push("c.firm_id = ?"); binds.push(parseInt(firmId)); }
        if (leadType) { where.push("c.lead_type = ?"); binds.push(leadType); }
        if (outcome) { where.push("c.outcome = ?"); binds.push(outcome); }
        const whereSQL = where.length ? `WHERE ${where.join(" AND ")}` : "";

        const { results } = await env.DB.prepare(`
          SELECT c.id, c.firm_id, f.name as firm_name, f.city, f.state,
                 c.timestamp, c.lead_type, c.duration_seconds,
                 c.ai_summary, c.outcome, c.caller_phone_masked
          FROM calls c
          JOIN firms f ON f.id = c.firm_id
          ${whereSQL}
          ORDER BY c.timestamp DESC
          LIMIT ? OFFSET ?
        `).bind(...binds, limit, offset).all();

        const countRow = await env.DB.prepare(
          `SELECT COUNT(*) as total FROM calls c ${whereSQL}`
        ).bind(...binds).first();

        return json({ calls: results, total: countRow.total, limit, offset });
      }

      // ================================================================
      // GET /api/stats - KPI + portfolio stats for dashboard
      // ================================================================
      if (path === "/api/stats" && request.method === "GET") {
        // KPIs
        const totalFirms = await env.DB.prepare("SELECT COUNT(*) as n FROM firms").first();
        const aiEnabledFirms = await env.DB.prepare(
          "SELECT COUNT(*) as n FROM firms WHERE ai_enabled = 1"
        ).first();
        const totalCalls30d = await env.DB.prepare(
          "SELECT COUNT(*) as n FROM calls WHERE timestamp >= datetime('now', '-30 days')"
        ).first();
        const bookedCalls30d = await env.DB.prepare(
          "SELECT COUNT(*) as n FROM calls WHERE outcome='Booked Consultation' AND timestamp >= datetime('now', '-30 days')"
        ).first();
        const avgDuration = await env.DB.prepare(
          "SELECT AVG(duration_seconds) as avg_dur FROM calls"
        ).first();

        // Firms that had activity in last 7 days
        const activeFirms = await env.DB.prepare(`
          SELECT COUNT(DISTINCT firm_id) as n FROM calls
          WHERE timestamp >= datetime('now', '-7 days')
        `).first();

        // Top firms by call volume
        const { results: topFirms } = await env.DB.prepare(`
          SELECT f.id, f.name, f.city, f.state, COUNT(c.id) as calls
          FROM firms f LEFT JOIN calls c ON c.firm_id = f.id
          GROUP BY f.id
          ORDER BY calls DESC
          LIMIT 20
        `).all();

        // Lead type distribution
        const { results: leadTypes } = await env.DB.prepare(`
          SELECT lead_type, COUNT(*) as count FROM calls
          GROUP BY lead_type ORDER BY count DESC
        `).all();

        // Daily volume (last 30 days)
        const { results: daily } = await env.DB.prepare(`
          SELECT DATE(timestamp) as day, COUNT(*) as calls,
                 COUNT(CASE WHEN outcome='Booked Consultation' THEN 1 END) as booked
          FROM calls
          WHERE timestamp >= datetime('now', '-30 days')
          GROUP BY day ORDER BY day ASC
        `).all();

        // Outcome breakdown
        const { results: outcomes } = await env.DB.prepare(`
          SELECT outcome, COUNT(*) as count FROM calls
          GROUP BY outcome ORDER BY count DESC
        `).all();

        // AI coverage
        const aiCovered = await env.DB.prepare(
          "SELECT COUNT(*) as n FROM calls WHERE ai_summary IS NOT NULL"
        ).first();
        const totalCallsForAI = await env.DB.prepare(
          "SELECT COUNT(*) as n FROM calls"
        ).first();
        const aiCoveragePct = totalCallsForAI.n > 0
          ? Math.round((aiCovered.n / totalCallsForAI.n) * 100)
          : 0;

        return json({
          kpis: {
            total_firms: totalFirms.n,
            ai_enabled_firms: aiEnabledFirms.n,
            active_firms_7d: activeFirms.n,
            total_calls_30d: totalCalls30d.n,
            booked_calls_30d: bookedCalls30d.n,
            conversion_rate: totalCalls30d.n > 0
              ? Math.round((bookedCalls30d.n / totalCalls30d.n) * 100)
              : 0,
            avg_duration_seconds: Math.round(avgDuration.avg_dur || 0),
            ai_coverage_pct: aiCoveragePct,
          },
          top_firms: topFirms,
          lead_types: leadTypes,
          daily: daily,
          outcomes: outcomes,
        });
      }

      // ================================================================
      // GET /api/health
      // ================================================================
      if (path === "/api/health") {
        return json({ status: "ok", service: "intakeiq-worker" });
      }

      // ================================================================
      // Default
      // ================================================================
      return json({
        service: "Intake IQ API",
        endpoints: [
          "GET /api/firms",
          "GET /api/firms/:id",
          "GET /api/calls",
          "GET /api/stats",
          "GET /api/health",
        ],
      });

    } catch (e) {
      return err(`Server error: ${e.message}`, 500);
    }
  },
};
