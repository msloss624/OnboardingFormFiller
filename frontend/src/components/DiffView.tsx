import ConfidenceBadge from './ConfidenceBadge';
import type { Answer } from '../api/client';

interface Props {
  baseline: Answer[];
  current: Answer[];
}

type ChangeType = 'new' | 'upgraded' | 'conflict' | 'unchanged';

function classifyChange(base: Answer | undefined, curr: Answer): ChangeType {
  if (!base || base.confidence === 'missing') {
    return curr.confidence !== 'missing' ? 'new' : 'unchanged';
  }
  if (curr.confidence === 'missing') return 'unchanged';
  if (curr.answer !== base.answer) {
    const confOrder = { high: 3, medium: 2, low: 1, missing: 0 };
    if (confOrder[curr.confidence] > confOrder[base.confidence]) return 'upgraded';
    return 'conflict';
  }
  return 'unchanged';
}

const changeStyles: Record<ChangeType, string> = {
  new: 'border-l-4 border-l-green-500 bg-green-50',
  upgraded: 'border-l-4 border-l-blue-500 bg-blue-50',
  conflict: 'border-l-4 border-l-yellow-500 bg-yellow-50',
  unchanged: '',
};

const changeLabels: Record<ChangeType, string> = {
  new: 'New',
  upgraded: 'Upgraded',
  conflict: 'Changed',
  unchanged: '',
};

export default function DiffView({ baseline, current }: Props) {
  const baseMap = Object.fromEntries(baseline.map((a) => [a.field_key, a]));
  const changes = current
    .map((curr) => ({
      curr,
      base: baseMap[curr.field_key],
      type: classifyChange(baseMap[curr.field_key], curr),
    }))
    .filter((c) => c.type !== 'unchanged');

  if (changes.length === 0) {
    return <p className="text-gray-500 text-sm py-4">No changes from baseline.</p>;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-gray-600 mb-2">
        {changes.length} field{changes.length !== 1 ? 's' : ''} changed
      </p>
      {changes.map(({ curr, base, type }) => (
        <div key={curr.field_key} className={`rounded-md p-3 ${changeStyles[type]}`}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase text-gray-600">{changeLabels[type]}</span>
            <span className="text-sm font-medium">{curr.question}</span>
          </div>
          {base && base.confidence !== 'missing' && (
            <p className="text-xs text-gray-500">
              Was: <ConfidenceBadge confidence={base.confidence} /> {base.answer || '—'}
            </p>
          )}
          <p className="text-sm mt-1">
            Now: <ConfidenceBadge confidence={curr.confidence} /> {curr.answer || '—'}
          </p>
        </div>
      ))}
    </div>
  );
}
