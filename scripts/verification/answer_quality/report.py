"""由独立逐题审阅分数生成成绩，不把被测模型的自评当作准确性评分。"""

import csv
import json
import statistics
from pathlib import Path


def build(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    grades = json.loads((directory / "grades.json").read_text(encoding="utf-8"))
    expected = {row["id"] for row in manifest["cases"]}
    if len(grades) != 20 or {row["id"] for row in grades} != expected:
        raise ValueError("必须完成全部20题评分，不能省略失败题")
    results = {
        key: json.loads((directory / "results" / f"{key}.json").read_text(encoding="utf-8"))
        for key in expected
    }
    rows = []
    for grade in sorted(grades, key=lambda row: row["id"]):
        if any(
            type(grade[key]) is not int or not 0 <= grade[key] <= 5
            for key in ("accuracy", "readability")
        ):
            raise ValueError("分数应为0至5整数")
        if not grade.get("evidence") or not grade.get("guidance"):
            raise ValueError("需要逐题评分依据和引导判断")
        result = results[grade["id"]]
        rows.append(
            {
                **grade,
                "category": result["category"],
                "seconds": result["seconds"],
                "status": result["status"],
                "passed": grade["accuracy"] >= 4
                and grade["readability"] >= 4
                and not grade.get("critical", False),
                "cited_records": result.get("cited_records", []),
                "image_positions": result.get("image_positions", 0),
            }
        )
    summary = {
        "count": len(rows),
        "experience": sum(row["category"] == "experience" for row in rows),
        "flow": sum(row["category"] == "flow" for row in rows),
        "answered": sum(row["status"] == "answered" for row in rows),
        "passed": sum(row["passed"] for row in rows),
        "accuracy_mean": statistics.mean(row["accuracy"] for row in rows),
        "readability_mean": statistics.mean(row["readability"] for row in rows),
        "median_seconds": statistics.median(row["seconds"] for row in rows),
        "max_seconds": max(row["seconds"] for row in rows),
        "critical_cases": [row["id"] for row in rows if row.get("critical")],
        "fallback_cases": [
            key
            for key, row in results.items()
            if "本轮回答未通过复核" in row["answer"] or "资料尚未完成范围核对" in row["answer"]
        ],
        "reviewer": (
            "当前助手对照先验核对点、记录原文、源码与浏览器逐题审阅；"
            "不是被测模型自评，也不是现场工程师验收"
        ),
        "application_sha256": manifest["application_sha256"],
        "dataset_sha256": manifest["dataset_sha256"],
    }
    (directory / "summary.json").write_text(
        json.dumps({**summary, "scores": rows}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (directory / "scorecard.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=(
                "id",
                "category",
                "accuracy",
                "readability",
                "passed",
                "seconds",
                "guidance",
                "evidence",
            ),
        )
        writer.writeheader()
        writer.writerows({key: row[key] for key in writer.fieldnames} for row in rows)
    table = [
        "| 题号 | 类型 | 准确性/5 | 阅读/5 | 达标 | 秒 | 引导 | 依据 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    table += [
        f"| {row['id']} | {row['category']} | {row['accuracy']} | {row['readability']} | "
        f"{'是' if row['passed'] else '否'} | {row['seconds']} | {row['guidance']} | "
        f"{row['evidence'].replace('|', ' / ').replace(chr(10), ' ')} |"
        for row in rows
    ]
    (directory / "scorecard.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    import sys

    print(json.dumps(build(sys.argv[1]), ensure_ascii=False, indent=2))
