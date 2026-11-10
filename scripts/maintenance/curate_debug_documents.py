"""显式整理问题与经验：先备份和生成草稿，审阅后按原版本整批提交。"""

import argparse
import asyncio
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def apply_drafts(database, directory):
    """全部校验后在同一事务发布；旧修订、原图和来源身份不覆盖。"""
    from app.core.identifiers import now_iso
    from app.infrastructure.database.session import Database
    from app.modules.handover.domain.debug_knowledge import knowledge_payload
    from app.modules.handover.domain.schemas import validate_payload
    from app.modules.handover.infrastructure.persistence.models import HandoverRecord
    from app.modules.handover.infrastructure.persistence.repository import (
        HandoverStore,
        dump,
    )
    from sqlalchemy import select

    rows = json.loads((directory / "source.json").read_text(encoding="utf-8"))
    approved = json.loads((directory / "reviewed.json").read_text(encoding="utf-8"))
    if set(approved) != {row["id"] for row in rows}:
        raise ValueError("必须逐条完成全部草稿审阅，不能部分发布")
    values = {}
    for row in rows:
        raw = (directory / "drafts" / f"{row['id']}.json").read_text(encoding="utf-8")
        if digest(raw) != approved[row["id"]]:
            raise ValueError("草稿在审阅后变化，须重新审阅")
        draft_value = json.loads(raw)
        if set(draft_value) != {"question", "answer", "keywords"}:
            raise ValueError("草稿必须只有问题、答案、关键词")
        if not draft_value["question"].strip() or not draft_value["answer"].strip():
            raise ValueError("问题与答案不能为空")
        value = {**knowledge_payload(row["payload"]), **draft_value}
        values[row["id"]] = validate_payload("debug_issue", value)
    db = Database(database)
    store = HandoverStore(database=db)
    try:
        with store.lock, db.session.begin() as session:
            current = {
                row.id: row
                for row in session.scalars(
                    select(HandoverRecord).where(HandoverRecord.kind == "debug_issue")
                )
            }
            if set(current) != set(approved):
                raise ValueError("记录集合已变化，未发布；请重新建立快照")
            for old in rows:
                row = current[old["id"]]
                if (
                    row.version != old["version"]
                    or digest(row.payload_json) != old["fingerprint"]
                ):
                    raise ValueError("记录在整理期间变化，未发布；请重新核对")
            for old in rows:
                row = current[old["id"]]
                store._validate(session, row.id, row.kind, values[row.id])
                row.payload_json = dump(values[row.id])
                row.version += 1
                row.updated_at = now_iso()
                if row.state == "confirmed":
                    row.state = "needs_review"
                store._snapshot(
                    session,
                    row,
                    "updated",
                    "知识整理（用户授权）",
                    "整理为问题、答案、关键词；原文、原图和来源保存在metadata与历史修订",
                )
                store._invalidate(
                    session, row.id, "知识整理（用户授权）", "问答内容已整理"
                )
            session.flush()
    finally:
        db.close()
    report = {"updated": len(rows), "backup": str(directory / "before.sqlite3")}
    (directory / "applied.json").write_text(
        json.dumps(report, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True))


def snapshot(database, directory):
    directory.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    backup = directory / "before.sqlite3"
    if backup.exists():
        raise ValueError("备份已存在，请使用新的输出目录")
    with sqlite3.connect(backup) as target:
        source.backup(target)
    rows = [
        dict(row)
        for row in source.execute(
            "SELECT * FROM handover_records WHERE kind = 'debug_issue' ORDER BY id"
        )
    ]
    source.close()
    for row in rows:
        row["fingerprint"] = digest(row["payload_json"])
        row["payload"] = json.loads(row.pop("payload_json"))
    (directory / "source.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"backed_up": len(rows), "directory": str(directory)}, ensure_ascii=True
        )
    )


async def draft(directory, audit=False):
    import httpx
    from anthropic import APIError as AnthropicError
    from app.core.config import Paths, SettingsStore
    from app.infrastructure.providers.models import create_model
    from app.modules.handover.infrastructure.ai import json_model
    from langchain_core.messages import HumanMessage, SystemMessage
    from openai import APIError as OpenAIError

    rows = json.loads((directory / "source.json").read_text(encoding="utf-8"))
    settings = SettingsStore(Paths()).load().model
    model = create_model(settings)
    writer = json_model(model, settings)
    semaphore = asyncio.Semaphore(3)
    target = directory / ("reviews" if audit else "drafts")
    target.mkdir(exist_ok=True)
    prompt = """将一条现有知识整理成问题、答案、关键词，只返回JSON对象question、answer、keywords。
用户已批准重新措辞。问题写成自然的问句；答案以完整句子组织，合并重复表达，直接回答。
仅据提供的内容改写，保留所有影响理解的条件、机型、模块、参数、单位、方法、结果及不确定性。
不得补造原文没有的解决方案、原因、操作顺序或验证结果；未解决问题如实写已知现象和已有建议。
工作进展和资料归档按事实回答，不能虚构处理方案；日期或人员是事情本身的关键信息时仍保留。
记录人、录入时间、来源编号等管理信息不写入答案；其由程序完整保存在metadata。
不要复述字段标签，不说‘记录库里’‘本条记录’‘根据记录’‘原记录显示’，不添加套话、追问或免责声明。
原文原因解释未被证实时用‘可能’‘当时判断’等自然措辞，不写成确定因果；组合效果不拆成单项有效。
不能遗漏数字、条件、否定和未知单位；参数单位未知时简短标注，不能建议按未确认单位的数值直接操作。
关键词为3至12个简短检索词，可含同义叫法；不放导入编号、记录人或时间。
格式：{"question":"……？","answer":"完整的句子。","keywords":["关键词"]}。"""
    if audit:
        prompt = """核对整理后的问答是否忠实于原始知识，只检查事实，不要求照抄措辞。
允许合并、删去无关历史背景和管理信息，以及把记录人判断改为自然的有限定说法。
重点检查关键参数、单位、机型、工况、否定、结果及未验证状态有无遗漏或误改，是否补造新处理方法或因果。
原始知识内来源编号、附件路径、跨记录检索提示和人工清单不是问答必须包含的内容。
历史日期若未明确年份不得自行推断；保留事件日期不等于把录入时间当作试验日期。
不要引入别条记录。只有明确事实错误或遗漏影响答案使用的必要事实时给issues。
只返回JSON：{"verdict":"passed或needs_correction","issues":["具体问题及对应原文"]}。"""

    async def one(row):
        path = target / f"{row['id']}.json"
        if path.exists():
            return
        async with semaphore:
            for attempt in range(3):
                try:
                    payload = {"title": row["title"], "payload": row["payload"]}
                    if audit:
                        payload["draft"] = json.loads(
                            (directory / "drafts" / f"{row['id']}.json").read_text(
                                encoding="utf-8"
                            )
                        )
                    reply = await writer.ainvoke(
                        [
                            SystemMessage(content=prompt),
                            HumanMessage(
                                content=json.dumps(payload, ensure_ascii=False)
                            ),
                        ]
                    )
                    value = json.loads(
                        reply.text.strip()
                        .removeprefix("```json")
                        .removesuffix("```")
                        .strip()
                    )
                    if audit:
                        if value.get("verdict") not in {
                            "passed",
                            "needs_correction",
                        } or not isinstance(value.get("issues"), list):
                            raise ValueError("复核结构无效")
                        path.write_text(
                            json.dumps(value, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                        print(
                            json.dumps(
                                {"audited": row["id"], "verdict": value["verdict"]}
                            ),
                            flush=True,
                        )
                        return
                    if set(value) != {"question", "answer", "keywords"}:
                        raise ValueError("草稿字段不符合三项结构")
                    if (
                        not isinstance(value["question"], str)
                        or not value["question"].strip()
                    ):
                        raise ValueError("草稿缺少问题")
                    if (
                        not isinstance(value["answer"], str)
                        or not value["answer"].strip()
                    ):
                        raise ValueError("草稿缺少完整答案")
                    if (
                        not isinstance(value["keywords"], list)
                        or not all(
                            isinstance(word, str) and 0 < len(word) <= 100
                            for word in value["keywords"]
                        )
                        or len(value["keywords"]) > 20
                    ):
                        raise ValueError("关键词格式无效")
                    path.write_text(
                        json.dumps(value, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    print(
                        json.dumps(
                            {
                                "drafted": row["id"],
                                "count": len(list(target.glob("*.json"))),
                            },
                            ensure_ascii=True,
                        ),
                        flush=True,
                    )
                    return
                except (
                    ValueError,
                    TimeoutError,
                    OSError,
                    httpx.HTTPError,
                    AnthropicError,
                    OpenAIError,
                ) as error:
                    if attempt == 2:
                        raise RuntimeError(
                            f"草稿生成失败：{row['id']}（{type(error).__name__}）"
                        ) from None

    try:
        await asyncio.gather(*(one(row) for row in rows))
    finally:
        for name in ("http_async_client", "http_client"):
            client = getattr(model, name, None)
            if client is not None:
                close = getattr(client, "aclose", None)
                if close:
                    await close()
                elif getattr(client, "close", None):
                    client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("snapshot", "draft", "audit", "apply"))
    parser.add_argument("--database", type=Path, default=ROOT / "data/app.sqlite3")
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "snapshot":
        snapshot(args.database.resolve(), args.directory.resolve())
    elif args.action == "apply":
        apply_drafts(args.database.resolve(), args.directory.resolve())
    else:
        asyncio.run(draft(args.directory.resolve(), audit=args.action == "audit"))


if __name__ == "__main__":
    main()
