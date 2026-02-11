import { useState } from 'react';
import ConfidenceBadge from './ConfidenceBadge';
import { Textarea } from './ui/Input';
import Spinner from './ui/Spinner';
import type { Answer } from '../api/client';

interface Props {
  answer: Answer;
  onChange: (updated: Answer) => void;
  onRetry?: (fieldKey: string) => void;
  retrying?: boolean;
}

export default function AnswerEditor({ answer, onChange, onRetry, retrying }: Props) {
  const [value, setValue] = useState(answer.answer || '');
  const [hovered, setHovered] = useState(false);

  function handleBlur() {
    if (value !== (answer.answer || '')) {
      onChange({
        ...answer,
        answer: value || null,
        confidence: value.trim() ? 'high' : 'missing',
        source: value.trim() ? 'Manual edit' : '',
      });
    }
  }

  const showRetry = answer.confidence === 'missing' || answer.confidence === 'low' || hovered;

  return (
    <div
      className="border-b border-gray-100 py-3"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="flex items-center gap-2 mb-1">
        <ConfidenceBadge confidence={answer.confidence} />
        <span className="font-medium text-sm text-gray-900 flex-1">{answer.question}</span>
        {onRetry && showRetry && (
          <button
            onClick={() => onRetry(answer.field_key)}
            disabled={retrying}
            title="Re-extract this field"
            className="flex items-center gap-1 rounded px-2 py-0.5 text-xs text-gray-500 hover:bg-gray-100 hover:text-primary disabled:opacity-50"
          >
            {retrying ? (
              <Spinner size="sm" className="h-3 w-3" />
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
                <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H4.598a.75.75 0 00-.75.75v3.634a.75.75 0 001.5 0v-2.033l.312.312a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm-11.073-3.85a.75.75 0 00-1.449-.39A7 7 0 0014.502 10.32l.312.311v-2.033a.75.75 0 011.5 0v3.634a.75.75 0 01-.75.75h-3.634a.75.75 0 010-1.5h2.433l-.312-.312a5.5 5.5 0 00-9.201-2.466.75.75 0 01-1.06-1.06 7 7 0 019.201 2.466" clipRule="evenodd" />
              </svg>
            )}
            {retrying ? 'Retrying...' : 'Retry'}
          </button>
        )}
      </div>
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={handleBlur}
        rows={2}
      />
      {answer.source && (
        <p className="text-xs text-gray-400 mt-0.5">Source: {answer.source}</p>
      )}
    </div>
  );
}
