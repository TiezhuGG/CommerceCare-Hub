"use client";

import { useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
type Ticket = { id: string; state: string; reason_code: string; trace_id: string; created_at: string };
type TicketDetail = Ticket & { events: Array<{ event_type: string; from_state: string | null; to_state: string | null; created_at: string }> };

export default function AgentWorkspacePage() {
  const [token, setToken] = useState("");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selected, setSelected] = useState<TicketDetail | null>(null);
  const [error, setError] = useState("");

  async function loadWorkspace() {
    setError("");
    try {
      const login = await fetch(`${apiBaseUrl}/auth/token`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "operator@demo.local", password: "demo-password-change-me" }) });
      if (!login.ok) throw new Error("无法登录 Agent Operator 演示账号。");
      const accessToken = ((await login.json()) as { access_token: string }).access_token;
      setToken(accessToken);
      const response = await fetch(`${apiBaseUrl}/tickets`, { headers: { Authorization: `Bearer ${accessToken}` } });
      if (!response.ok) throw new Error("无法读取工单队列。");
      setTickets((await response.json()) as Ticket[]);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "无法读取工作台。"); }
  }

  async function openTicket(ticket: Ticket) {
    try {
      const response = await fetch(`${apiBaseUrl}/tickets/${ticket.id}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error("无法读取工单详情。");
      setSelected((await response.json()) as TicketDetail);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "无法读取工单详情。"); }
  }

  return <main>
    <h1>Agent Workspace</h1><p className="lead">运营人员查看受权限保护的工单与状态事件；此页面不展示客户原文、提示词或内部风险分。</p>
    <button onClick={() => void loadWorkspace()}>加载运营工作台</button>{error ? <p className="error" role="alert">{error}</p> : null}
    <div className="grid"><section className="card"><h2>工单队列</h2>{tickets.length ? <ul>{tickets.map((ticket) => <li key={ticket.id}><button onClick={() => void openTicket(ticket)}>{ticket.reason_code} · {ticket.state}</button><p className="muted">{ticket.id.slice(0, 8)} · {ticket.created_at}</p></li>)}</ul> : <p className="muted">加载后显示最多 100 条工单。</p>}</section>
    <section className="card"><h2>工单时间线</h2>{selected ? <><p>状态：<span className={`pill pill-${selected.state}`}>{selected.state}</span></p><p className="muted">Trace：{selected.trace_id}</p><ol className="timeline">{selected.events.map((event, index) => <li key={`${event.created_at}-${index}`}><strong>{event.event_type}</strong><br /><span className="muted">{event.from_state ?? "none"} → {event.to_state ?? "none"} · {event.created_at}</span></li>)}</ol></> : <p className="muted">选择左侧工单以查看状态事件。</p>}</section></div>
  </main>;
}
