"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";

type View = "dashboard" | "library" | "chat" | "study" | "reports";
type Collection = { id: string; name: string; description: string; source_count: number };
type Source = { id: string; title: string; source_type: string; summary: string; created_at: string };
type Task = { id: string; title: string; completed: number };
type Goal = { id: string; title: string; description: string; progress: number; tasks: Task[] };
type Report = { id: string; title: string; topic: string; content: string; created_at: string };
type Dashboard = {
  counts: { collections: number; sources: number; notes: number; reports: number };
  recent_sources: Source[];
  today_tasks: (Task & { goal_title: string })[];
};
type Citation = { source_id: string; title: string; excerpt: string; score: number };

const nav: { id: View; label: string; icon: string }[] = [
  { id: "dashboard", label: "工作台", icon: "⌂" },
  { id: "library", label: "资料库", icon: "▤" },
  { id: "chat", label: "AI 研究", icon: "✦" },
  { id: "study", label: "学习中心", icon: "◫" },
  { id: "reports", label: "报告工作室", icon: "▧" },
];

const emptyDashboard: Dashboard = {
  counts: { collections: 0, sources: 0, notes: 0, reports: 0 },
  recent_sources: [],
  today_tasks: [],
};

function formatDate(value?: string) {
  if (!value) return "刚刚";
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(new Date(value));
}

export default function Home() {
  const [view, setView] = useState<View>("dashboard");
  const [dashboard, setDashboard] = useState<Dashboard>(emptyDashboard);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const loadAll = useCallback(async () => {
    try {
      const [dashboardData, collectionData, sourceData, goalData, reportData] = await Promise.all([
        api<Dashboard>("/dashboard"),
        api<Collection[]>("/collections"),
        api<Source[]>("/sources"),
        api<Goal[]>("/learning/goals"),
        api<Report[]>("/reports"),
      ]);
      setDashboard(dashboardData);
      setCollections(collectionData);
      setSources(sourceData);
      setGoals(goalData);
      setReports(reportData);
      setError("");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "无法连接后端服务");
    }
  }, []);

  useEffect(() => { void loadAll(); }, [loadAll]);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await loadAll();
      setToast(success);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "操作失败");
    } finally {
      setBusy(false);
    }
  };

  const title = nav.find((item) => item.id === view)?.label ?? "工作台";

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">M</span><span>MemoStudy <b>Agent</b></span></div>
        <div className="workspace"><span>个人工作空间</span><b>⌄</b></div>
        <nav>
          {nav.map((item) => (
            <button key={item.id} className={view === item.id ? "nav-item active" : "nav-item"} onClick={() => setView(item.id)}>
              <span>{item.icon}</span>{item.label}
              {item.id === "library" && dashboard.counts.sources > 0 ? <em>{dashboard.counts.sources}</em> : null}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="model-status"><i /> 本地知识库已连接</div>
          <button className="user-card"><span>研</span><div><b>研究者</b><small>单用户版本</small></div><strong>•••</strong></button>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div><p>个人知识管理与学习 Agent</p><h1>{title}</h1></div>
          <div className="top-actions"><button className="icon-button" onClick={() => void loadAll()}>↻</button><button className="primary" onClick={() => setView("library")}>＋ 添加资料</button></div>
        </header>

        {error ? <div className="error-banner">{error}<button onClick={() => setError("")}>×</button></div> : null}
        {view === "dashboard" && <DashboardView data={dashboard} onNavigate={setView} />}
        {view === "library" && <LibraryView collections={collections} sources={sources} busy={busy} run={run} />}
        {view === "chat" && <ChatView collections={collections} busy={busy} setBusy={setBusy} setError={setError} />}
        {view === "study" && <StudyView goals={goals} busy={busy} run={run} />}
        {view === "reports" && <ReportsView collections={collections} reports={reports} busy={busy} run={run} />}
      </section>
      {toast ? <div className="toast">✓ {toast}</div> : null}
    </main>
  );
}

function DashboardView({ data, onNavigate }: { data: Dashboard; onNavigate: (view: View) => void }) {
  const cards = [
    ["知识库", data.counts.collections, "个专题", "violet"],
    ["已整理资料", data.counts.sources, "份内容", "blue"],
    ["知识笔记", data.counts.notes, "张卡片", "amber"],
    ["研究报告", data.counts.reports, "份输出", "green"],
  ];
  return (
    <div className="content dashboard-view">
      <section className="hero">
        <div><span className="eyebrow">早上好，研究者</span><h2>今天想深入研究什么？</h2><p>让资料沉淀为知识，让每一次学习都有结果。</p></div>
        <button onClick={() => onNavigate("chat")}><span>✦</span> 开始 AI 研究 <b>→</b></button>
      </section>
      <section className="stat-grid">
        {cards.map(([label, number, unit, color]) => <article className={`stat-card ${color}`} key={label}><div className="stat-icon">{label === "知识库" ? "▤" : label === "已整理资料" ? "◧" : label === "知识笔记" ? "◇" : "▧"}</div><p>{label}</p><h3>{number}<small>{unit}</small></h3></article>)}
      </section>
      <section className="two-column">
        <article className="panel">
          <div className="panel-head"><div><h3>最近资料</h3><p>继续阅读和整理你的知识</p></div><button onClick={() => onNavigate("library")}>查看全部 →</button></div>
          <div className="source-list">
            {data.recent_sources.length ? data.recent_sources.map((source) => <div className="source-row" key={source.id}><span className={`file-icon ${source.source_type}`}>{source.source_type === "pdf" ? "PDF" : "TXT"}</span><div><b>{source.title}</b><p>{source.summary || "等待生成摘要"}</p></div><time>{formatDate(source.created_at)}</time></div>) : <Empty icon="▤" title="还没有资料" text="添加第一份资料，开始建立个人知识库。" />}
          </div>
        </article>
        <article className="panel">
          <div className="panel-head"><div><h3>今日学习</h3><p>从一个小任务开始</p></div><button onClick={() => onNavigate("study")}>学习中心 →</button></div>
          <div className="task-list">
            {data.today_tasks.length ? data.today_tasks.map((task, index) => <div className="task-row" key={task.id}><span>{index + 1}</span><div><b>{task.title}</b><p>{task.goal_title}</p></div></div>) : <Empty icon="◫" title="暂无学习任务" text="创建一个学习目标，系统会生成执行路径。" />}
          </div>
        </article>
      </section>
      <section className="quick-grid">
        <button onClick={() => onNavigate("chat")}><span>✦</span><div><b>知识库问答</b><small>基于资料获得带引用的回答</small></div><em>→</em></button>
        <button onClick={() => onNavigate("study")}><span>◫</span><div><b>生成学习复盘</b><small>总结进度并规划下一步</small></div><em>→</em></button>
        <button onClick={() => onNavigate("reports")}><span>▧</span><div><b>创建研究报告</b><small>从资料到结构化研究成果</small></div><em>→</em></button>
      </section>
    </div>
  );
}

function LibraryView({ collections, sources, busy, run }: { collections: Collection[]; sources: Source[]; busy: boolean; run: (action: () => Promise<void>, success: string) => Promise<void> }) {
  const [collectionId, setCollectionId] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [newCollection, setNewCollection] = useState("");
  const folderInputRef = useRef<HTMLInputElement>(null);
  const selected = collectionId || collections[0]?.id || "";

  useEffect(() => {
    folderInputRef.current?.setAttribute("webkitdirectory", "");
    folderInputRef.current?.setAttribute("directory", "");
  }, []);

  async function addText(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      await api("/sources", { method: "POST", body: JSON.stringify({ collection_id: selected, title, source_type: "text", content }) });
      setTitle(""); setContent("");
    }, "资料已加入知识库");
  }
  async function uploadFiles(fileList: FileList | null) {
    if (!fileList || !selected) return;
    const supported = new Set(["pdf", "txt", "md", "markdown", "csv", "json"]);
    const files = Array.from(fileList).filter((file) => {
      const extension = file.name.toLowerCase().split(".").pop() || "";
      return supported.has(extension);
    });
    if (!files.length) return;
    await run(async () => {
      for (let index = 0; index < files.length; index += 3) {
        await Promise.all(files.slice(index, index + 3).map(async (file) => {
          const data = new FormData();
          data.append("collection_id", selected);
          data.append("file", file);
          const relativePath = (file as File & { webkitRelativePath?: string }).webkitRelativePath;
          if (relativePath) data.append("relative_path", relativePath);
          await api("/sources/upload", { method: "POST", body: data });
        }));
      }
    }, `已导入 ${files.length} 个文件`);
  }
  async function createCollection(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      await api("/collections", { method: "POST", body: JSON.stringify({ name: newCollection, description: "" }) });
      setNewCollection("");
    }, "知识库已创建");
  }
  return (
    <div className="content">
      <div className="page-grid library-grid">
        <section className="panel form-panel"><div className="panel-head"><div><h3>添加资料</h3><p>上传文件或粘贴文本内容</p></div></div>
          <div className="upload-actions">
            <label className="upload-box"><input type="file" accept=".pdf,.txt,.md,.markdown,.csv,.json" onChange={(e) => { const input = e.currentTarget; void uploadFiles(input.files).finally(() => { input.value = ""; }); }} disabled={busy || !selected} /><span>⇧</span><b>上传文件</b><small>选择一份资料</small></label>
            <label className="upload-box"><input ref={folderInputRef} type="file" multiple onChange={(e) => { const input = e.currentTarget; void uploadFiles(input.files).finally(() => { input.value = ""; }); }} disabled={busy || !selected} /><span>▦</span><b>导入文件夹</b><small>批量导入并保留路径</small></label>
          </div>
          <div className="divider"><span>或粘贴文本</span></div>
          <form onSubmit={addText} className="form-stack"><label>所属知识库<select value={selected} onChange={(e) => setCollectionId(e.target.value)}>{collections.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>资料标题<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="例如：RAG 技术入门" required /></label><label>正文内容<textarea value={content} onChange={(e) => setContent(e.target.value)} placeholder="粘贴文章、课堂笔记或研究资料……" required /></label><button className="primary wide" disabled={busy || !selected}>{busy ? "处理中…" : "保存并建立索引"}</button></form>
        </section>
        <section className="panel"><div className="panel-head"><div><h3>资料库</h3><p>{sources.length} 份资料已完成知识化</p></div></div><div className="source-list large">{sources.length ? sources.map((source) => <div className="source-row" key={source.id}><span className={`file-icon ${source.source_type}`}>{source.source_type.toUpperCase().slice(0, 3)}</span><div><b>{source.title}</b><p>{source.summary}</p></div><time>{formatDate(source.created_at)}</time></div>) : <Empty icon="◧" title="等待第一份资料" text="资料上传后会自动切片并建立检索索引。" />}</div></section>
      </div>
      <section className="panel collection-bar"><form onSubmit={createCollection}><div><h3>专题知识库</h3><p>将不同学习主题分开管理</p></div><input value={newCollection} onChange={(e) => setNewCollection(e.target.value)} placeholder="新知识库名称" required /><button className="secondary" disabled={busy}>＋ 创建</button></form><div className="chips">{collections.map((item) => <span key={item.id}><b>{item.name}</b>{item.source_count} 份资料</span>)}</div></section>
    </div>
  );
}

function ChatView({ collections, busy, setBusy, setError }: { collections: Collection[]; busy: boolean; setBusy: (value: boolean) => void; setError: (value: string) => void }) {
  const [query, setQuery] = useState("");
  const [collectionId, setCollectionId] = useState("");
  const [conversationId, setConversationId] = useState<string>();
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string; citations?: Citation[] }[]>([]);
  const selected = collectionId || collections[0]?.id || "";
  async function ask(event: FormEvent) {
    event.preventDefault(); if (!query.trim()) return;
    const current = query; setQuery(""); setMessages((items) => [...items, { role: "user", content: current }]); setBusy(true);
    try {
      const result = await api<{ conversation_id: string; answer: string; citations: Citation[] }>("/chat/query", { method: "POST", body: JSON.stringify({ query: current, collection_id: selected || null, conversation_id: conversationId }) });
      setConversationId(result.conversation_id); setMessages((items) => [...items, { role: "assistant", content: result.answer, citations: result.citations }]);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "问答失败"); }
    finally { setBusy(false); }
  }
  return <div className="content chat-layout"><section className="chat-panel"><div className="chat-head"><div><span className="ai-orb">✦</span><div><h3>知识研究助手</h3><p>回答会严格基于知识库，并显示资料引用</p></div></div><select value={selected} onChange={(e) => setCollectionId(e.target.value)}>{collections.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></div><div className="messages">{messages.length ? messages.map((message, index) => <div key={index} className={`message ${message.role}`}><span>{message.role === "assistant" ? "深" : "我"}</span><div><p>{message.content}</p>{message.citations?.length ? <div className="citations"><b>参考资料</b>{message.citations.map((citation, citationIndex) => <article key={`${citation.source_id}-${citationIndex}`}><em>[{citationIndex + 1}]</em><div><strong>{citation.title}</strong><small>{citation.excerpt}</small></div></article>)}</div> : null}</div></div>) : <div className="chat-empty"><span>✦</span><h2>从你的知识开始提问</h2><p>我会检索资料、组织答案，并标注每一条证据来自哪里。</p><div>{["总结知识库的核心观点", "有哪些概念值得做成卡片？", "帮我找出资料中的观点冲突"].map((text) => <button key={text} onClick={() => setQuery(text)}>{text}</button>)}</div></div>}</div><form className="chat-input" onSubmit={ask}><textarea value={query} onChange={(e) => setQuery(e.target.value)} placeholder="向知识库提问……" onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><button disabled={busy || !query.trim()}>{busy ? "…" : "↑"}</button><small>Enter 发送 · Shift + Enter 换行</small></form></section></div>;
}

function StudyView({ goals, busy, run }: { goals: Goal[]; busy: boolean; run: (action: () => Promise<void>, success: string) => Promise<void> }) {
  const [title, setTitle] = useState(""); const [description, setDescription] = useState(""); const [review, setReview] = useState("");
  async function createGoal(event: FormEvent) { event.preventDefault(); await run(async () => { await api("/learning/goals", { method: "POST", body: JSON.stringify({ title, description }) }); setTitle(""); setDescription(""); }, "学习路径已生成"); }
  async function toggle(task: Task) { await run(async () => { await api(`/learning/tasks/${task.id}`, { method: "PATCH", body: JSON.stringify({ completed: !task.completed }) }); }, task.completed ? "任务已恢复" : "完成一个学习任务"); }
  async function generateReview() { await run(async () => { const result = await api<{ content: string }>("/reviews/generate", { method: "POST", body: JSON.stringify({ period: "weekly" }) }); setReview(result.content); }, "本周复盘已生成"); }
  return <div className="content"><div className="page-grid study-grid"><section className="panel form-panel"><div className="panel-head"><div><h3>创建学习目标</h3><p>系统会自动拆分为可执行任务</p></div></div><form onSubmit={createGoal} className="form-stack"><label>想学什么？<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="例如：两周掌握 RAG 开发" required /></label><label>目标说明<textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="描述当前基础、目标和时间要求……" /></label><button className="primary wide" disabled={busy}>✦ 生成学习路径</button></form><div className="review-card"><span>◫</span><div><b>学习复盘</b><p>结合资料和任务进度发现薄弱点</p></div><button onClick={() => void generateReview()} disabled={busy}>生成周报</button></div></section><section className="panel"><div className="panel-head"><div><h3>学习路径</h3><p>循序渐进地完成每个目标</p></div></div><div className="goals">{goals.length ? goals.map((goal) => <article className="goal" key={goal.id}><header><div><b>{goal.title}</b><p>{goal.description || "持续积累，形成完整认知。"}</p></div><strong>{goal.progress}%</strong></header><div className="progress"><i style={{ width: `${goal.progress}%` }} /></div><div className="goal-tasks">{goal.tasks.map((task) => <button className={task.completed ? "done" : ""} onClick={() => void toggle(task)} key={task.id}><span>{task.completed ? "✓" : ""}</span>{task.title}</button>)}</div></article>) : <Empty icon="◫" title="还没有学习目标" text="创建目标后，AI 会生成五步学习路径。" />}</div></section></div>{review ? <section className="panel review-output"><div className="panel-head"><div><h3>最新学习复盘</h3><p>根据近期资料和任务进度生成</p></div></div><pre>{review}</pre></section> : null}</div>;
}

function ReportsView({ collections, reports, busy, run }: { collections: Collection[]; reports: Report[]; busy: boolean; run: (action: () => Promise<void>, success: string) => Promise<void> }) {
  const [title, setTitle] = useState(""); const [topic, setTopic] = useState(""); const [collectionId, setCollectionId] = useState(""); const [selectedId, setSelectedId] = useState<string>();
  const selected = useMemo(() => reports.find((item) => item.id === selectedId) || reports[0], [reports, selectedId]);
  async function generate(event: FormEvent) { event.preventDefault(); await run(async () => { const result = await api<Report>("/reports/generate", { method: "POST", body: JSON.stringify({ title, topic, collection_id: collectionId || collections[0]?.id || null }) }); setTitle(""); setTopic(""); setSelectedId(result.id); }, "研究报告已生成"); }
  return <div className="content"><div className="page-grid report-grid"><section className="panel form-panel"><div className="panel-head"><div><h3>新建研究报告</h3><p>从知识库证据生成结构化输出</p></div></div><form onSubmit={generate} className="form-stack"><label>报告标题<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="例如：企业 AI Agent 趋势分析" required /></label><label>使用知识库<select value={collectionId || collections[0]?.id || ""} onChange={(e) => setCollectionId(e.target.value)}>{collections.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>研究要求<textarea value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="说明研究问题、报告重点和期望结论……" required /></label><button className="primary wide" disabled={busy}>{busy ? "正在检索与写作…" : "✦ 生成报告"}</button></form><div className="report-history"><h4>历史报告</h4>{reports.map((report) => <button className={selected?.id === report.id ? "active" : ""} key={report.id} onClick={() => setSelectedId(report.id)}><span>▧</span><div><b>{report.title}</b><small>{formatDate(report.created_at)}</small></div></button>)}</div></section><section className="panel report-preview">{selected ? <><div className="panel-head"><div><h3>{selected.title}</h3><p>{selected.topic}</p></div><button onClick={() => navigator.clipboard.writeText(selected.content)}>复制 Markdown</button></div><pre>{selected.content}</pre></> : <Empty icon="▧" title="报告画布等待内容" text="输入研究主题，系统会检索资料并生成带证据的报告草稿。" />}</section></div></div>;
}

function Empty({ icon, title, text }: { icon: string; title: string; text: string }) {
  return <div className="empty"><span>{icon}</span><b>{title}</b><p>{text}</p></div>;
}
