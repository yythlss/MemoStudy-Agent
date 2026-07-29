import httpx

from ..config import settings


async def call_llm(system_prompt: str, user_prompt: str) -> str | None:
    if not settings.llm_base_url or not settings.llm_model:
        return None
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    payload = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{settings.llm_base_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return None


async def answer_with_context(question: str, passages: list[dict]) -> str:
    context = "\n\n".join(
        f"[{index + 1}]《{item['title']}》\n{item['content']}"
        for index, item in enumerate(passages)
    )
    generated = await call_llm(
        "你是严谨的个人知识助手。只能依据给定资料回答；信息不足时必须明确说明。"
        "回答使用中文，并用 [1]、[2] 标记引用。",
        f"用户问题：{question}\n\n可用资料：\n{context}",
    )
    if generated:
        return generated
    if not passages:
        return "当前知识库中还没有找到相关内容。请先导入资料，或换一种问法。"
    points = []
    for index, item in enumerate(passages[:3]):
        excerpt = item["content"].replace("\n", " ").strip()
        if len(excerpt) > 180:
            excerpt = excerpt[:180] + "……"
        points.append(f"- {excerpt} [{index + 1}]")
    return "根据当前知识库，找到以下相关信息：\n\n" + "\n".join(points) + (
        "\n\n当前未配置大语言模型，因此这里展示的是检索摘要；配置模型后会生成完整回答。"
    )

