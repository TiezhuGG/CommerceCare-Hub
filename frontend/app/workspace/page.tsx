"use client";

import { useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type Ticket = { id: string; state: string; reason_code: string; trace_id: string };

export default function WorkspacePage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState("");

  async function loadTickets() {
    setError("");
    const login = await fetch(`${apiBaseUrl}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "operator@demo.local", password: "demo-password-change-me" }),
    });
    if (!login.ok) {
      setError("无法登录 Operator 演示账号。");
      return;
    }
    const { access_token: token } = (await login.json()) as { access_token: string };
    const response = await fetch(`${apiBaseUrl}/tickets`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      setError("无法读取工单列表。");
      return;
    }
    setTickets((await response.json()) as Ticket[]);
  }

  return (
    <main>
      <h1>Agent workspace</h1>
      <button onClick={loadTickets}>加载近期工单</button>
      {error ? <p role="alert">{error}</p> : null}
      <ul>
        {tickets.map((ticket) => (
          <li key={ticket.id}>
            {ticket.state} · {ticket.reason_code} · {ticket.trace_id}
          </li>
        ))}
      </ul>
      <a href="/">返回 Customer chat</a>
    </main>
  );
}
