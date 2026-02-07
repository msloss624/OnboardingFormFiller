import type { Deal } from '../api/client';

interface Props {
  deal: Deal;
  onSelect: (deal: Deal) => void;
}

export default function DealCard({ deal, onSelect }: Props) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div>
        <h3 className="font-semibold text-gray-900">{deal.name}</h3>
        <p className="text-sm text-gray-500">
          Stage: {deal.stage}
          {deal.amount && <> &middot; ${deal.amount}</>}
        </p>
      </div>
      <button
        onClick={() => onSelect(deal)}
        className="rounded-md bg-[#1E4488] px-4 py-2 text-sm font-medium text-white hover:bg-[#2a5298]"
      >
        Select
      </button>
    </div>
  );
}
