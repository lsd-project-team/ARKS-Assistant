"""首批五项固定身份；显示名称不能替代动作代码。"""

CATALOG = [
    {
        "code": "s1.bond_position_vision",
        "name": "S1 焊点定位",
        "station": "S1",
        "class_name": "S1DispenseCorrectionActionNode",
        "source_file": "AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/"
        "S1DispenseCorrectionActionNode.cs",
    },
    {
        "code": "s1.dispense",
        "name": "S1 点胶",
        "station": "S1",
        "class_name": "S1DispenseActionNode",
        "source_file": "AKRS.ZX2200/DispenseSystem/Models/DispenseAction/DispenseBPAction/"
        "S1DispenseActionNode.cs",
    },
    {
        "code": "s2.pick",
        "name": "S2 取片",
        "station": "S2",
        "class_name": "PickActionNode",
        "source_file": "AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/PickActionNode.cs",
    },
    {
        "code": "s2.uplook",
        "name": "S2 上视纠偏",
        "station": "S2",
        "class_name": "UpLookCorrectionActionNode",
        "source_file": "AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/"
        "UpLookCorrectionActionNode.cs",
    },
    {
        "code": "s2.bond",
        "name": "S2 固晶",
        "station": "S2",
        "class_name": "BondActionNode",
        "source_file": "AKRS.ZX2200/BondSystem/Models/ActionNodes/BPActionNode/BondActionNode.cs",
    },
]
BY_CODE = {row["code"]: row for row in CATALOG}
