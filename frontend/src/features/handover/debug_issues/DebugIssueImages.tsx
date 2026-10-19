import type { HandoverRecord } from '../shared/types';
import { debugImages, debugImageUrl } from './debugImages';
import './debug-images.css';

export function DebugIssueImages({ row }: { row: HandoverRecord }) {
  return (
    <div className="debug-original-images">
      {debugImages(row.payload).map((image, index) => (
        <figure key={`${image.id}:${index}`}>
          <figcaption>
            原图 {index + 1}
            {image.recorded_at && ` · ${image.recorded_at}`}
          </figcaption>
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
