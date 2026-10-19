"""题目、先验核对点与限定来源；随机顺序不改变评分依据。"""

import random

from scripts.verification.answer_style import ORIGINAL

BEFORE = (
    "室温为25.2℃，adv-3采用温度补偿方案进行贴片试验，记录的贴片精度稳定在3μm 3Σ。\n"
    "7月23日14:00左右，精度均值下降约2μm。记录人根据曲线判断，该变化与角度的相关性较大，Y方向受影响有限。"
)
COOL = (
    "7月24日16:30，上一阶段试验结束后暂停贴片，并下调空调温度。\n"
    "至7月25日14:47，室温下降至23.2℃，恢复贴片，持续至7月26日00:50。\n"
    "该阶段记录的精度范围从-4~4μm变化为-4~2μm。"
)
RECORDS = {
    "before": {
        "title": "7月23—24日｜adv-3 温补方案贴片精度试验",
        "text": BEFORE,
        "device": "adv-3",
        "images": 2,
    },
    "cool": {
        "title": "7月25—26日｜adv-3 降温后的贴片精度变化",
        "text": COOL,
        "device": "adv-3",
        "images": 3,
    },
    "blue": {"title": "蓝膜刺穿处理经验", "text": ORIGINAL, "device": "", "images": 1},
    "later": {
        "title": "7月27日｜adv-3 后续阶段",
        "text": "7月27日09:00，adv-3恢复另一阶段的贴片试验，该阶段精度范围为8~10μm。",
        "device": "adv-3",
        "images": 1,
    },
    "other": {
        "title": "7月25—26日｜adv-30 贴片精度试验",
        "text": "7月25日14:47至7月26日00:50，adv-30持续贴片试验，精度范围为11~12μm。",
        "device": "adv-30",
        "images": 1,
    },
}

GLOBAL = "AKRS.ZX2200/CalibSystem/GlobalCalibration/FrmGlobalCalibration.cs"
SYSTEM = "AKRS.ZX2200/SupportFeature/Calibrate/FrmSystem2Calibrate.cs"
PRODUCTION = "AKRS.ZX2200/Main/Controls/Ucmain/MainControls/UcMainSystem.Production.cs"
OPERATE = "AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs"


def cases(seed=20261019):
    rows = [
        (
            "E01",
            "adv-3在7月25日14:47到7月26日00:50的试验结果是什么？展示记录文字和全部原图。",
            ["cool"],
            [
                "23.2℃；-4~4μm变为-4~2μm；恢复贴片时间与截止时间准确",
                "只显示对应记录3张测试原图，不混7月23日、7月27日或adv-30结果",
            ],
            ["8~10", "11~12"],
        ),
        (
            "E02",
            "简短说一下adv-3在7月25日14:47至7月26日00:50的试验结果，只回答结果。",
            ["cool"],
            ["范围-4~4μm变为-4~2μm，不把3μm 3Σ当本阶段指标", "明确不要建议时不追加引导"],
            ["8~10", "11~12"],
        ),
        (
            "E03",
            "adv-3降温后范围从-4~4变成-4~2μm，是不是每个点都提高了2μm？请依据7月25—26日记录判断。",
            ["cool"],
            [
                "范围变化不能推出每个点均提高2μm，不伪造逐点数据",
                "可简短引导比较原始点或同条件数据，不称已经完成比较",
            ],
            ["11~12"],
        ),
        (
            "E04",
            "adv-3在7月23日温补贴片试验有什么经验？包括精度、下午的变化与记录人的判断。",
            ["before"],
            [
                "25.2℃、3μm 3Σ、14:00左右均值下降约2μm",
                "角度相关与Y方向影响有限归属记录人的曲线判断",
            ],
            ["11~12"],
        ),
        (
            "E05",
            "对比adv-3在7月23—24日温补试验和7月25—26日降温试验，讲清两段事实，最后给一个相关的进一步分析方向。",
            ["before", "cool"],
            [
                "两阶段独立分组与引用，不混3Σ和范围的指标口径",
                "3μm 3Σ不直接换算为-4~2μm的改善百分比；引导有据且为建议",
            ],
            ["11~12"],
        ),
        (
            "E06",
            "adv-3在7月28日14:47到7月29日00:50的试验结果是什么？展示对应原图。",
            [],
            [
                "本轮资料没有该时段的已知结果，不能拿相邻日期代替",
                "不附其他阶段原图，不断言整个知识库不存在这条记录",
            ],
            ["11~12", "8~10"],
        ),
        (
            "E07",
            "我要的是adv-3的7月25—26日降温试验，别把adv-30或7月27日的结果算进去，给结果与原图。",
            ["cool"],
            ["设备adv-3、时段7月25—26日，范围-4~4至-4~2μm", "只引用cool记录并展示其3个图片位置"],
            ["11~12", "8~10"],
        ),
        (
            "E08",
            "蓝膜刺穿处理经验",
            ["blue"],
            [
                "0.6×0.45mm、025/050调整为075；20~30g、3mm/s、280~300；216颗无刺穿",
                "保留原因归属，组织清晰，允许有依据的简短引导",
            ],
            ["11~12"],
        ),
        (
            "E09",
            "蓝膜刺穿那次成功的参数组合是什么？请列出来，别给没记录的单位。",
            ["blue"],
            [
                "075、20~30g、3mm/s、280~300；高度未标单位",
                "列表易于逐项查看，不补mm、μm、脉冲等单位",
            ],
            ["高度280~300mm"],
        ),
        (
            "E10",
            "结合蓝膜刺穿处理经验，说说这次调整为什么有参考价值，最后给一句有依据的验证建议。",
            ["blue"],
            [
                "组合试验216颗结果；小顶针应力集中为记录人判断",
                "不新增针径/面积/物理风险等事实，不把组合结果解释为各项缺一不可；引导为建议",
            ],
            [],
        ),
        (
            "E11",
            "蓝膜刺穿只换075顶针就一定能根治吗？换其他尺寸芯片也能直接照用吗？",
            ["blue"],
            [
                "不能从单次组合试验推出单换075独立有效或所有规格适用",
                "也不能反过来宣称075单独无效，各项缺一不可",
            ],
            [],
        ),
        (
            "E12",
            "请逐字提取蓝膜刺穿处理经验的完整原文，不要分析，也不要追加建议。",
            ["blue"],
            ["完整四部分原文与数值逐字保留，附真实引用", "没有引导、解释或对原文因果措辞的改写"],
            [],
        ),
        (
            "E13",
            "蓝膜刺穿记录里的顶针高度280~300是什么单位？",
            ["blue"],
            ["记录未给高度单位，明确无法从资料确定", "不凭习惯补单位或称为坐标刻度"],
            [],
        ),
        (
            "E14",
            "蓝膜刺穿连续216颗无刺穿，能说明已经长期量产稳定了吗？",
            ["blue"],
            [
                "有限连续取放记录不能证明长期量产稳定",
                "保留实际已观察结果，不否定此次结果也不扩大样本",
            ],
            [],
        ),
        (
            "E15",
            "把蓝膜刺穿处理经验和adv-3在7月25—26日的降温试验分别讲清楚，参数不要混在一起，末尾可给一个相关的分析方向。",
            ["blue", "cool"],
            [
                "两主题分组，216颗与蓝膜参数只归蓝膜，23.2℃和-4~2μm只归adv-3",
                "真实引用覆盖两条，排除其他日期设备，延伸引导不过度",
            ],
            ["11~12", "8~10"],
        ),
    ]
    result = [
        {
            "id": key,
            "category": "experience",
            "question": q,
            "expected_records": refs,
            "oracle": oracle,
            "forbidden": forbidden,
        }
        for key, q, refs, oracle, forbidden in rows
    ]
    flows = [
        (
            "F01",
            "我想在做设备标定，给我输出一下标定流程。请结合ZX2200全局标定窗口说明开始、类型选择、停止与保存，按步骤写；未核实的底层动作不要编造。",
            GLOBAL,
            105,
            239,
            [
                "先保存参数；任务为空或完成才新建启动；按SelectedIndex选择不同流程，不是所有标定串行执行",
                "类型1顺序InitData、PreliminaryCompensationX、PreliminaryCompensationY、Mapping2DCalibration(999)",
                "停止isStop=true；SelectedText为Z-XY直接返回，其余保存AxisCompensateProgram；引用源码，避免把停止标志等同硬件已停止",
            ],
        ),
        (
            "F02",
            "我要做吸嘴自动校准，请根据FrmSystem2Calibrate的实际代码输出操作流程，写明准备失败和校准失败怎么处理，底层未读取部分说明范围。",
            SYSTEM,
            126,
            186,
            [
                "PrepareBeforceNozzleAutoCali返回false立即结束",
                "读取Nozzle并保留初值，调用NozzleCaliAssistance，按Success判断弹框",
                "注释掉的模板确认分支不写成当前必经步骤；不宣称执行设备动作",
            ],
        ),
        (
            "F03",
            "根据FrmSystem2Calibrate的BtnCaliEjection_Click，给我顶针校准流程。选择做顶针中心模板后，是否还继续下面的自动校准？",
            SYSTEM,
            280,
            357,
            [
                "PrepareBeforeEjectionAutoCali失败返回；获取料片/顶针配置与初始偏移",
                "选择模板分支后会return，未选模板才调用EjectionConfigCaliAssistance；准确描述结果分支",
                "不把旧注释代码当执行流程，引用对应源文件",
            ],
        ),
        (
            "F04",
            "ZX2200 Production界面点击启动后有哪些步骤？配方确认点取消会继续启动吗？"
            "异常和finally怎么走？请给清楚的流程。",
            PRODUCTION,
            63,
            116,
            [
                "Enabled=false，按配置弹配方确认；Cancel返回且finally恢复Enabled=true",
                "关闭方向盘，退出单步模式，调用Machine.Start；异常Stop并提示；引用源码",
                "发起Start不证明硬件动作已完成",
            ],
        ),
        (
            "F05",
            "请按Machine.Operate.cs的PrepareMachineReadyToStart说明启动前检查流程，尤其是未配置安全门时的分支，不要把注释当执行条件。",
            OPERATE,
            185,
            256,
            [
                "检查AllAxisReset、模组任务关闭、初始化成功；安全门未关且已配置才该分支拒绝",
                "IsWorking时返回false；配置System1才相应MoveToSafePos，System2调用安全位置，未屏蔽顶针模块才AbsoluteMove(0)",
                "CheckOperatingEnvironment失败返回false，不能把绝对移动调用当设备已完成；引用源码",
            ],
        ),
    ]
    result += [
        {
            "id": key,
            "category": "flow",
            "question": q,
            "source": {"path": path, "start": first, "end": last},
            "oracle": oracle,
            "expected_records": [],
            "forbidden": [],
        }
        for key, q, path, first, last, oracle in flows
    ]
    random.Random(seed).shuffle(result)
    return result
