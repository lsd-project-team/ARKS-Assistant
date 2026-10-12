import * as SelectPrimitive from '@radix-ui/react-select';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';
import { useWorkspace } from '../lib/store';
import { FileIcon } from './FileIcon';

export function OpenFilesMenu() {
  const { paths, activePath, previewPath, openFile } = useWorkspace();
  if (!paths.length) return null;
  return (
    <SelectPrimitive.Root
      value={activePath}
      onValueChange={(path) =>
        openFile(path, undefined, path === previewPath ? 'preview' : 'pinned')
      }
    >
      <SelectPrimitive.Trigger
        className="file-tab-button"
        aria-label="全部已打开文件"
        title={`全部已打开文件（${paths.length}）`}
      >
        <SelectPrimitive.Icon>
          <ChevronDown size={15} />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          className="ui-select-content open-files-list"
          position="popper"
          sideOffset={6}
          align="end"
          collisionPadding={12}
          aria-label="全部已打开文件"
        >
          <SelectPrimitive.ScrollUpButton className="ui-select-scroll">
            <ChevronUp size={14} />
          </SelectPrimitive.ScrollUpButton>
          <SelectPrimitive.Viewport className="ui-select-viewport">
            <SelectPrimitive.Group>
              <SelectPrimitive.Label className="open-files-heading">
                已打开 {paths.length} 个文件
              </SelectPrimitive.Label>
              {paths.map((path) => (
                <SelectPrimitive.Item
                  className="ui-select-item open-file-item"
                  key={path}
                  value={path}
                  textValue={path.split('/').at(-1) || path}
                  title={path}
                >
                  <FileIcon name={path} />
                  <div className="open-file-label">
                    <SelectPrimitive.ItemText>
                      <strong>{path.split('/').at(-1)}</strong>
                      <small>
                        {path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : 'trunk'}
                      </small>
                    </SelectPrimitive.ItemText>
                  </div>
                  <SelectPrimitive.ItemIndicator className="ui-select-indicator">
                    <Check size={14} />
                  </SelectPrimitive.ItemIndicator>
                </SelectPrimitive.Item>
              ))}
            </SelectPrimitive.Group>
          </SelectPrimitive.Viewport>
          <SelectPrimitive.ScrollDownButton className="ui-select-scroll">
            <ChevronDown size={14} />
          </SelectPrimitive.ScrollDownButton>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}
