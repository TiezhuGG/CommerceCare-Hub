"use client";

import { useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
type Ticket = { id: string; state: string; reason_code: string; trace_id: string };
type Detail = Ticket & { events: Array<{ event_type: string; from_state: string | null; to_state: string | null; created_at: string }> };

export default function TicketTimelinePage() {
  const [token, setToken] = useState(""); const [tickets, setTickets] = useState<Ticket[]>([]); const [detail, setDetail] = useState<Detail | null>(null); const [error, setError] = useState("");
  async function loadTickets() { try { const login = await fetch(`${apiBaseUrl}/auth/token`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "supervisor@demo.local", password: "demo-password-change-me" }) }); const accessToken = ((await login.json()) as { access_token: string }).access_token; setToken(accessToken); const response = await fetch(`${apiBaseUrl}/tickets`, { headers: { Authorization: `Bearer ${accessToken}` } }); if (!response.ok) throw new Error("无法读取工单。"); setTickets((await response.json()) as Ticket[]); } catch (reason) { setError(reason instanceof Error ? reason.message : "无法读取工单。"); } }
  async function inspect(ticket: Ticket) { const response = await fetch(`${apiBaseUrl}/tickets/${ticket.id}`, { headers: { Authorization: `Bearer ${token}` } }); if (!response.ok) return setError("无法读取时间线。"); setDetail((await response.json()) as Detail); }
  return <main><h1>Ticket Timeline</h1><p className="lead">独立的只读状态时间线，用于展示每一次领域状态迁移的可追溯性。</p><button onClick={() => void loadTickets()}>加载工单</button>{error ? <p className="error" role="alert">{error}</p> : null}<div className="grid"><section className="card"><h2>选择工单</h2>{tickets.map((ticket) => <button key={ticket.id} onClick={() => void inspect(ticket)}>{ticket.reason_code} · {ticket.state}</button>)}</section><section className="card"><h2>状态转移</h2>{detail ? <ol className="timeline">{detail.events.map((event, index) => <li key={`${index}-${event.created_at}`}><strong>{event.from_state ?? "none"} → {event.to_state ?? "none"}</strong><br /><span className="muted">{event.event_type} · {event.created_at}</span></li>)}</ol> : <p className="muted">选择工单后显示事件。</p>}</section></div></main>;
}
