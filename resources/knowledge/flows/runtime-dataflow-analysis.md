# ZX2200 运行数据与持久化流

## 配置输入

`ZX2200PathConfig` 将产品、制程、输送、点胶、固晶、晶圆和统计配置映射到 RecipeDirPath 下的 JSON 文件。生产启动时，`Machine` 和各生产域读取这些 Singleton 配置并生成动作消息；编辑操作也会通过各 Repository 或 Domain 的 `Save()` 写回文件。

## 运行数据

S1、S2、Transport 和 Wafer 工作线程在动作执行、报警、步骤完成和载具交接时产生状态与统计实体。视觉服务返回 `BaseAlgResult` / `MatchResult`，并可把 Bitmap 放入 `BitmapBlockingCollection`。这些队列是进程内缓冲，不是持久化队列。

## 异步持久化

`StatisticsService.DbEntityBlockingCollection` 是容量 500 的 `BlockingCollection<object>`。`SaveEntity` 去重相同的上一条消息后加入 `OperateLogEntity`；后台 `SaveEntityToDb` 按实体类型调用 `DBService.Insert`，涵盖操作、缺陷、参数变化和焊点位置日志。查询方法直接执行 SQL，例如 MTBA 和报警时长统计。

`VisionService.SaveVisionImage` 创建目录并将 Bitmap 放入队列，`SaveBitmap` 后台线程写 BMP 并释放 Bitmap。图像写入与动作线程解耦，源码没有把图片落盘成功作为动作完成条件。

`Machine.DataSave` 顺序保存晶圆、Bond、Transport、S1、硬件、视觉和 RTU 等多类配置；异常只记录并弹窗，源码没有提供跨文件事务或回滚。

## 证据

- `SupportFeature/Statistics/StatisticsService.cs:35–125`：队列、去重、后台线程和数据库写入。
- `Infrastructure/Service/VisionService.cs:182–229,337–351`：图片入队与 BMP 后台保存。
- `Main/Machine/MachineSupport/Machine.cs:352–403`：集中 DataSave。
- `Infrastructure/Models/Path/ZX2200PathConfig.cs:35–313`：数据文件路径。

对应图：[runtime-dataflow.html](runtime-dataflow.html)，源文件：[runtime-dataflow.archify.json](runtime-dataflow.archify.json)。
