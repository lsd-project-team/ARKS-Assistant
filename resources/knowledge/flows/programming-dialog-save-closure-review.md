# 编程页面间接对话框与保存闭环

记录时间：2026-10-07T08:51:09.423Z。固定核对 5 个当前由非接口页面或通用仓库窗体创建的模态源文件。

| ID | 文件 | 源角色 | 直接 Save 数 | DialogResult 赋值 | 仓库调用 | 上层保存归属 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| transport-add-object | `trunk/AKRS.ZX2200/TransportUnitSystem/Controls/TransportUnitEdit/FrmAddObject.cs` | modal-add | 0 | 2 | 0 | FrmTransportUnitEdit.BtAdd_Click |
| transport-object-copy | `trunk/AKRS.ZX2200/TransportUnitSystem/Controls/TransportUnitEdit/FrmObjectCopy.cs` | modal-copy | 0 | 2 | 0 | FrmTransportUnitEdit.BtCopy_Click |
| epoxy-create | `trunk/AKRS.ZX2200/DispenseSystem/Controls/Setting/EpoxyApplication/FrmNewCreateEpoxyApplication.cs` | modal-create-and-save | 1 | 2 | 0 | UcAddEpoxyApplication.BtnAdd_Click |
| postbond-create | `trunk/AKRS.ZX2200/BondSystem/Controls/Setting/PostBond/FrmNewCreatePostBond.cs` | modal-create-and-save | 2 | 2 | 0 | UcAddPostBond.BtnAdd_Click |
| generic-repository | `trunk/AKRS.ZX2200/Infrastructure/Controls/Currency/FrmRepository.cs` | generic-repository | 2 | 1 | 5 | UcAddEpoxyApplication.BtEpoxyApplicationRepository_Click / UcAddPostBond.BtPostBondInspectionRepository_Click |

关键闭环：`FrmAddObject` 和 `FrmObjectCopy` 只构造输出对象，由 `FrmTransportUnitEdit` 在返回 OK 后保存；两个新建对话框在确认按钮内直接把对象加入仓库并保存，然后由父页面刷新；`FrmRepository<T>` 的显式保存按钮和 FormClosed 都保存仓库，新增/删除先改内存，提取/双击通过委托触发父页面刷新。

机器结果见 [programming-dialog-save-closure.json](programming-dialog-save-closure.json)。这份静态闭环补足了对话框内部保存和委托边界，不能替代真实 UI、Singleton 文件、异常恢复或设备验收。
