"""知识正文与检索metadata分离，保留固定版本和来源关联。"""

from langchain_core.documents import Document

from app.modules.handover.domain.debug_knowledge import knowledge_payload


def knowledge_document(row):
    payload = knowledge_payload(row["payload"])
    content = {
        "问题": payload["question"],
        "答案": payload["answer"],
        "关键词": "、".join(payload["keywords"]),
    }
    return Document(
        page_content="\n\n".join(f"{key}：{value}" for key, value in content.items() if value),
        metadata={
            **payload["metadata"],
            **{
                key: row[key]
                for key in ("id", "title", "version", "created_at", "updated_at")
                if key in row
            },
        },
    )
