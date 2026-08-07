"use client";

import { FormEvent, useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type ActionResult = {
  action_id: string;
  ticket_id: string;
  trace_id: string;
  status: string;
  approval_id: string | null;
};

export default function HomePage() {
  const [email, setEmail] = useState("customer1@demo.local");
  const [password, setPassword] = useState("demo-password-change-me");
  const [token, setToken] = useState("");
  const [conversationId, setConversationId] = useState("");
  const [actionType, setActionType] = useState("damaged_item");
  const [orderNumber, setOrderNumber] = useState("CC-1001");
  const [amountMinor, setAmountMinor] = useState("500");
  const [addressReference, setAddressReference] = useState("ADDR-CHANGE-REFERENCE");
  const [result, setResult] = useState<ActionResult | null>(null);
  const [error, setError] = useState("");

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${apiBaseUrl}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      setError("登录失败，请检查本地演示账号。");
      return;
    }
    const data = (await response.json()) as { access_token: string };
    setToken(data.access_token);
  }

  async function ensureConversation() {
    if (conversationId) return conversationId;
    const response = await fetch(`${apiBaseUrl}/conversations`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Idempotency-Key": crypto.randomUUID() },
    });
    if (!response.ok) throw new Error("无法创建会话");
    const data = (await response.json()) as { id: string };
    setConversationId(data.id);
    return data.id;
  }

  async function submitAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    if (!token) {
      setError("请先使用 Customer 演示账号登录。");
      return;
    }
    try {
      const activeConversationId = await ensureConversation();
      const body: Record<string, unknown> = {
        action_type: actionType,
        order_number: orderNumber,
        reason_code: "CUSTOMER_REQUEST",
      };
      if (actionType === "refund") body.amount_minor = Number(amountMinor);
      if (actionType === "address_update") body.address_reference = addressReference;
      const response = await fetch(`${apiBaseUrl}/conversations/${activeConversationId}/actions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        const detail = (await response.json()) as { message?: string };
        setError(detail.message ?? "售后请求未能提交。");
        return;
      }
      setResult((await response.json()) as ActionResult);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "售后请求未能提交。");
    }
  }

  return (
    <main>
      <h1>CommerceCare Hub</h1>
      <p>可审计的电商售后服务演示：所有写入均经过规则、幂等与可追溯工作流。</p>
      <form onSubmit={login}>
        <label>
          Email
          <input value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        <button type="submit">登录 Customer</button>
      </form>

      <section>
        <h2>提交售后请求</h2>
        <form onSubmit={submitAction}>
          <label>
            类型
            <select value={actionType} onChange={(event) => setActionType(event.target.value)}>
              <option value="damaged_item">商品破损（自动创建承运商工单）</option>
              <option value="refund">退款（需主管审批）</option>
              <option value="return">退货（仅已签收订单）</option>
              <option value="address_update">修改地址（需主管审批）</option>
            </select>
          </label>
          <label>
            订单号
            <input value={orderNumber} onChange={(event) => setOrderNumber(event.target.value)} />
          </label>
          {actionType === "refund" ? (
            <label>
              退款金额（分）
              <input value={amountMinor} onChange={(event) => setAmountMinor(event.target.value)} />
            </label>
          ) : null}
          {actionType === "address_update" ? (
            <label>
              新地址引用
              <input value={addressReference} onChange={(event) => setAddressReference(event.target.value)} />
            </label>
          ) : null}
          <button type="submit">提交请求</button>
        </form>
      </section>
      {result ? (
        <section aria-live="polite">
          <h2>请求已记录</h2>
          <p>状态：{result.status}</p>
          <p>Trace ID: {result.trace_id}</p>
          {result.approval_id ? <p>审批编号：{result.approval_id}</p> : <p>已安全派发到 mock provider。</p>}
        </section>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
      <p><a href="/workspace">打开主管审批队列</a></p>
    </main>
  );
}
