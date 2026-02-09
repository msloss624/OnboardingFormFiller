import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { listRuns, downloadExcel, deleteRun, type RunSummary } from '../api/client';

export default function HistoryPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const dealId = searchParams.get('deal_id') || undefined;
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRuns(dealId)
      .then(setRuns)
      .finally(() => setLoading(false));
  }, [dealId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#1E4488] border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-900">
          Run History {dealId && <span className="text-gray-500 text-base font-normal">(filtered by deal)</span>}
        </h2>
        <button
          onClick={() => navigate('/')}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          &larr; Back to Search
        </button>
      </div>

      {runs.length === 0 ? (
        <p className="text-gray-500 text-sm py-8 text-center">No runs found.</p>
      ) : (
        <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
          {runs.map((run) => (
            <div key={run.id} className="flex items-center justify-between px-4 py-4">
              <div className="min-w-0 flex-1">
                <p className="font-medium text-gray-900 truncate">{run.company_name || run.deal_name}</p>
                <p className="text-sm text-gray-500">
                  {run.created_at && new Date(run.created_at).toLocaleString()}
                </p>
                <div className="flex gap-3 mt-1">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      run.status === 'completed'
                        ? 'bg-green-100 text-green-700'
                        : run.status === 'failed'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-yellow-100 text-yellow-700'
                    }`}
                  >
                    {run.status}
                  </span>
                  {run.stats && (
                    <span className="text-xs text-gray-500">
                      {run.stats.completion_pct}% complete ({run.stats.filled}/{run.stats.total_fields})
                    </span>
                  )}
                </div>
              </div>
              <div className="flex gap-2 ml-4">
                {run.status === 'completed' && (
                  <>
                    <button
                      onClick={() => navigate(`/review/${run.id}`)}
                      className="text-sm text-[#1E4488] hover:underline"
                    >
                      Review
                    </button>
                    <button
                      onClick={() => downloadExcel(run.id)}
                      className="text-sm text-[#F78E28] hover:underline"
                    >
                      Download
                    </button>
                  </>
                )}
                <button
                  onClick={async () => {
                    if (!confirm('Delete this run?')) return;
                    await deleteRun(run.id);
                    setRuns((prev) => prev.filter((r) => r.id !== run.id));
                  }}
                  className="text-sm text-red-400 hover:text-red-600"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
