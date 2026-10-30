# 点胶背景图交互复核

2026-09-29。39项隔离检查通过；40个完整原始源码文件及23个精确提取的方法/属性。使用真实Bitmap和System.Drawing.Matrix，鼠标事件、控件、坐标映射和位图重建由测试宿主提供。生产源码未修改。

## 已确认行为

- BackgroundImageInfo复制矩阵数组但共享Bitmap；MatrixElements getter直接暴露内部数组。短数组setter先写入部分元素再抛错，长数组仅取前六项。
- 控件BackgroundImageInfo getter隔离矩阵但仍共享Bitmap。实际矩阵使用Append顺序，旋转也会旋转已有平移，旋转中心采用coordinateSystemOrigin。没有图像时仍改变矩阵，但不重建或重绘。
- 位图重建失败发生在矩阵提交之后；属性赋值失败也可能保留新矩阵。重建替身仅验证调用顺序，不验证实际渲染。
- “重置角度”和“重置位置”两个原菜单方法都调用Matrix.Reset，均清除整个变换，再切换None。重建异常时矩阵已归零，但模式未退出。
- 平移处理器接受任意按钮及图像外位置的按下；Move对逻辑Y增量取负，而Up直接加正Y增量。Shift/Control轴约束仅对Move生效，Up不应用约束；组合修饰键不锁定轴。
- Move在宿主变换前更新前一个鼠标点：重建失败后同位置重试增量为零。Up在宿主变换成功后才清除holding：失败重试可能重复应用已提交增量。
- 旋转接受右键按下及无按键Move；角度由像素Y变化、逻辑X正负和Shift单独按下决定。释放坐标不补算角度。
- 平移SetMode清除holding；旋转SetMode仅重置累计显示角度，不清除holding和前一次鼠标点。隔离重入后可继续旧拖动。
- 两个背景动作在无图像时SetMode均抛出NullReferenceException。实际UI是否允许到达该状态仍需验收。

## 验证与限制

运行`node scripts/test-background-edit.cjs`，回执为`background-edit-test.json`；`build-background-edit-audit.cjs --check`核对原文件、提取片段、脚本及报告哈希。

坐标转换使用明确的测试映射，未运行真实WinForms消息循环、完整控件的RebuildBackgroundBitmap、DevExpress窗口、SXml文件往返、产品构建或硬件。上述现象是原处理器/方法在给定输入下的证据，不能直接推断所有真实界面触发路径。29个模块组仍保持部分复核。
