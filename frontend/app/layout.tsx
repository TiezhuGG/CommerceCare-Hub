import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "CommerceCare Hub",
  description: "Auditable ecommerce customer-service operations hub",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <header className="site-header">
          <a className="brand" href="/">CommerceCare Hub</a>
          <nav aria-label="演示导航">
            <a href="/">Customer Chat</a>
            <a href="/workspace">Agent Workspace</a>
            <a href="/approvals">Approvals</a>
            <a href="/tickets">Ticket Timeline</a>
            <a href="/trace">Trace &amp; Audit</a>
            <a href="/metrics">Metrics</a>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
