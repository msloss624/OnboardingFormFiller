import type { Transcript } from '../api/client';

interface Props {
  transcript: Transcript;
  checked: boolean;
  onChange: (checked: boolean) => void;
  previousSources?: string[];
}

export default function TranscriptCheckbox({ transcript, checked, onChange, previousSources = [] }: Props) {
  const dateStr = transcript.date ? String(transcript.date).slice(0, 10) : 'N/A';
  const wasPrevious = previousSources.some((s) => s.includes(transcript.title));

  return (
    <label className="flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3 cursor-pointer hover:border-blue-300">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 rounded border-gray-300 text-[#1E4488]"
      />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">{transcript.title}</p>
        <p className="text-sm text-gray-500">
          {dateStr} &middot; {transcript.word_count.toLocaleString()} words
          {wasPrevious && (
            <span className="ml-2 text-xs text-orange-600 font-medium">Previously processed</span>
          )}
        </p>
      </div>
    </label>
  );
}
