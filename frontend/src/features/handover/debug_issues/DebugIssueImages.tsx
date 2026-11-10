import { useState } from 'react';
import { RotateCcw, RotateCw } from 'lucide-react';
import type { Client } from '../shared/client';
import type { HandoverRecord } from '../shared/types';
import { ErrorText } from '../../../shared/ui/ui';
import { debugImages, debugImageUrl } from './debugImages';
import './debug-images.css';

export function DebugIssueImages({
  row,
  client,
  editable = false,
  onChanged,
}: {
  row: HandoverRecord;
  client?: Client;
  editable?: boolean;
  onChanged?: () => void;
}) {
  const images = debugImages(row.payload);
  const [rotations, setRotations] = useState<Record<number, number>>(() =>
    Object.fromEntries(images.map((image, index) => [index, image.rotation || 0])),
  );
  const [busy, setBusy] = useState<number>();
  const [error, setError] = useState<unknown>();

  async function rotate(index: number, delta: number) {
    if (!client) return;
    const current = rotations[index] || 0;
    const rotation = ((current + delta + 360) % 360) as 0 | 90 | 180 | 270;
    setBusy(index);
    setError(undefined);
    try {
      await client.rotateDebugImage<HandoverRecord>(row.id, row.version, index, rotation);
      setRotations((value) => ({ ...value, [index]: rotation }));
      onChanged?.();
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(undefined);
    }
  }

  return (
    <div className="debug-original-images">
      <ErrorText error={error} reveal />
      {images.map((image, index) => (
        <figure key={`${image.id}:${index}`}>
          <div className="debug-image-toolbar">
            <figcaption>
              原图 {index + 1}
              {image.recorded_at && ` · ${image.recorded_at}`}
            </figcaption>
            {editable && client && (
              <div className="debug-image-actions" aria-label={`调整原图 ${index + 1} 方向`}>
                <button
                  type="button"
                  title="向左旋转 90°"
                  aria-label={`原图 ${index + 1} 向左旋转 90°`}
                  disabled={busy === index}
                  onClick={() => void rotate(index, -90)}
                >
                  <RotateCcw size={14} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  title="向右旋转 90°"
                  aria-label={`原图 ${index + 1} 向右旋转 90°`}
                  disabled={busy === index}
                  onClick={() => void rotate(index, 90)}
                >
                  <RotateCw size={14} aria-hidden="true" />
                </button>
              </div>
            )}
          </div>
          <a href={debugImageUrl(row.id, row.version, index)} target="_blank" rel="noreferrer">
            <img
              src={debugImageUrl(row.id, row.version, index)}
              alt={`${row.title} · 原图 ${index + 1}`}
              loading="lazy"
            />
          </a>
        </figure>
      ))}
    </div>
  );
}
