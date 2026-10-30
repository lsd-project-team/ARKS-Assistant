# 点胶模板管理与删除复核

日期：2026-09-29。两份完整原始管理窗口主类配合真实 Windows 临时文件、独占删除限制执行，20项断言通过。原产品源码未修改。

## 入口与事件

EpoxyPatternForm.buttonManageRepository_Click（1129行起）创建 ManageRepositoryExDialogBox，设置目录并 ShowDialog。返回后不检查 OK；若当前名称对应的.ep不存在，只清空 currentPatternName。本处理器未清空当前编辑曲线。两份 Designer 合计8处事件绑定：各三个按钮及一个空 Load 处理器；真正枚举位于重写 OnLoad。

## 文件操作与失败顺序

|操作|原始顺序及验证结果|
|---|---|
|基本窗口列举|按*.ep列出名称，不要求缩略图存在；未设置目录、null或空目录参数被拒绝。|
|两个窗口删除所选|先删除.ep，再删除同名.bmp，最后更新列表；均不删除Snapshoot_名称.bmp。锁定背景图时.ep已经消失，但列表仍保留。|
|基本窗口全部删除|逐个删除.ep及.bmp，全部成功后才将DataSource置null；快照及无对应.ep的孤立图保留。锁定.ep使操作异常退出。|
|扩展窗口加载|将Snapshoot_名称.bmp复制到tmp_时间戳.bmp，再构造Bitmap并添加项目；缺失快照导致该模板不显示，尽管.ep仍存在。成功复制产生临时文件。|
|扩展窗口全部删除|先清空项目、释放并清空图像，然后枚举*.ep。删除.ep失败向外抛出，此时界面已清空；背景图和快照删除分别吞掉异常。无对应.ep的孤立图不清理。|
|退出与关闭|Exit先设OK，再调用私有DeleteTemporaryFiles；OnClosed也调用它。单文件删除异常被捕获并继续，下次关闭可重试；目录枚举在catch外，目录消失时可在OK已赋值后抛出。|

PatternFile.ClearTmpFiles与扩展窗口的私有DeleteTemporaryFiles是不同方法，不能将前者未发现调用等同于后者没有执行。

## 图像索引限制

所选删除执行Images.RemoveAt(selectedItem.ImageIndex)，然后Items.Remove。源码没有显式调整剩余项目ImageIndex。List替身下删除首项后，剩余索引1对应仅一个图像；再次删除会在两个文件已经删除后抛出越界。此两项断言仅证明列表模型下的执行顺序，不能证明原生WinForms ImageList/ListView必然出现同样行为，仍需真实控件验收。

## 验证证据与未完成项

- [运行回执](repository-delete-test.json)：20项断言及源码/测试哈希；命令 node scripts/test-repository-delete.cjs。
- [源码绑定审计](repository-delete-audit.json)：原类、Designer、命名辅助方法、宿主入口和报告绑定；命令 node scripts/build-repository-delete-audit.cjs --check。
- 测试仅使用独立GUID临时目录及真实文件锁；控件、Form和图像均为替身。Bitmap替身只读取字节，未证明图像解码、真实位图锁、原生图像索引或模态窗口关闭行为。
- 未读取或删除生产模板，未执行完整产品构建；权限、磁盘耗尽、多文件并发、真实UI以及取消生命周期仍未验收。
- 本增量补齐管理删除的这一轮证据，不覆盖其余曲线算法、鼠标动作、全部82个源文件或设备运行。
