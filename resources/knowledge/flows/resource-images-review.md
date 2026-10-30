# 资源图片解码检查

对[RESX引用清单](resx-references.json)中的134条引用进行检查，全部通过；每项输入文件哈希先与清单比对，结果见[逐项回执](resource-images-test.json)。

- 111条Bitmap引用：使用本机内置.NET的System.Drawing打开图片，再绘制到新的同尺寸内存Bitmap，记录宽、高和像素格式。全部成功释放图像与Graphics对象，没有写回文件。
- 23条DevExpress SvgImage引用：禁用DTD和外部XML解析器后读取，验证svg根节点及标准命名空间。未调用DevExpress SVG解析/渲染器，因此仅计XML结构通过。

复现：`node scripts/test-resource-images.cjs`。已纳入统一回归。

这里的数量是引用条数，不保证目标文件彼此唯一。图片解码及绘制成功不证明资源命名、嵌入产物、视觉效果、DPI、控件绑定或目标.NET Framework环境正确；这些仍需要产品构建与UI验收。嵌入在RESX中的序列化对象也不在本轮解码范围内。
