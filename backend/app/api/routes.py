import json
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..db import get_connection, rows_to_dicts, utc_now
from ..schemas import (
    ChatRequest,
    CollectionCreate,
    LearningGoalCreate,
    NoteCreate,
    ReportRequest,
    ReviewRequest,
    SourceCreate,
    TaskUpdate,
)
from ..services.documents import extract_upload
from ..services.llm import answer_with_context, call_llm
from ..services.retrieval import rank_chunks, split_text

router = APIRouter(prefix="/api/v1")


def insert_source(payload: SourceCreate) -> dict:
    source_id = str(uuid4())
    chunks = split_text(payload.content)
    summary = payload.content.replace("\n", " ").strip()[:180]
    with get_connection() as connection:
        collection = connection.execute(
            "SELECT id FROM collections WHERE id = ?", (payload.collection_id,)
        ).fetchone()
        if not collection:
            raise HTTPException(status_code=404, detail="知识库不存在")
        connection.execute(
            """INSERT INTO sources
            (id, collection_id, title, source_type, content, summary, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'ready', ?)""",
            (
                source_id,
                payload.collection_id,
                payload.title,
                payload.source_type,
                payload.content,
                summary,
                utc_now(),
            ),
        )
        connection.executemany(
            "INSERT INTO source_chunks (id, source_id, chunk_index, content) VALUES (?, ?, ?, ?)",
            [(str(uuid4()), source_id, index, chunk) for index, chunk in enumerate(chunks)],
        )
        row = connection.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    return dict(row)


def retrieve(query: str, collection_id: str | None = None, limit: int = 6) -> list[dict]:
    sql = """SELECT sc.id, sc.content, sc.chunk_index, s.id AS source_id, s.title
             FROM source_chunks sc JOIN sources s ON s.id = sc.source_id"""
    params: tuple = ()
    if collection_id:
        sql += " WHERE s.collection_id = ?"
        params = (collection_id,)
    with get_connection() as connection:
        chunks = rows_to_dicts(connection.execute(sql, params).fetchall())
    return rank_chunks(query, chunks, limit=limit)


@router.get("/dashboard")
def dashboard() -> dict:
    with get_connection() as connection:
        counts = {
            "collections": connection.execute("SELECT COUNT(*) FROM collections").fetchone()[0],
            "sources": connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "notes": connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0],
            "reports": connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
        }
        recent_sources = rows_to_dicts(
            connection.execute(
                "SELECT id, title, source_type, summary, created_at FROM sources ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
        )
        tasks = rows_to_dicts(
            connection.execute(
                """SELECT lt.*, lg.title AS goal_title FROM learning_tasks lt
                JOIN learning_goals lg ON lg.id = lt.goal_id
                WHERE lt.completed = 0 ORDER BY lg.created_at DESC, lt.position LIMIT 5"""
            ).fetchall()
        )
    return {"counts": counts, "recent_sources": recent_sources, "today_tasks": tasks}


@router.get("/collections")
def list_collections() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """SELECT c.*, COUNT(s.id) AS source_count FROM collections c
            LEFT JOIN sources s ON s.collection_id = c.id
            GROUP BY c.id ORDER BY c.created_at DESC"""
        ).fetchall()
    return rows_to_dicts(rows)


@router.post("/collections", status_code=201)
def create_collection(payload: CollectionCreate) -> dict:
    item = {"id": str(uuid4()), **payload.model_dump(), "created_at": utc_now()}
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO collections (id, name, description, created_at) VALUES (?, ?, ?, ?)",
            (item["id"], item["name"], item["description"], item["created_at"]),
        )
    return {**item, "source_count": 0}


@router.get("/sources")
def list_sources(collection_id: str | None = None) -> list[dict]:
    sql = "SELECT id, collection_id, title, source_type, summary, status, created_at FROM sources"
    params: tuple = ()
    if collection_id:
        sql += " WHERE collection_id = ?"
        params = (collection_id,)
    sql += " ORDER BY created_at DESC"
    with get_connection() as connection:
        return rows_to_dicts(connection.execute(sql, params).fetchall())


@router.post("/sources", status_code=201)
def create_source(payload: SourceCreate) -> dict:
    return insert_source(payload)


@router.post("/sources/upload", status_code=201)
async def upload_source(
    collection_id: str = Form(...),
    file: UploadFile = File(...),
    relative_path: str | None = Form(None),
) -> dict:
    original_title, content = await extract_upload(file)
    title = (relative_path or original_title).replace("\\", "/").strip("/")[:200]
    suffix = original_title.lower().rsplit(".", 1)[-1] if "." in original_title else "text"
    return insert_source(
        SourceCreate(collection_id=collection_id, title=title, source_type=suffix, content=content)
    )


@router.get("/notes")
def list_notes() -> list[dict]:
    with get_connection() as connection:
        return rows_to_dicts(connection.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall())


@router.post("/notes", status_code=201)
def create_note(payload: NoteCreate) -> dict:
    item = {"id": str(uuid4()), **payload.model_dump(), "created_at": utc_now()}
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO notes (id, collection_id, title, content, note_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (item["id"], item["collection_id"], item["title"], item["content"], item["note_type"], item["created_at"]),
        )
    return item


@router.post("/chat/query")
async def chat(payload: ChatRequest) -> dict:
    passages = retrieve(payload.query, payload.collection_id)
    answer = await answer_with_context(payload.query, passages)
    citations = [
        {
            "source_id": item["source_id"],
            "title": item["title"],
            "excerpt": item["content"][:240],
            "score": item["score"],
        }
        for item in passages
    ]
    conversation_id = payload.conversation_id or str(uuid4())
    now = utc_now()
    with get_connection() as connection:
        exists = connection.execute(
            "SELECT id FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if not exists:
            connection.execute(
                "INSERT INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
                (conversation_id, payload.query[:60], now),
            )
        connection.execute(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, 'user', ?, ?)",
            (str(uuid4()), conversation_id, payload.query, now),
        )
        connection.execute(
            """INSERT INTO messages
            (id, conversation_id, role, content, citations_json, created_at)
            VALUES (?, ?, 'assistant', ?, ?, ?)""",
            (str(uuid4()), conversation_id, answer, json.dumps(citations, ensure_ascii=False), now),
        )
    return {"conversation_id": conversation_id, "answer": answer, "citations": citations}


@router.get("/learning/goals")
def list_learning_goals() -> list[dict]:
    with get_connection() as connection:
        goals = rows_to_dicts(
            connection.execute("SELECT * FROM learning_goals ORDER BY created_at DESC").fetchall()
        )
        for goal in goals:
            goal["tasks"] = rows_to_dicts(
                connection.execute(
                    "SELECT * FROM learning_tasks WHERE goal_id = ? ORDER BY position", (goal["id"],)
                ).fetchall()
            )
    return goals


@router.post("/learning/goals", status_code=201)
def create_learning_goal(payload: LearningGoalCreate) -> dict:
    goal_id = str(uuid4())
    task_titles = [
        "明确目标并收集核心资料",
        "阅读资料并标记关键概念",
        "通过问答解决理解盲点",
        "整理知识卡片并完成一次测验",
        "生成专题总结并进行复盘",
    ]
    with get_connection() as connection:
        connection.execute(
            """INSERT INTO learning_goals
            (id, title, description, target_date, progress, created_at) VALUES (?, ?, ?, ?, 0, ?)""",
            (goal_id, payload.title, payload.description, payload.target_date, utc_now()),
        )
        connection.executemany(
            "INSERT INTO learning_tasks (id, goal_id, title, completed, position) VALUES (?, ?, ?, 0, ?)",
            [(str(uuid4()), goal_id, title, index) for index, title in enumerate(task_titles)],
        )
    return next(goal for goal in list_learning_goals() if goal["id"] == goal_id)


@router.patch("/learning/tasks/{task_id}")
def update_learning_task(task_id: str, payload: TaskUpdate) -> dict:
    with get_connection() as connection:
        task = connection.execute("SELECT * FROM learning_tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="学习任务不存在")
        connection.execute(
            "UPDATE learning_tasks SET completed = ? WHERE id = ?", (int(payload.completed), task_id)
        )
        goal_id = task["goal_id"]
        total, completed = connection.execute(
            "SELECT COUNT(*), SUM(completed) FROM learning_tasks WHERE goal_id = ?", (goal_id,)
        ).fetchone()
        progress = round((completed or 0) / max(total, 1) * 100)
        connection.execute("UPDATE learning_goals SET progress = ? WHERE id = ?", (progress, goal_id))
    return {"id": task_id, "completed": payload.completed, "progress": progress}


@router.post("/reviews/generate", status_code=201)
async def generate_review(payload: ReviewRequest) -> dict:
    with get_connection() as connection:
        recent = rows_to_dicts(
            connection.execute(
                "SELECT title, summary FROM sources ORDER BY created_at DESC LIMIT 8"
            ).fetchall()
        )
        task_stats = connection.execute(
            "SELECT COUNT(*), SUM(completed) FROM learning_tasks"
        ).fetchone()
    materials = "\n".join(f"- {item['title']}：{item['summary']}" for item in recent) or "暂无新增资料"
    generated = await call_llm(
        "你是学习教练，请根据学习资料和任务完成情况生成简洁、具体、可执行的中文复盘。",
        f"复盘周期：{payload.period}\n资料：\n{materials}\n任务：完成 {task_stats[1] or 0}/{task_stats[0]}",
    )
    content = generated or (
        f"## 本期学习概览\n\n已整理 {len(recent)} 份近期资料，学习任务完成 "
        f"{task_stats[1] or 0}/{task_stats[0]}。\n\n## 近期资料\n\n{materials}\n\n"
        "## 下一步建议\n\n1. 选择一份核心资料进行精读。\n2. 对不理解的概念进行知识库问答。"
        "\n3. 将关键结论整理成知识卡片。"
    )
    item = {"id": str(uuid4()), "period": payload.period, "content": content, "created_at": utc_now()}
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO reviews (id, period, content, created_at) VALUES (?, ?, ?, ?)",
            (item["id"], item["period"], item["content"], item["created_at"]),
        )
    return item


@router.get("/reports")
def list_reports() -> list[dict]:
    with get_connection() as connection:
        return rows_to_dicts(
            connection.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()
        )


@router.post("/reports/generate", status_code=201)
async def generate_report(payload: ReportRequest) -> dict:
    passages = retrieve(payload.topic, payload.collection_id, limit=8)
    context = "\n\n".join(
        f"[{index + 1}]《{item['title']}》\n{item['content']}" for index, item in enumerate(passages)
    )
    generated = await call_llm(
        "你是专业研究报告作者。基于给定材料生成中文 Markdown 报告，包括摘要、主要发现、分析、结论和建议。"
        "所有基于材料的关键结论使用 [1] 格式引用，禁止编造证据。",
        f"报告标题：{payload.title}\n研究主题：{payload.topic}\n\n资料：\n{context or '暂无相关资料'}",
    )
    if generated:
        content = generated
    else:
        evidence = "\n".join(
            f"- 《{item['title']}》：{item['content'][:220].replace(chr(10), ' ')} [{index + 1}]"
            for index, item in enumerate(passages)
        ) or "- 当前知识库中没有检索到相关材料。"
        content = (
            f"# {payload.title}\n\n## 摘要\n\n本报告围绕“{payload.topic}”整理现有知识库资料。"
            "\n\n## 主要证据\n\n" + evidence +
            "\n\n## 待补充研究\n\n当前未配置大语言模型。配置模型后可自动完成综合分析、结论与建议。"
        )
    item = {
        "id": str(uuid4()), "title": payload.title, "topic": payload.topic,
        "content": content, "status": "completed", "created_at": utc_now(),
    }
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO reports (id, title, topic, content, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (item["id"], item["title"], item["topic"], item["content"], item["status"], item["created_at"]),
        )
    return item
