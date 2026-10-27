// 制作清单与已复核节点逐项对应；未审核的旧专题保持 pending，不能用已有图数推定完成。
export function validateAtlasCoverage({ plan, coverage, guides }) {
  const expected = [...plan.matchAll(/^#### (\d{2}) (.+)$|^- (\d{2}\.\d{2}) (.+)$/gm)];
  const plannedTopics = expected
    .filter((match) => match[1])
    .map((match) => [match[1], match[2].trim()]);
  const plannedItems = expected
    .filter((match) => match[3])
    .map((match) => [match[3], match[4].trim()]);
  const topics = coverage.topics.map((topic) => [topic.id, topic.title]);
  const items = coverage.topics.flatMap((topic) =>
    topic.requirements.map((item) => [item.id, item.text]),
  );
  if (
    JSON.stringify(topics) !== JSON.stringify(plannedTopics) ||
    JSON.stringify(items) !== JSON.stringify(plannedItems)
  )
    throw new Error('规划条目不一致：必须保留原清单的全部专题、编号与内容');

  let reviewed = 0;
  for (const topic of coverage.topics) {
    for (const requirement of topic.requirements) {
      if (!['pending', 'reviewed'].includes(requirement.status))
        throw new Error(`复核状态无效：${requirement.id}`);
      if (requirement.status === 'pending') {
        if (requirement.bindings.length)
          throw new Error(`未复核项不应声明已完成绑定：${requirement.id}`);
        continue;
      }
      if (!requirement.bindings.length) throw new Error(`已复核项缺少阅读节点：${requirement.id}`);
      for (const binding of requirement.bindings) {
        const guide = guides.find((guide) => guide.topic === binding.topic);
        const flow = guide?.flows.find((flow) => flow.id === binding.flow);
        if (
          !flow ||
          !binding.steps.length ||
          !binding.steps.every((id) =>
            flow.steps.some((step) => step.id === id && step.refs.length),
          )
        )
          throw new Error(`已复核项的阅读绑定无效：${requirement.id}`);
      }
      reviewed++;
    }
  }
  return {
    topics: topics.length,
    requirements: items.length,
    reviewed,
    pending: items.length - reviewed,
  };
}
