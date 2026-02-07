import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getRun, type Run } from '../api/client';

export default function ExtractingPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<Run | null>(null);

  useEffect(() => {
    if (!runId) return;

    const interval = setInterval(async () => {
      const data = await getRun(runId);
      setRun(data);

      if (data.status === 'completed') {
        clearInterval(interval);
        navigate(`/review/${runId}`);
      } else if (data.status === 'failed') {
        clearInterval(interval);
      }
    }, 2000);

    // Initial fetch
    getRun(runId).then(setRun);

    return () => clearInterval(interval);
  }, [runId, navigate]);

  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      {(!run || run.status === 'pending' || run.status === 'extracting') && (
        <>
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-[#1E4488] border-t-transparent mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Extracting Answers</h2>
          <p className="text-gray-500 text-sm">
            Claude is reading transcripts and extracting answers...
          </p>
          <p className="text-gray-400 text-xs mt-1">This may take 1-2 minutes</p>
          {run?.deal_name && (
            <p className="text-sm text-gray-600 mt-4">Deal: {run.deal_name}</p>
          )}
        </>
      )}

      {run?.status === 'failed' && (
        <>
          <div className="text-red-500 text-4xl mb-4">!</div>
          <h2 className="text-xl font-semibold text-red-700 mb-2">Extraction Failed</h2>
          <p className="text-gray-600 text-sm max-w-md">{run.error_message}</p>
          <button
            onClick={() => navigate('/')}
            className="mt-6 rounded-lg bg-[#1E4488] px-6 py-2.5 text-sm font-medium text-white hover:bg-[#2a5298]"
          >
            Back to Search
          </button>
        </>
      )}
    </div>
  );
}
