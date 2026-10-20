"""可选展示协议，与既有文本消息共存。"""

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StringConstraints,
    model_validator,
)

Identifier = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9_-]{1,80}$")]
Title = Annotated[str, StringConstraints(strict=True, max_length=300)]
Text = Annotated[str, StringConstraints(strict=True, max_length=20000)]
Description = Annotated[str, StringConstraints(strict=True, max_length=4000)]
Line = Annotated[int, Field(strict=True, ge=1, le=10000000)]


class ContentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @model_validator(mode="before")
    @classmethod
    def no_explicit_null(cls, value):
        if isinstance(value, dict) and any(item is None for item in value.values()):
            raise ValueError("未知可选字段应省略，不能使用 null")
        return value


class SourcePointer(ContentModel):
    path: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=1024)]
    start_line: Line
    end_line: Line | None = None
    version: Annotated[str, StringConstraints(strict=True, max_length=128)] | None = None
    source_workspace_id: Identifier | None = None

    @model_validator(mode="after")
    def valid_location(self):
        if (
            any(char in self.path for char in "\\:")
            or any(ord(char) < 32 or ord(char) == 127 for char in self.path)
            or any(part in {"", ".", ".."} for part in self.path.split("/"))
            or (self.end_line is not None and self.end_line < self.start_line)
        ):
            raise ValueError("源码路径或范围无效")
        return self


class BlockBase(ContentModel):
    id: Identifier


class TextBlock(BlockBase):
    type: Literal["text"]
    content: Text


class OverviewItem(ContentModel):
    id: Identifier
    title: Title
    description: Description
    icon: Literal["code", "layers", "settings", "workflow"] | None = None
    status: Title | None = None
    source: SourcePointer | None = None


class OverviewBlock(BlockBase):
    type: Literal["overview_grid"]
    title: Title | None = None
    items: Annotated[list[OverviewItem], Field(max_length=64)]


class Step(ContentModel):
    id: Identifier
    title: Title
    description: Description
    details: Text | None = None
    sources: Annotated[list[SourcePointer], Field(max_length=16)] = Field(default_factory=list)


class StepFlowBlock(BlockBase):
    type: Literal["step_flow"]
    title: Title | None = None
    description: Description | None = None
    steps: Annotated[list[Step], Field(max_length=128)]


class SourceBlock(BlockBase):
    type: Literal["source_reference"]
    sources: Annotated[list[SourcePointer], Field(max_length=64)]


class CodeBlock(BlockBase):
    type: Literal["code"]
    content: Annotated[str, StringConstraints(strict=True, max_length=60000)]
    language: Annotated[str, StringConstraints(strict=True, pattern=r"^[\w#+.-]{1,40}$")] | None = (
        None
    )
    filename: Annotated[str, StringConstraints(strict=True, max_length=1024)] | None = None
    start_line: Line | None = None
    source: SourcePointer | None = None


class Column(ContentModel):
    id: Identifier
    label: Title
    align: Literal["left", "right", "center"] | None = None


class Row(ContentModel):
    id: Identifier
    cells: Annotated[list[Description | StrictInt | StrictFloat | None], Field(max_length=32)]


class TableBlock(BlockBase):
    type: Literal["table"]
    title: Title | None = None
    columns: Annotated[list[Column], Field(min_length=1, max_length=32)]
    rows: Annotated[list[Row], Field(max_length=200)]


class DiagramNode(ContentModel):
    id: Identifier
    label: Title
    description: Description | None = None


class DiagramEdge(ContentModel):
    from_: Identifier = Field(alias="from")
    to: Identifier
    label: Title | None = None


class DiagramBlock(BlockBase):
    type: Literal["diagram"]
    title: Title
    description: Description | None = None
    layout: Literal["vertical", "horizontal"] | None = None
    nodes: Annotated[list[DiagramNode], Field(min_length=1, max_length=60)]
    edges: Annotated[list[DiagramEdge], Field(max_length=120)]


class CollapsibleBlock(BlockBase):
    type: Literal["collapsible"]
    title: Title
    default_open: bool = False
    blocks: Annotated[list["ContentBlock"], Field(max_length=128)]


ContentBlock = Annotated[
    TextBlock
    | OverviewBlock
    | StepFlowBlock
    | SourceBlock
    | CodeBlock
    | TableBlock
    | DiagramBlock
    | CollapsibleBlock,
    Field(discriminator="type"),
]
CollapsibleBlock.model_rebuild()


def unique(rows):
    if len({row.id for row in rows}) != len(rows):
        raise ValueError("ID 重复")


class RichDocument(ContentModel):
    version: Literal[1]
    blocks: Annotated[list[ContentBlock], Field(max_length=128)]

    @model_validator(mode="before")
    @classmethod
    def integer_version(cls, value):
        if isinstance(value, dict) and type(value.get("version")) is not int:
            raise ValueError("协议版本必须是整数")
        return value

    @model_validator(mode="after")
    def valid_structure(self):
        identifiers = set()

        def visit(blocks, depth=0):
            if depth > 4:
                raise ValueError("内容嵌套过深")
            for block in blocks:
                if block.id in identifiers:
                    raise ValueError("内容块 ID 重复")
                identifiers.add(block.id)
                if len(identifiers) > 128:
                    raise ValueError("内容块过多")
                if isinstance(block, OverviewBlock):
                    unique(block.items)
                elif isinstance(block, StepFlowBlock):
                    unique(block.steps)
                elif isinstance(block, TableBlock):
                    unique(block.columns)
                    unique(block.rows)
                    if any(len(row.cells) != len(block.columns) for row in block.rows):
                        raise ValueError("表格列数不一致")
                elif isinstance(block, DiagramBlock):
                    unique(block.nodes)
                    nodes = {node.id for node in block.nodes}
                    if any(edge.from_ not in nodes or edge.to not in nodes for edge in block.edges):
                        raise ValueError("图形连接指向未知节点")
                elif isinstance(block, CollapsibleBlock):
                    visit(block.blocks, depth + 1)

        visit(self.blocks)
        return self
