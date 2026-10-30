import type { Message, Run } from '../../../shared/types/api';

export type ReplyVersion = { message: Message; run: Run };

export function groupReplies(messages: Message[], runs: Run[]) {
  const replyRuns = new Map(
    runs.filter((run) => run.response_message_id).map((run) => [run.response_message_id, run]),
  );
  const versionGroups = new Map<string, ReplyVersion[]>();
  for (const message of messages) {
    const run = replyRuns.get(message.id);
    if (!run) continue;
    const versions = versionGroups.get(run.message_id) || [];
    versions.push({ message, run });
    versionGroups.set(run.message_id, versions);
  }
  return { replyRuns, versionGroups };
}
