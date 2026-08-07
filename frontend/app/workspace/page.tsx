"use client";

import { useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type Approval = { id: string; action_id: string; status: string; action_status: string };

export default function WorkspacePage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");

  async function loadApprovals() {
    setError("");
    const login = await fetch(`${apiBaseUrl}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "supervisor@demo.local", password: "demo-password-change-me" }),
    });
    if (!login.ok) {
      setError("无法登录 Supervisor 演示账号。");
      return;
    }
    const { access_token: accessToken } = (await login.json()) as { access_token: string };
    setToken(accessToken);
    const response = await fetch(`${apiBaseUrl}/approvals`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) {
      setError("无法读取审批队列。");
      return;
    }
    setApprovals((await response.json()) as Approval[]);
  }

  async function decide(approvalId: string, decision: "approve" | "reject") {
    const response = await fetch(`${apiBaseUrl}/approvals/${approvalId}/decision`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({ decision, reason_code: "SUPERVISOR_REVIEW" }),
    });
    if (!response.ok) {
      setError("该审批已过期或不可处理。");
      return;
    }
    await loadApprovals();
  }

  return (
    <main>
      <h1>Supervisor approval queue</h1>
      <p>仅展示必要的审批状态；客户敏感地址只以引用指纹保存，不会在队列中展示。</p>
      <button onClick={loadApprovals}>加载审批队列</button>
      {error ? <p role="alert">{error}</p> : null}
      <ul>
        {approvals.map((approval) => (
          <li key={approval.id}>
            <p>审批：{approval.status}；动作：{approval.action_status}</p>
            {approval.status === "pending" ? (
              <>
                <button onClick={() => decide(approval.id, "approve")}>批准</button>
                <button onClick={() => decide(approval.id, "reject")}>拒绝</button>
              </>
            ) : null}
          </li>
        ))}
      </ul>
      <p>管理员可调用 outbox dispatch，将已批准动作派发至 mock provider。</p>
      <a href="/">返回 Customer 售后页</a>
    </main>
  );
}
