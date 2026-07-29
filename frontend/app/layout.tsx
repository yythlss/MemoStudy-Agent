import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MemoStudy Agent",
  description: "个人知识管理与学习 Agent",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
