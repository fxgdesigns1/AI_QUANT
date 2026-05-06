import { NextRequest, NextResponse } from "next/server";
import { UPSTREAM_BASE, UPSTREAM_TOKEN } from "@/lib/api/upstream";
import { safeJsonFetch } from "@/lib/api/safeFetch";
import { heartbeatAgeSec } from "@/lib/bridgeHeartbeat";

const TOP3_STALE_MS = 900000;

/** Aggregator needs longer timeout than default upstream (parallel VM calls). */
async function fetchUpstreamAgg(path: string): Promise<{
  data: any;
  error: string | null;
  status: number;
  state: "ok" | "degraded" | "unknown" | "unreachable" | "timeout";
}> {
  if (!UPSTREAM_BASE) {
    return {
      data: null,
      error: "upstream_base_unconfigured:set_UPSTREAM_API_BASE_URL",
      status: 503,
      state: "unreachable",
    };
  }
  const url = `${UPSTREAM_BASE}${path}`;
  const res = await safeJsonFetch(
    url,
    {
      headers: {
        Authorization: `Bearer ${UPSTREAM_TOKEN}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
      timeoutMs: 20000,
    },
    null,
  );
  if (!res.ok) {
    return { data: null, error: res.error || res.state, status: res.status, state: res.state };
  }
  return { data: res.data, error: null, status: res.status, state: "ok" };
}

function unwrapUpstreamBody(res: {
  data: any;
  error: string | null;
}): { payload: any; error: string | null } {
  if (res.error) return { payload: null, error: res.error };
  const body = res.data;
  if (body == null) return { payload: null, error: "empty_body" };
  if (typeof body === "object" && body !== null && "data" in body && (body as any).data !== undefined) {
    return { payload: (body as any).data, error: null };
  }
  return { payload: body, error: null };
}

function formatAge(sec: number | null | undefined): string {
  if (sec == null || Number.isNaN(Number(sec))) return "unknown";
  const s = Math.max(0, Math.floor(Number(sec)));
  if (s < 120) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 120) return `${m}m`;
  const h = Math.floor(m / 60);
  return `${h}h+`;
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const base = `${url.protocol}//${url.host}`;

  const [
    mt5Fetch,
    preRes,
    runRes,
    top3Res,
    bridgeRes,
    newsRes,
    probsRes,
  ] = await Promise.all([
    fetch(`${base}/api/mt5`, { cache: "no-store" }).then(async (r) => ({
      ok: r.ok,
      json: await r.json().catch(() => null),
    })),
    fetchUpstreamAgg("/api/mt5/preflight"),
    fetchUpstreamAgg("/api/runtime/status"),
    fetchUpstreamAgg("/api/top3/opportunities"),
    fetchUpstreamAgg("/api/bridge/status"),
    fetchUpstreamAgg("/api/news/provider_status"),
    fetchUpstreamAgg("/api/observability/problems"),
  ]);

  const mt5 = mt5Fetch.json;
  const mt5Health = mt5?.health;
  const mt5Truth = mt5?.mt5_truth;
  const bridgeEst = mt5?.bridge_estates;

  const serviceUp = Boolean(mt5Health?.service_up);
  const terminalOk = Boolean(mt5Health?.terminal_connected);
  const accountOk = Boolean(mt5Health?.account_connected);
  const mt5PathHealthy = serviceUp && terminalOk && accountOk;

  const { payload: pf, error: pfErr } = unwrapUpstreamBody(preRes);
  const { payload: rt, error: rtErr } = unwrapUpstreamBody(runRes);
  const { payload: t3, error: t3Err } = unwrapUpstreamBody(top3Res);
  const { payload: bridgeRaw } = unwrapUpstreamBody(bridgeRes);

  const preflightStatus = String(pf?.preflight_status ?? pf?.status ?? "UNKNOWN").toUpperCase();
  const preflightPass = preflightStatus === "PASS";

  const mode = rt?.mode != null ? String(rt.mode) : "unknown";
  const marketClosed = Boolean(rt?.weekend_indicator ?? rt?.market_closed);
  const noTradeReason = rt?.no_trade_reason != null ? String(rt.no_trade_reason) : null;

  const accounts = Array.isArray(rt?.accounts) ? rt.accounts : [];
  const lane010 = accounts.find((a: any) => String(a?.id_masked || "").includes("010"));
  const lane011 = accounts.find((a: any) => String(a?.id_masked || "").includes("011"));
  const lane010Mode =
    lane010?.execution_mode != null
      ? String(lane010.execution_mode)
      : "manual_only";
  const lane011Mode =
    lane011?.execution_mode != null
      ? String(lane011.execution_mode)
      : "automated";

  const freshnessMsRaw = t3?.freshness_ms;
  let freshnessMs: number | null = null;
  if (freshnessMsRaw != null && !Number.isNaN(Number(freshnessMsRaw))) {
    freshnessMs = Number(freshnessMsRaw);
  }
  let freshnessState = String(t3?.freshness_state ?? "").toUpperCase();
  if (!freshnessState || freshnessState === "UNKNOWN") {
    if (t3Err) {
      freshnessState = "UNKNOWN";
    } else if (freshnessMs == null) {
      freshnessState = "UNKNOWN";
    } else if (freshnessMs > TOP3_STALE_MS) {
      freshnessState = "STALE";
    } else {
      freshnessState = "FRESH";
    }
  }
  const freshnessAgeSec =
    t3?.freshness_age_seconds != null
      ? Number(t3.freshness_age_seconds)
      : freshnessMs != null
        ? Math.floor(freshnessMs / 1000)
        : null;
  const opportunities = Array.isArray(t3?.opportunities) ? t3.opportunities : [];
  const rawCandidates = Number(
    t3?.raw_top_candidates_count ?? (opportunities.length > 0 ? opportunities.length : 0),
  );
  const scanRecordStatus = t3?.scan_record_status != null ? String(t3.scan_record_status) : null;
  const embargoActive = Boolean(t3?.embargo_active);
  const embargoState =
    t3?.embargo_state != null
      ? String(t3.embargo_state)
      : embargoActive
        ? "ACTIVE"
        : "CLEAR";
  const verificationOverall = String(t3?.verification?.overall_status ?? "UNKNOWN");

  const bridgeRunning = typeof bridgeRaw?.running === "boolean" ? bridgeRaw.running : null;
  const hbAge = heartbeatAgeSec(bridgeRaw?.last_heartbeat);
  let bridgeLogSecondaryWarning: string | null = null;
  if (mt5PathHealthy && bridgeRunning === false) {
    bridgeLogSecondaryWarning =
      "Legacy producer / bridge heartbeat idle or service_down; MT5 sidecar telemetry shows terminal+account connected.";
  } else if (mt5PathHealthy && hbAge != null && hbAge > 600) {
    bridgeLogSecondaryWarning = `Consumer bridge log heartbeat age ~${formatAge(hbAge)} (non-primary; MT5 path healthy).`;
  }

  const newsData = newsRes.data || {};
  const probsData = (probsRes.data as any)?.data || probsRes.data || {};
  const providerMap = (newsData as any)?.providers || {};
  const providerNames = Object.keys(providerMap);
  const providersHealthy = providerNames.filter((name) => {
    const p = providerMap[name];
    return p?.status === "configured";
  }).length;
  const providersDisplay =
    providerNames.length > 0 ? `${providersHealthy} / ${providerNames.length}` : "unknown";

  const topBlocker = probsData?.top_blocker || null;

  const reasons: string[] = [];
  if (!mt5Fetch.ok || !mt5) {
    reasons.push("dashboard /api/mt5 unavailable or invalid");
  } else if (!mt5PathHealthy) {
    reasons.push(
      mt5Truth?.failure_bucket
        ? `MT5 path: ${mt5Truth.failure_bucket}`
        : "MT5 sidecar health: service/terminal/account not all OK",
    );
  }
  if (pfErr) reasons.push(`preflight fetch: ${pfErr}`);
  else if (!preflightPass) {
    reasons.push(
      `preflight ${preflightStatus}${pf?.blocking_reason ? ` (${pf.blocking_reason})` : ""}`,
    );
  }
  if (rtErr) reasons.push(`runtime fetch: ${rtErr}`);
  if (t3Err) reasons.push(`top3 fetch: ${t3Err}`);

  let overall: "DEGRADED" | "NO_TRADE" | "WAIT" | "READY" = "READY";
  if (!mt5PathHealthy || pfErr || !preflightPass || rtErr || t3Err) {
    overall = "DEGRADED";
  } else if (marketClosed) {
    overall = "NO_TRADE";
    reasons.push("market closed (runtime)");
  } else if (freshnessState === "STALE" || (freshnessState === "UNKNOWN" && !t3Err)) {
    overall = "NO_TRADE";
    reasons.push(`top3 freshness: ${freshnessState}`);
  } else if (rawCandidates === 0 || opportunities.length === 0) {
    overall = "NO_TRADE";
    reasons.push(
      scanRecordStatus === "no_trade" || scanRecordStatus === "NO_TRADE"
        ? "scan_record_status indicates no trade"
        : "no top3 opportunities / zero raw candidates",
    );
  } else if (embargoState && embargoState !== "CLEAR" && embargoState !== "unknown") {
    overall = "WAIT";
    reasons.push(`embargo: ${embargoState}`);
  } else if (verificationOverall && verificationOverall !== "PASS" && verificationOverall !== "UNKNOWN") {
    overall = "WAIT";
    reasons.push(`top3 verification: ${verificationOverall}`);
  }

  const bannerReason =
    reasons.length > 0
      ? reasons.join(" · ")
      : overall === "READY"
        ? "MT5 path healthy; preflight PASS; fresh top3 with candidates (paper-only gates still apply)."
        : "No blocking reasons surfaced.";

  const ui_status = {
    overall,
    banner_reason: bannerReason,
    mode_display: mode !== "unknown" ? mode : rtErr ? "unknown (runtime unreachable)" : "unknown",
    paper_safe_label: "PAPER ONLY",
    mt5_bridge_status: mt5PathHealthy ? "UP" : "DOWN",
    mt5_bridge_secondary_warning: bridgeLogSecondaryWarning,
    latest_scan_age: formatAge(freshnessAgeSec),
    providers_ok_display: providersDisplay,
    providers_top_blocker: topBlocker,
    lane_010_label: `010: ${lane010Mode.toUpperCase()}`,
    lane_011_label: `011: ${lane011Mode.toUpperCase()}`,
    execution_consumer: bridgeEst?.execution_consumer ?? null,
    target_kind: bridgeEst?.target_kind ?? null,
    resolved_sidecar: bridgeEst?.resolved_sidecar_base_url ?? null,
    top3_freshness_state: freshnessState,
    raw_top_candidates_count: rawCandidates,
    opportunity_count: opportunities.length,
    scan_record_status: scanRecordStatus,
    embargo_state: embargoState,
    verification_overall: verificationOverall,
    market_closed: marketClosed,
    no_trade_reason: noTradeReason,
  };

  const hb = pf?.consumer_runtime_status?.windows_consumer_heartbeat ?? null;
  const windowsConsumerHeartbeatSummary = hb
    ? {
        present: Boolean(hb.present),
        ok: Boolean(hb.ok),
        fresh: Boolean(hb.fresh),
        ts_utc: hb.ts_utc ?? null,
        age_seconds: hb.age_seconds ?? null,
        latest_signal_id_seen: hb.latest_signal_id_seen ?? null,
        latest_signal_id_executed_ok: hb.latest_signal_id_executed_ok ?? null,
        latest_signal_id_failed: hb.latest_signal_id_failed ?? null,
        validation_ok_count: hb.validation_ok_count ?? null,
        terminal_rejects_count: hb.terminal_rejects_count ?? null,
        lock_dedupe_hits_count: hb.lock_dedupe_hits_count ?? null,
        execution_enabled: hb.execution_enabled ?? null,
        kill_switch_enabled: hb.kill_switch_enabled ?? null,
        last_result_code: hb.last_result_code ?? null,
      }
    : null;

  return NextResponse.json({
    ts_utc: new Date().toISOString(),
    mt5_truth: mt5Truth,
    bridge_estates: bridgeEst,
    mt5_health: mt5Health,
    preflight_truth: pf,
    preflight_error: pfErr,
    windows_consumer_heartbeat_summary: windowsConsumerHeartbeatSummary,
    runtime_truth: rt,
    runtime_error: rtErr,
    top3_truth: t3,
    top3_error: t3Err,
    bridge_upstream: bridgeRaw,
    diagnostics: {
      providers_ok_display: providersDisplay,
      provider_names: providerNames,
      top_blocker: topBlocker,
    },
    ui_status,
    opportunity_preview: opportunities.slice(0, 5),
  });
}
