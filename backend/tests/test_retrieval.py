from app.services.retrieval import rank_chunks, score_text, split_text


def test_split_text_keeps_content():
    text = "第一段知识。\n\n第二段知识。"
    chunks = split_text(text, chunk_size=20)
    assert chunks
    assert "第一段知识" in chunks[0]


def test_chinese_query_scores_related_text_higher():
    related = score_text("什么是向量检索", "向量检索可以按照语义相似度查找文档")
    unrelated = score_text("什么是向量检索", "今天的天气非常晴朗")
    assert related > unrelated


def test_rank_chunks_returns_best_first():
    chunks = [
        {"id": "1", "content": "苹果是一种水果"},
        {"id": "2", "content": "RAG 使用向量检索寻找相关文档"},
    ]
    result = rank_chunks("RAG 向量检索", chunks)
    assert result[0]["id"] == "2"

