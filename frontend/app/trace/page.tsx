"use client";

import { FormEvent, useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
type Trace = { status: string; final_result_code: string | null; agents: string[]; tools: string[]; evidence: string[]; state_transitions: string[] };
type Audit = { event_type: string; resource_type: string; resource_id: string; occurred_at: string };

export default function TraceAuditPage() {
  const [token, setToken] = useState(""); const [traceId, setTraceId] = useState(""); const [trace, setTrace] = useState<Trace | null>(null); const [audit, setAudit] = useState<Audit[]>([]); const [error, setError] = useState("");
  async function loginAdmin() { const login = await fetch(`${apiBaseUrl}/auth/token`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "admin@demo.local", password: "demo-password-change-me" }) }); if (!login.ok) throw new Error("无法登录 Admin。"); const accessToken = ((await login.json()) as { access_token: string }).access_token; setToken(accessToken); return accessToken; }
  async function loadAudit() { try { const active = token || await loginAdmin(); const response = await fetch(`${apiBaseUrl}/audit-logs`, { headers: { Authorization: `Bearer ${active}` } }); if (!response.ok) throw new Error("无法读取审计日志。"); setAudit((await response.json()) as Audit[]); } catch (reason) { setError(reason instanceof Error ? reason.message : "无法读取审计日志。"); } }
  async function loadTrace(event: FormEvent<HTMLFormElement>) { event.preventDefault(); try { const active = token || await loginAdmin(); const response = await fetch(`${apiBaseUrl}/workflow-runs/${traceId}`, { headers: { Authorization: `Bearer ${active}` } }); if (!response.ok) throw new Error("未找到该 trace，或当前身份无权读取。"); setTrace((await response.json()) as Trace); } catch (reason) { setError(reason instanceof Error ? reason.message : "无法读取 trace。"); } }
  return <main><h1>Trace &amp; Audit</h1><p className="lead">只显示结构化运行摘要：Agent、工具、证据和状态迁移；不展示原始提示词或私有推理。</p><div className="grid"><section className="card"><h2>读取 Trace</h2><form onSubmit={loadTrace}><label>Trace ID<input value={traceId} onChange={(event) => setTraceId(event.target.value)} placeholder="从 Customer Chat 或 Ticket Timeline 复制" /></label><button type="submit">查询 Trace</button></form>{trace ? <pre>{JSON.stringify(trace, null, 2)}</pre> : null}</section><section className="card"><h2>最近审计</h2><button onClick={() => void loadAudit()}>加载审计摘要</button><ul>{audit.map((entry) => <li key={`${entry.event_type}-${entry.occurred_at}`}><strong>{entry.event_type}</strong><br /><span className="muted">{entry.resource_type} · {entry.occurred_at}</span></li>)}</ul></section></div>{error ? <p className="error" role="alert">{error}</p> : null}</main>;
}
