# Main PR 清单、流程初始化与配方复制复核

本轮继续展开 `ReLoadRecipe` 的 PR 路径：入口从 `System2CommonService.GetCurrentRecipePREntityNameList()` 取得当前配方名称，逐项从 `VisionEntityRepository` 查找。找不到的实体只记录日志并继续；找到后调用 `BaseAlg.InitVmProcedure()`。该方法在锁内优先读取产品目录下的同名 `.prc`，不存在时退回 `AlgFlowTemplates` 中按算法类型命名的模板，随后赋值流程名、参数和两个图像工具。异常被记录后吞掉，没有成功标志或异常返回给 `ReLoadRecipe`。循环结束后主流程仍会设置 `PrInitSuccess=true`。

`DispenseRunTimeProvider.LoadDispensePr()` 当前方法体在去除注释后没有可执行语句。原本的点胶 PR 克隆、硬件替换和缓存列表代码全部被注释，因此 `ReLoadRecipe` 对它的调用不会加载点胶模板。

`GetCurrentRecipePREntityNameList()` 汇总晶圆载台、顶针、焊后检测、吸嘴、异形配置或标准 TU/基板/基岛/焊点定位配置，最后无条件追加 `IPTCenterCircle`。异常提示后执行 `throw ex`，会重置异常堆栈边界。

`CopyOldRecipePR` 会临时切换到旧配方目录读取配置，按异形配置或固定名称集合筛选 PR，再恢复默认路径；名称筛选使用精确相等匹配，随后调用 `PREntity.CopyPREntity` 并保存仓库。复制方法先复制 `.prc` 文件，再克隆实体、初始化流程、改名并加入仓库；复制结果和底层失败没有被上层检查。

机器审计：[main-pr-reload-audit.json](main-pr-reload-audit.json)。本轮只做源码和方法体证据核对，没有调用真实 VM、PR 仓库、配方文件或设备。
