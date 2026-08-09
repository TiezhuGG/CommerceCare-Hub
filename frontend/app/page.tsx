"use client";

import { FormEvent, useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type WorkflowResult = { ticket_id: string; trace_id: string; workflow_status: string; customer_reply: string };
type ActionResult = { action_id: string; ticket_id: string; trace_id: string; status: string; approval_id: string | null };

export default function CustomerChatPage() {
  const [email, setEmail] = useState("customer1@demo.local");
  const [password, setPassword] = useState("demo-password-change-me");
  const [token, setToken] = useState("");
  const [conversationId, setConversationId] = useState("");
  const [message, setMessage] = useState("Order CC-1001 is delayed and late.");
  const [workflow, setWorkflow] = useState<WorkflowResult | null>(null);
  const [actionType, setActionType] = useState("refund");
  const [amountMinor, setAmountMinor] = useState("500");
  const [action, setAction] = useState<ActionResult | null>(null);
  const [error, setError] = useState("");

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${apiBaseUrl}/auth/token`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }),
    });
    if (!response.ok) return setError("登录失败，请检查本地演示账号。");
    setToken(((await response.json()) as { access_token: string }).access_token);
  }

  async function ensureConversation() {
    if (conversationId) return conversationId;
    const response = await fetch(`${apiBaseUrl}/conversations`, {
      method: "POST", headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": crypto.randomUUID() },
    });
    if (!response.ok) throw new Error("无法创建会话");
    const id = ((await response.json()) as { id: string }).id;
    setConversationId(id);
    return id;
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setWorkflow(null);
    if (!token) return setError("请先登录 Customer 演示账号。");
    try {
      const id = await ensureConversation();
      const response = await fetch(`${apiBaseUrl}/conversations/${id}/messages`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({ message, client_message_id: crypto.randomUUID() }),
      });
      if (!response.ok) throw new Error("咨询未能完成。");
      setWorkflow((await response.json()) as WorkflowResult);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "咨询未能完成。"); }
  }

  async function submitAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setAction(null);
    if (!token) return setError("请先登录 Customer 演示账号。");
    try {
      const id = await ensureConversation();
      const body: Record<string, unknown> = { action_type: actionType, order_number: "CC-1001", reason_code: "CUSTOMER_REQUEST" };
      if (actionType === "refund") body.amount_minor = Number(amountMinor);
      const response = await fetch(`${apiBaseUrl}/conversations/${id}/actions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error("售后请求未能提交。");
      setAction((await response.json()) as ActionResult);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "售后请求未能提交。"); }
  }

  return <main>
    <h1>Customer Chat</h1>
    <p className="lead">以受控工作流处理订单问题和售后请求。模型只分析，写操作始终经确定性规则、幂等与审批。</p>
    <div className="grid">
      <section className="card">
        <h2>1. Customer 登录</h2>
        <form onSubmit={login}><label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label><button type="submit">登录</button></form>
        {token ? <p className="success" data-testid="customer-authenticated">Customer identity ready</p> : null}
      </section>
      <section className="card">
        <h2>2. 订单与物流咨询</h2>
        <form onSubmit={sendMessage}><label>消息<textarea value={message} onChange={(event) => setMessage(event.target.value)} /></label><button type="submit" data-testid="send-message">发送咨询</button></form>
        {workflow ? <div className="success"><p>{workflow.customer_reply}</p><p className="muted">状态：{workflow.workflow_status} · Trace：{workflow.trace_id}</p></div> : null}
      </section>
      <section className="card card-wide">
        <h2>3. 受控售后请求</h2><p className="muted">退款默认进入主管审批；不会由自然语言模型自动执行。</p>
        <form onSubmit={submitAction}><label>动作<select value={actionType} onChange={(event) => setActionType(event.target.value)}><option value="refund">退款（需主管审批）</option><option value="return">退货</option><option value="damaged_item">商品破损</option></select></label>{actionType === "refund" ? <label>金额（分）<input value={amountMinor} onChange={(event) => setAmountMinor(event.target.value)} /></label> : null}<button type="submit">提交受控请求</button></form>
        {action ? <div className="success"><p>状态：<span className={`pill pill-${action.status}`}>{action.status}</span></p><p className="muted">工单：{action.ticket_id} · Trace：{action.trace_id}</p></div> : null}
      </section>
    </div>
    {error ? <p className="error" role="alert">{error}</p> : null}
  </main>;
}
