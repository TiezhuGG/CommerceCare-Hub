"use client";

import { FormEvent, useState } from "react";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type WorkflowReply = {
  customer_reply: string;
  trace_id: string;
  ticket_id: string;
};

export default function HomePage() {
  const [email, setEmail] = useState("customer1@demo.local");
  const [password, setPassword] = useState("demo-password-change-me");
  const [token, setToken] = useState("");
  const [conversationId, setConversationId] = useState("");
  const [message, setMessage] = useState("订单 CC-1001 为什么还没到？");
  const [reply, setReply] = useState<WorkflowReply | null>(null);
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

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      setError("请先登录 Customer 演示账号。");
      return;
    }
    setError("");
    let activeConversationId = conversationId;
    if (!activeConversationId) {
      const conversation = await fetch(`${apiBaseUrl}/conversations`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Idempotency-Key": crypto.randomUUID(),
        },
      });
      if (!conversation.ok) {
        setError("无法创建会话。");
        return;
      }
      const data = (await conversation.json()) as { id: string };
      activeConversationId = data.id;
      setConversationId(data.id);
    }
    const response = await fetch(`${apiBaseUrl}/conversations/${activeConversationId}/messages`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({ message, client_message_id: crypto.randomUUID() }),
    });
    if (!response.ok) {
      setError("查询失败，请确认 API 已启动且订单号属于当前客户。");
      return;
    }
    setReply((await response.json()) as WorkflowReply);
  }

  return (
    <main>
      <h1>CommerceCare Hub</h1>
      <p>Customer chat demo · Phase 2 order status and delivery delay</p>
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
      <form onSubmit={sendMessage}>
        <label>
          Message
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} />
        </label>
        <button type="submit">发送并查询</button>
      </form>
      {reply ? (
        <section aria-live="polite">
          <h2>回复</h2>
          <p>{reply.customer_reply}</p>
          <p>Trace ID: {reply.trace_id}</p>
          <p>Ticket ID: {reply.ticket_id}</p>
        </section>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
      <p><a href="/workspace">进入 Agent workspace</a></p>
    </main>
  );
}
