"""按现场常见问法验收检索，所有案例只进入临时数据库。"""

from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus
from app.modules.knowledge.corpora.handover_materials import HandoverMaterialCorpus


def test_twenty_realistic_question_variants(services):
    issues = DebugIssues(HandoverStore(database=services[1]))
    records = {}
    for title, payload in (
        (
            "中转台取片异常",
            {
                "problem": "中转台取片不稳定",
                "device": "ZX2200 HS",
                "software_version": "2.1.0",
                "conditions": "加热生产",
                "cause": "芯片背胶粘连",
                "solution": "增加中转台吹气并改成吸嘴",
                "resolution_status": "resolved",
            },
        ),
        ("真空报警 E901", {"problem": "取片时 E901 负压不足", "resolution_status": "open"}),
        (
            "载具通信中断",
            {
                "problem": "载具控制器 TCP 断连",
                "solution": "检查交换机端口和网线连接",
                "resolution_status": "resolved",
            },
        ),
    ):
        records[title] = issues.save(DebugWrite(title=title, payload=payload), {})["id"]
    corpus = DebugIssueCorpus(services[1])
    debug_cases = (
        ("中转台取片异常怎么处理", "中转台取片异常"),
        ("之前中转台吸不起来怎么解决的", "中转台取片异常"),
        ("中间平台抓取不稳定", "中转台取片异常"),
        ("芯片黏住平台取不下来", "中转台取片异常"),
        ("IPT 拾取失败", "中转台取片异常"),
        ("背胶粘片有什么经验", "中转台取片异常"),
        ("ZX2200 HS V2.1.0 加热取片异常", "中转台取片异常"),
        ("中转台改吸嘴的历史方案", "中转台取片异常"),
        ("E901 报警", "真空报警 E901"),
        ("真空 E901 修好了吗", "真空报警 E901"),
        ("E901 负压不足如何排查", "真空报警 E901"),
        ("载具 TCP 掉线", "载具通信中断"),
        ("托盘控制器连接中断", "载具通信中断"),
        ("E999 报警", None),
        ("ZX2300 中转台取片异常", None),
        ("V3.0.0 中转台取片异常", None),
        ("常温下中转台取片异常", None),
    )
    for question, title in debug_cases:
        rows = corpus.search(question)
        if title:
            assert rows and rows[0]["id"] == records[title], (
                question,
                [row["title"] for row in rows],
            )
        else:
            assert records["中转台取片异常"] not in {row["id"] for row in rows}, question
        if "E999" in question:
            assert rows == []
    store = HandoverStore(database=services[1])
    row = store.create(
        "source",
        "停机恢复规程",
        {"content": "机器停止后重新启动生产，需要先恢复运行条件，再确认联锁。"},
        "测试",
    )
    documents = HandoverMaterialCorpus(services[1])
    for question in ("停机以后怎样重新生产", "恢复生产前要确认什么", "交接资料里怎样恢复运行"):
        assert documents.search(question)[0]["id"] == row["id"]


def test_function_description_remains_candidate_when_requested_stage_is_unknown(services):
    issues = DebugIssues(HandoverStore(database=services[1]))
    saved = [
        issues.save(
            DebugWrite(
                title=f"中转台取片记录 {module}",
                payload={
                    "problem": "中转台加热后取片不稳",
                    "module": module,
                },
            ),
            {},
        )
        for module in ("中转台取片", "S1点胶")
    ]
    result = DebugIssueCorpus(services[1]).search_report("S2 中转台加热取片不稳")
    assert [row["id"] for row in result["matches"]] == [saved[0]["id"]]
    assert result["matches"][0]["compatibility"]["status"] == "needs_confirmation"
    assert "module" in result["matches"][0]["compatibility"]["missing"]
    assert saved[1]["id"] in {row["id"] for row in result["excluded_records"]}
