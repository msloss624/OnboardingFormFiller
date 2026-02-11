const styles: Record<string, string> = {
  high: 'bg-green-100 text-green-800',
  medium: 'bg-bw-orange/10 text-bw-orange-dark',
  low: 'bg-red-100 text-red-800',
  missing: 'bg-gray-100 text-gray-500',
};

export default function ConfidenceBadge({ confidence }: { confidence: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[confidence] || styles.missing}`}
    >
      {confidence}
    </span>
  );
}
