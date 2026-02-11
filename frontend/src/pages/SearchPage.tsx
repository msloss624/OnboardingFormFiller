import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { searchDeals, listRuns, deleteRun, type Deal, type RunSummary } from '../api/client';
import DealCard from '../components/DealCard';
import Button from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';

export default function SearchPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [deals, setDeals] = useState<Deal[]>([]);
  const [recentRuns, setRecentRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const results = await searchDeals(query);
      setDeals(results);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  }

  function handleSelect(deal: Deal) {
    navigate('/gather', { state: { deal } });
  }

  // Load recent runs on mount
  useState(() => {
    listRuns().then(setRecentRuns).catch(() => {});
  });

  return (
    <div className="space-y-6">
      <h2 className="font-heading text-2xl text-primary">Find a Deal</h2>

      <form onSubmit={handleSearch} className="flex gap-3">
        <Input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search HubSpot deals by company name..."
          className="flex-1"
        />
        <Button type="submit" loading={loading}>
          Search
        </Button>
      </form>

      {deals.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-gray-900">Results</h3>
          {deals.map((deal) => (
            <DealCard key={deal.id} deal={deal} onSelect={handleSelect} />
          ))}
        </div>
      )}

      {searched && deals.length === 0 && (
        <p className="text-gray-500 text-sm">No deals found. Try a different search term.</p>
      )}

      {recentRuns.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-gray-900">Recent Runs</h3>
          <Card className="p-0 divide-y divide-gray-100">
            {recentRuns.slice(0, 10).map((run) => (
              <div key={run.id} className="flex items-center justify-between px-5 py-3">
                <div>
                  <p className="font-medium text-gray-900">{run.deal_name}</p>
                  <p className="text-xs text-gray-500">
                    {run.status} &middot;{' '}
                    {run.created_at && new Date(run.created_at).toLocaleDateString()}
                    {run.stats && <> &middot; {run.stats.completion_pct}% complete</>}
                  </p>
                </div>
                <div className="flex gap-3">
                  {run.status === 'completed' && (
                    <button
                      onClick={() => navigate(`/review/${run.id}`)}
                      className="text-sm text-primary hover:underline"
                    >
                      View
                    </button>
                  )}
                  <button
                    onClick={async () => {
                      if (!confirm('Delete this run?')) return;
                      await deleteRun(run.id);
                      setRecentRuns((prev) => prev.filter((r) => r.id !== run.id));
                    }}
                    className="text-sm text-red-400 hover:text-red-600"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </Card>
        </div>
      )}
    </div>
  );
}
