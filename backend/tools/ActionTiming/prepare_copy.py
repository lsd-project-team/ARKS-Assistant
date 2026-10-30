"""在新目录复制并接入首批动作；输入源码始终只读，拒绝覆盖已有副本。"""

import argparse
import difflib
import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import tree_sitter_c_sharp
from tree_sitter import Language, Parser

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PREFIX = "global::Arks.ActionTiming.ZxTiming"
PARSER = Parser(Language(tree_sitter_c_sharp.language()))
IGNORED = {"bin", "obj", ".vs", ".git", "__pycache__"}
TASKS = {
    "DispenseSystem/Tasks/DispenseWorkTask.cs": "S1",
    "BondSystem/Tasks/BondTask.cs": "S2",
}


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def source_files(root):
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and not IGNORED.intersection(path.relative_to(root).parts)
    )


def reject_links(root):
    if any(
        (path.is_symlink() or path.is_junction())
        for path in root.rglob("*")
        if not IGNORED.intersection(path.relative_to(root).parts)
    ):
        raise ValueError("源码副本不接受符号链接，请使用普通目录快照")


def fingerprint(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_files(root)
    }


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"源码入口已变化，无法唯一接入：{before}")
    return text.replace(before, after, 1)


def dependency_projects(source):
    """保留现有ProjectReference的同级布局；缺失工程单列，不伪造依赖。"""
    solution = source.parent.resolve()
    pending, seen, roots, missing = [source / "AKRS.ZX2200.csproj"], set(), set(), set()
    while pending:
        project = pending.pop().resolve()
        if project in seen:
            continue
        seen.add(project)
        tree = ET.parse(project)
        for node in tree.getroot().iter():
            if node.tag.rsplit("}", 1)[-1] != "ProjectReference":
                continue
            target = (project.parent / node.attrib["Include"].replace("\\", "/")).resolve()
            if not target.is_relative_to(solution):
                raise ValueError("引用工程超出源码解决方案目录，请先核对引用")
            if not target.is_file():
                missing.add(target.relative_to(solution).as_posix())
                continue
            top = solution / target.relative_to(solution).parts[0]
            if top != source:
                roots.add(top)
            pending.append(target)
    return sorted(roots), sorted(missing)


def instrument_method(text, method, branch=None, calls=None):
    """按语法节点插入，注释/字符串中的伪调用不会被当成接入点。"""
    raw = text.encode("utf-8")
    tree = PARSER.parse(raw)
    if tree.root_node.has_error:
        raise ValueError("C#源码语法解析失败")
    methods = [
        node
        for node in walk(tree.root_node)
        if node.type == "method_declaration"
        and raw[
            node.child_by_field_name("name").start_byte : node.child_by_field_name("name").end_byte
        ].decode()
        == method
    ]
    if len(methods) != 1:
        raise ValueError(f"无法唯一确定方法：{method}")
    node = methods[0]
    edits = []
    if branch:
        body = node.child_by_field_name("body")
        edits.append(
            (
                body.start_byte + 1,
                body.start_byte + 1,
                f"\n            {PREFIX}.Branch({branch});".encode(),
            )
        )
    counts = {name: 0 for name in (calls or {})}
    for call in walk(node):
        if call.type != "invocation_expression":
            continue
        function = call.child_by_field_name("function")
        expression = raw[function.start_byte : function.end_byte].decode()
        if expression not in (calls or {}):
            continue
        stage, category = calls[expression]
        original = raw[call.start_byte : call.end_byte].decode()
        replacement = f'{PREFIX}.Stage("{stage}", "{category}", () => {original})'
        edits.append((call.start_byte, call.end_byte, replacement.encode()))
        counts[expression] += 1
    if any(count == 0 for count in counts.values()):
        raise ValueError(f"{method}缺少预期调用：{counts}")
    for start, end, replacement in sorted(edits, reverse=True):
        raw = raw[:start] + replacement + raw[end:]
    if PARSER.parse(raw).root_node.has_error:
        raise ValueError(f"{method}接入后语法无效")
    return raw.decode()


def build_edits(source):
    if (source / "ArksActionTiming").exists():
        raise ValueError("输入已是采集副本，请复用现有副本，不能重复接入")
    edits = {}
    for relative, station in TASKS.items():
        text = (source / relative).read_text(encoding="utf-8-sig")
        text = replace_once(
            text,
            "actionNode.IsDoWork()",
            f'{PREFIX}.ShouldRun(actionNode.Name, "{station}", () => actionNode.IsDoWork())',
        )
        edits[relative] = replace_once(
            text,
            "actionNode.DoWork()",
            f'{PREFIX}.Invoke(actionNode.Name, "{station}", () => actionNode.DoWork())',
        )
    machine = "Main/Machine/MachineSupport/Machine.Operate.cs"
    text = (source / machine).read_text(encoding="utf-8-sig")
    # Start与Stop语法方法各自定位，避免误改Continue中的Working状态设置。
    raw = text.encode()
    tree = PARSER.parse(raw)
    lifecycle = []
    for node in walk(tree.root_node):
        if node.type != "method_declaration":
            continue
        name = node.child_by_field_name("name")
        name = raw[name.start_byte : name.end_byte].decode()
        if name not in {"Start", "Stop"}:
            continue
        original = raw[node.start_byte : node.end_byte].decode()
        if name == "Start":
            updated = replace_once(
                original,
                "Machine.GetInstance().SetState(MachineStateEnum.Working);",
                f"{PREFIX}.Start();\n"
                "            Machine.GetInstance().SetState(MachineStateEnum.Working);",
            )
        else:
            updated = replace_once(
                original,
                "Machine.GetInstance().SetState(MachineStateEnum.Stop);",
                "Machine.GetInstance().SetState(MachineStateEnum.Stop);\n"
                f"            {PREFIX}.Stop();",
            )
        lifecycle.append((node.start_byte, node.end_byte, updated.encode()))
    if len(lifecycle) != 2:
        raise ValueError("无法唯一接入Machine.Start/Stop")
    for start, end, updated in sorted(lifecycle, reverse=True):
        raw = raw[:start] + updated + raw[end:]
    edits[machine] = raw.decode()
    definitions = [
        (
            "DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseCorrectionActionNode.cs",
            "DoWork",
            '"drycycle.s1.vision"',
            {
                "System1Domain.GetInstance().System1MatterVision": (
                    "定位流程（空跑替代识别结果）",
                    "work",
                ),
            },
        ),
        (
            "DispenseSystem/Models/DispenseAction/DispenseBPAction/S1DispenseActionNode.cs",
            "DoWork",
            '"drycycle.s1.dispense"',
            {
                "System1Domain.GetInstance().WaitSingleStep": ("等待单步", "wait"),
                "System1Domain.GetInstance().DispenseActionNodes.PreDispenseAction.DoWork": (
                    "预点胶调用",
                    "work",
                ),
                "Signal.WaitStart": ("等待运行/暂停恢复", "wait"),
                "System1Domain.GetInstance().DispenseController.InterpolationApplication": (
                    "点胶轨迹（不出胶）",
                    "work",
                ),
            },
        ),
        (
            "BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.MoveHelper.cs",
            "PickActionDryRun",
            '"drycycle.pick." + component.CarrierType.ToString()',
            {
                "System2RunTimeProvider.WaitAllowBondPickSignal": ("等待允许取片", "wait"),
                "this.bondModuleController.MoveSafeBondXYZT": ("静态料盒拍照位移动", "work"),
                "this.bondModuleController.MoveSafeBondXY": ("移动至取片中心", "work"),
                "this.bondHeadController.MoveAxisZ": ("移动至空跑高度", "work"),
                "this.bondHeadController.MoveBondZToSafePos": ("抬起至安全位", "work"),
                "Signal.WaitStart": ("等待运行/暂停恢复", "wait"),
            },
        ),
        (
            "BondSystem/Models/ActionNodes/BPActionNode/UpLookCorrectionActionNode.cs",
            "UplookActionDryRun",
            'component.IsTwoPointAdjust ? "drycycle.uplook.two_point"'
            ' : "drycycle.uplook.one_point"',
            {
                "this.bondModuleController.MoveToG0Pos": ("第一点移动", "work"),
                "this.bondModuleController.MoveBondXYToG0Pos": ("第二点移动", "work"),
                "Thread.Sleep": ("拍照配置停留（未执行识别）", "delay"),
            },
        ),
        (
            "BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.MoveHelper.cs",
            "BondActionDryRun",
            '"drycycle.bond"',
            {
                "this.bondModuleController.MoveSafeBondXYZ": ("移动至空跑固晶位", "work"),
                "DelayHelper.Delay": ("放置配置停留", "delay"),
                "this.bondHeadController.MoveBondZToSafePos": ("抬起至安全位", "work"),
            },
        ),
    ]
    for relative, method, branch, calls in definitions:
        text = (source / relative).read_text(encoding="utf-8-sig")
        # Pick方法内先获取component，分支标签必须在该赋值之后。
        if method == "PickActionDryRun":
            text = instrument_method(text, method, calls=calls)
            text = replace_once(
                text,
                "BaseCarrierConfig component = "
                "this.actionNodesService.GetCurrentComponent().component;",
                "BaseCarrierConfig component = "
                "this.actionNodesService.GetCurrentComponent().component;\n"
                f"            {PREFIX}.Branch({branch});",
            )
        else:
            text = instrument_method(text, method, branch=branch, calls=calls)
        edits[relative] = text
    project = "AKRS.ZX2200.csproj"
    text = (source / project).read_text(encoding="utf-8-sig")
    if ET.fromstring(text).tag.rsplit("}", 1)[-1] != "Project" or not text.rstrip().endswith(
        "</Project>"
    ):
        raise ValueError("工程XML根节点不匹配")
    prefix, suffix = text.rsplit("</Project>", 1)
    edits[project] = (
        prefix + '  <ItemGroup>\n    <Compile Include="ArksActionTiming\\Collector.cs" />\n'
        '    <Compile Include="ArksActionTiming\\ZxTiming.cs" />\n  </ItemGroup>\n</Project>'
        + suffix
    )
    return edits


def prepare(source, destination):
    source, destination = source.resolve(), destination.resolve()
    if (
        destination == source
        or destination.is_relative_to(source)
        or source.is_relative_to(destination)
    ):
        raise ValueError("隔离副本不能覆盖、包含或位于输入源码目录内")
    if destination.is_relative_to(ROOT) and not destination.is_relative_to(ROOT / "output"):
        raise ValueError("仓库内的隔离副本只能放在output，trunk和应用代码保持原位")
    if destination.exists():
        raise ValueError("副本目录已存在，请复用/核对已有成果，不覆盖重建")
    if not (source / "AKRS.ZX2200.csproj").is_file():
        raise ValueError("请选择含AKRS.ZX2200.csproj的源码根目录")
    reject_links(source)
    baseline = fingerprint(source)
    edits = build_edits(source)
    dependencies, missing = dependency_projects(source)
    for dependency in dependencies:
        reject_links(dependency)
        if (destination.parent / dependency.name).exists():
            raise ValueError(f"同级工程副本已存在，不覆盖：{dependency.name}")
    revision = hashlib.sha256(json.dumps(baseline, sort_keys=True).encode()).hexdigest()
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*IGNORED))
    patches = []
    for relative, content in edits.items():
        original = (source / relative).read_text(encoding="utf-8-sig")
        (destination / relative).write_text(content, encoding="utf-8-sig")
        patches.extend(
            difflib.unified_diff(
                original.splitlines(True),
                content.splitlines(True),
                fromfile="a/" + relative,
                tofile="b/" + relative,
            )
        )
    timing = destination / "ArksActionTiming"
    timing.mkdir()
    shutil.copyfile(HERE / "Collector.cs", timing / "Collector.cs")
    bridge = (
        (HERE / "ZxTiming.cs.template")
        .read_text(encoding="utf-8")
        .replace("__SOURCE_REVISION__", revision)
    )
    (timing / "ZxTiming.cs").write_text(bridge, encoding="utf-8-sig")
    if fingerprint(source) != baseline:
        raise ValueError("复制期间输入源码发生变化，副本需重新核对")
    dependency_baselines = {}
    for dependency in dependencies:
        dependency_baselines[dependency.name] = fingerprint(dependency)
        shutil.copytree(
            dependency,
            destination.parent / dependency.name,
            ignore=shutil.ignore_patterns(*IGNORED),
        )
        if fingerprint(dependency) != dependency_baselines[dependency.name]:
            raise ValueError(f"复制期间引用工程变化：{dependency.name}")
    report = {
        "source": str(source),
        "destination": str(destination),
        "source_revision": revision,
        "source_unchanged": True,
        "source_files": len(baseline),
        "baseline": baseline,
        "patched_files": list(edits),
        "added_files": ["ArksActionTiming/Collector.cs", "ArksActionTiming/ZxTiming.cs"],
        "device_program_executed": False,
        "dependency_baselines": dependency_baselines,
        "missing_project_references": missing,
    }
    (destination.parent / (destination.name + "-timing-copy.json")).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (destination.parent / (destination.name + "-timing.patch")).write_text(
        "".join(patches), encoding="utf-8"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "trunk/AKRS.ZX2200")
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.source, args.destination)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "destination",
                    "source_revision",
                    "source_unchanged",
                    "source_files",
                    "patched_files",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
