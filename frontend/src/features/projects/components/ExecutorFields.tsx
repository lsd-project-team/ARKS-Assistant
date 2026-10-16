import { Select } from '../../../shared/ui/Select';
import type { VerificationExecutor } from '../types/codeWork';

export function ExecutorFields({
  value,
  onChange,
  disabled,
}: {
  value: VerificationExecutor;
  onChange: (value: VerificationExecutor) => void;
  disabled: boolean;
}) {
  return (
    <fieldset className="code-work-executor" disabled={disabled}>
      <legend>执行环境</legend>
      <label>
        隔离方式
        <Select
          aria-label="验证隔离方式"
          value={value.kind}
          onValueChange={(kind) =>
            onChange({ ...value, kind: kind as VerificationExecutor['kind'] })
          }
        >
          <option value="container">隔离容器（默认）</option>
          <option value="trusted_host">可信宿主（非沙箱，显式选择）</option>
        </Select>
      </label>
      <label>
        执行平台
        <Select
          aria-label="验证执行平台"
          value={value.platform}
          onValueChange={(platform) =>
            onChange({ ...value, platform: platform as VerificationExecutor['platform'] })
          }
        >
          <option value="linux">Linux</option>
          <option value="windows">Windows（Hyper-V 隔离）</option>
        </Select>
      </label>
      {value.kind === 'container' ? (
        <>
          <label>
            固定镜像 digest
            <input
              value={value.image}
              onChange={(event) => onChange({ ...value, image: event.target.value })}
              placeholder="registry/image@sha256:…"
              required
              spellCheck={false}
            />
          </label>
          <label>
            Docker context
            <input
              value={value.context}
              onChange={(event) => onChange({ ...value, context: event.target.value })}
              required
            />
          </label>
          <p className="muted">
            不挂载宿主目录或凭据，固定无网络。Windows 需要具备 Hyper-V 容器能力的独立节点， SSH
            context 与可用磁盘探测；配置后先探测节点及固定镜像。保存配置不代表实际构建已通过。
          </p>
        </>
      ) : (
        <p role="alert" className="error-text">
          可信宿主为非沙箱执行；副本不限制进程系统权限，仅可配置已信任的人工测试程序，不能作为沙箱交付依据。
        </p>
      )}
    </fieldset>
  );
}
