"""独立验收：直接调用 LibraryService 与 reports，验证搜索分页/热门榜。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from library import LibraryService  # noqa: E402
from library.reports import popular_books  # noqa: E402

FAILS = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def main():
    svc = LibraryService()
    a = svc.add_book("Clean Code", "Robert Martin", 2008)
    b = svc.add_book("The Clean Coder", "Robert Martin", 2011)
    c = svc.add_book("Refactoring", "Martin Fowler", 2018)

    result = svc.search_books("clean")
    check("搜索不区分大小写", {item.id for item in result["items"]} == {a.id, b.id}, str(result))
    check("total 正确", result["total"] == 2, str(result.get("total")))
    check("空 query 返回全部", svc.search_books("")["total"] == 3)

    result = svc.search_books("fowler")
    check("按作者搜索", [item.id for item in result["items"]] == [c.id], str(result))

    first = svc.search_books("", page=1, size=2)
    second = svc.search_books("", page=2, size=2)
    check("分页第一页 2 条", len(first["items"]) == 2 and first["total"] == 3, str(first))
    check("分页第二页 1 条", len(second["items"]) == 1, str(second))
    check("分页按 id 升序", [item.id for item in first["items"]] == [a.id, b.id])

    for kwargs in ({"page": 0}, {"size": 0}, {"size": 101}):
        try:
            svc.search_books("", **kwargs)
            check(f"非法参数抛 ValueError {kwargs}", False)
        except ValueError:
            check(f"非法参数抛 ValueError {kwargs}", True)

    member = svc.register_member("张三")
    svc.loan(a.id, member.id, "2026-01-01")
    svc.return_book(a.id)
    svc.loan(a.id, member.id, "2026-01-02")
    svc.loan(b.id, member.id, "2026-01-03")
    popular = popular_books(svc)
    check(
        "热门榜按次数排序",
        popular[0][0] == "Clean Code" and popular[0][1] == 2 and popular[1][1] == 1,
        str(popular),
    )
    check("热门榜 limit", len(popular_books(svc, limit=1)) == 1)
    try:
        popular_books(svc, limit=0)
        check("非法 limit 抛 ValueError", False)
    except ValueError:
        check("非法 limit 抛 ValueError", True)

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
