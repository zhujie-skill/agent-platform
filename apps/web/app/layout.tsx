import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Agent Tool Platform", template: "%s · Agent Tool Platform" },
  description: "Control Plane for reusable Agents and Tools",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <header className="site-header">
          <Link className="brand" href="/">
            <span className="brand-mark">AT</span><span>Agent Tool Platform</span>
          </Link>
          <nav aria-label="主导航">
            <Link href="/">Overview</Link><Link href="/agents">Agents</Link>
            <Link href="/tools">Tools</Link><Link href="/mcp">MCP</Link>
            <Link href="/executions">Executions</Link><Link href="/policies">Policies</Link>
            <Link href="/audit">Audit</Link>
          </nav>
          <a className="api-link" href="http://127.0.0.1:8000/docs">API Docs →</a>
        </header>
        {children}
      </body>
    </html>
  );
}
