import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { searchDeals, listRuns, deleteRun, type Deal, type RunSummary } from '../api/client';
import DealCard from '../components/DealCard';

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
      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search HubSpot deals by company name..."
          className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-[#1E4488] focus:ring-1 focus:ring-[#1E4488] focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-[#1E4488] px-6 py-2.5 text-sm font-medium text-white hover:bg-[#2a5298] disabled:opacity-50"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {deals.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-900">Results</h2>
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
          <h2 className="text-lg font-semibold text-gray-900">Recent Runs</h2>
          <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
            {recentRuns.slice(0, 10).map((run) => (
              <div key={run.id} className="flex items-center justify-between px-4 py-3">
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
                      className="text-sm text-[#1E4488] hover:underline"
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
          </div>
        </div>
      )}
    </div>
  );
}
