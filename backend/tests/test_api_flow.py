def test_complete_mvp_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "deepstudy-test.db"))

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        collections = client.get("/api/v1/collections").json()
        collection_id = collections[0]["id"]

        source = client.post(
            "/api/v1/sources",
            json={
                "collection_id": collection_id,
                "title": "RAG 入门资料",
                "source_type": "text",
                "content": (
                    "RAG 是检索增强生成技术。它先从知识库检索相关资料，"
                    "再让大语言模型结合资料回答，并保留引用来源。"
                ),
            },
        )
        assert source.status_code == 201

        answer = client.post(
            "/api/v1/chat/query",
            json={"query": "什么是 RAG？", "collection_id": collection_id},
        )
        assert answer.status_code == 200
        assert answer.json()["citations"]

        goal = client.post(
            "/api/v1/learning/goals",
            json={"title": "掌握 RAG 开发", "description": "完成一个问答系统"},
        )
        assert goal.status_code == 201
        assert len(goal.json()["tasks"]) == 5

        report = client.post(
            "/api/v1/reports/generate",
            json={
                "title": "RAG 技术报告",
                "topic": "RAG 检索与引用",
                "collection_id": collection_id,
            },
        )
        assert report.status_code == 201

        dashboard = client.get("/api/v1/dashboard").json()
        assert dashboard["counts"]["sources"] == 1
        assert dashboard["counts"]["reports"] == 1

