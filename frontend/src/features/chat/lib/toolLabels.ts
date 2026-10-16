const labels: Record<string, string> = {
  read_source: '读取源码',
  read_source_context: '读取方法上下文',
  read_source_batch: '批量读取源码',
  plan_source_checks: '规划源码核查',
  search_project_knowledge: '查阅流程与功能资料',
  search_debug_issues: '检索调试问题',
  read_debug_issue: '读取调试记录',
  search_handover_materials: '检索交接资料',
  read_handover_material: '读取交接资料',
  search_source: '检索源码',
  find_source_files: '查找源码文件',
  csharp_symbols: '分析 C# 符号',
  csharp_relations: '核对 C# 调用关系',
  recall_conversation: '查找历史对话',
  remember: '保存长期记忆',
  compact_conversation: '压缩对话上下文',
  read_file: '读取文件',
  ls: '浏览目录',
  glob: '查找文件',
  grep: '检索文件内容',
  write_todos: '整理待办',
  read_wiki_structure: '读取项目文档目录',
  read_wiki_contents: '读取项目文档',
  ask_question: '查询项目文档',
};
export const toolLabel = (name: string) =>
  labels[name.replace(/^mcp_deepwiki_/, '')] ||
  (name.startsWith('mcp_') ? '查询外部资料' : '执行辅助操作');
