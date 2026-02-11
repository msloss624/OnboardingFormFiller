import type { Transcript } from '../api/client';

interface Props {
  transcript: Transcript;
  checked: boolean;
  onChange: (checked: boolean) => void;
  previousSources?: string[];
}

export default function TranscriptCheckbox({ transcript, checked, onChange, previousSources = [] }: Props) {
  let dateStr = 'N/A';
  if (transcript.date) {
    const d = typeof transcript.date === 'number'
      ? new Date(transcript.date)
      : new Date(transcript.date);
    if (!isNaN(d.getTime())) {
      dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
  }
  const wasPrevious = previousSources.some((s) => s.includes(transcript.title));

  return (
    <label className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3 cursor-pointer hover:border-primary transition-colors">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 rounded border-gray-300 text-primary accent-primary"
      />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">{transcript.title}</p>
        <p className="text-sm text-gray-500">
          {dateStr} &middot; {transcript.word_count.toLocaleString()} words
          {wasPrevious && (
            <span className="ml-2 text-xs text-accent-dark font-medium">Previously processed</span>
          )}
        </p>
      </div>
    </label>
  );
}
