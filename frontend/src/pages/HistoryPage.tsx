import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { listRuns, downloadExcel, deleteRun, type RunSummary } from '../api/client';
import { Card } from '../components/ui/Card';
import Spinner from '../components/ui/Spinner';

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
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-heading text-2xl text-gray-900">
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
        <Card className="p-0 divide-y divide-gray-100">
          {runs.map((run) => (
            <div key={run.id} className="flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors">
              <div className="min-w-0 flex-1">
                <p className="font-medium text-gray-900 truncate">{run.company_name || run.deal_name}</p>
                <p className="text-sm text-gray-500">
                  {run.created_at && new Date(run.created_at).toLocaleString()}
                  {run.created_by && <span className="ml-2 text-gray-400">by {run.created_by}</span>}
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
                      className="text-sm text-primary hover:underline"
                    >
                      Review
                    </button>
                    <button
                      onClick={() => downloadExcel(run.id)}
                      className="text-sm text-accent hover:underline"
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
        </Card>
      )}
    </div>
  );
}
