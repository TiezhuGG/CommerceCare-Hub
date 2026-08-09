"use client";

import { useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
type Approval = { id: string; action_id: string; status: string; action_status: string };

export default function SupervisorApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  async function loadApprovals() {
    setError("");
    try {
      const login = await fetch(`${apiBaseUrl}/auth/token`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: "supervisor@demo.local", password: "demo-password-change-me" }) });
      if (!login.ok) throw new Error("无法登录 Supervisor 演示账号。");
      const accessToken = ((await login.json()) as { access_token: string }).access_token;
      setToken(accessToken);
      const response = await fetch(`${apiBaseUrl}/approvals`, { headers: { Authorization: `Bearer ${accessToken}` } });
      if (!response.ok) throw new Error("无法读取审批队列。");
      setApprovals((await response.json()) as Approval[]);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "无法读取审批队列。"); }
  }
  async function decide(id: string, decision: "approve" | "reject") {
    const response = await fetch(`${apiBaseUrl}/approvals/${id}/decision`, { method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ decision, reason_code: "SUPERVISOR_REVIEW" }) });
    if (!response.ok) return setError("该审批已过期或不可处理。");
    await loadApprovals();
  }
  return <main><h1>Supervisor Approvals</h1><p className="lead">高风险请求只有在主管明确批准后才会进入 durable outbox；地址只保留指纹引用。</p><button onClick={() => void loadApprovals()}>加载审批队列</button>{error ? <p className="error" role="alert">{error}</p> : null}<section className="card"><h2>待处理请求</h2>{approvals.length ? <ul>{approvals.map((approval) => <li key={approval.id}><p><span className={`pill pill-${approval.status}`}>{approval.status}</span> · 动作：{approval.action_status}</p>{approval.status === "pending" ? <><button onClick={() => void decide(approval.id, "approve")}>批准</button> <button onClick={() => void decide(approval.id, "reject")}>拒绝</button></> : null}</li>)}</ul> : <p className="muted">暂无审批，先在 Customer Chat 提交退款请求。</p>}</section></main>;
}
