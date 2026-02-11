import type { Deal } from '../api/client';
import { Card } from './ui/Card';
import Button from './ui/Button';

interface Props {
  deal: Deal;
  onSelect: (deal: Deal) => void;
}

export default function DealCard({ deal, onSelect }: Props) {
  return (
    <Card className="flex items-center justify-between border-l-4 border-l-accent">
      <div>
        <h3 className="font-semibold text-gray-900">{deal.name}</h3>
        <p className="text-sm text-gray-500">
          Stage: {deal.stage}
          {deal.amount && <> &middot; ${deal.amount}</>}
        </p>
      </div>
      <Button size="sm" onClick={() => onSelect(deal)}>
        Select
      </Button>
    </Card>
  );
}
