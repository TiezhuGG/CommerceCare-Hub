"use client";

import { useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type Dashboard = {
  workflow_counts: Record<string, number>;
  action_counts: Record<string, number>;
  outbox_retry_count: number;
  audit_event_count: number;
  agent_latency_avg_ms: number;
  evaluation: { status: string; suite_version: string | null; summary: Record<string, unknown> };
  slo_status: string;
};

export default function MetricsPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function authenticate() {
    const response = await fetch(`${apiBaseUrl}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "admin@demo.local", password: "demo-password-change-me" }),
    });
    if (!response.ok) throw new Error("无法登录 Admin 演示账号。");
    const data = (await response.json()) as { access_token: string };
    setToken(data.access_token);
    return data.access_token;
  }

  async function loadDashboard(existingToken?: string) {
    setError("");
    try {
      const activeToken = existingToken ?? (token || (await authenticate()));
      const response = await fetch(`${apiBaseUrl}/metrics/dashboard`, {
        headers: { Authorization: `Bearer ${activeToken}` },
      });
      if (!response.ok) throw new Error("无法读取指标。请先加载演示数据。");
      setDashboard((await response.json()) as Dashboard);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "无法读取指标。");
    }
  }

  async function runEvaluation() {
    setLoading(true);
    setError("");
    try {
      const activeToken = token || (await authenticate());
      const response = await fetch(`${apiBaseUrl}/admin/evaluations/run`, {
        method: "POST",
        headers: { Authorization: `Bearer ${activeToken}`, "Idempotency-Key": crypto.randomUUID() },
      });
      if (!response.ok) throw new Error("评估未能完成。");
      await loadDashboard(activeToken);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "评估未能完成。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Reliability metrics</h1>
      <p>仅展示聚合指标与评估结果；不显示客户原文、提示词或内部推理。</p>
      <button onClick={() => void loadDashboard()}>加载指标</button>
      <button onClick={() => void runEvaluation()} disabled={loading}>
        {loading ? "正在运行评估…" : "运行 100 条合成评估"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
      {dashboard ? (
        <section aria-live="polite">
          <h2>SLO：{dashboard.slo_status}</h2>
          <p>Agent 平均延迟：{dashboard.agent_latency_avg_ms} ms</p>
          <p>Outbox 重试：{dashboard.outbox_retry_count}；审计事件：{dashboard.audit_event_count}</p>
          <h3>工作流</h3>
          <pre>{JSON.stringify(dashboard.workflow_counts, null, 2)}</pre>
          <h3>售后动作</h3>
          <pre>{JSON.stringify(dashboard.action_counts, null, 2)}</pre>
          <h3>最近评估：{dashboard.evaluation.status}</h3>
          <p>Suite：{dashboard.evaluation.suite_version ?? "尚未运行"}</p>
          <pre>{JSON.stringify(dashboard.evaluation.summary, null, 2)}</pre>
        </section>
      ) : null}
      <p><a href="/">返回 Customer 售后页</a></p>
    </main>
  );
}
