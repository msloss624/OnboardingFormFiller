import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getRun, updateAnswers, getExcelUrl, retryField, type Run, type Answer } from '../api/client';
import AnswerEditor from '../components/AnswerEditor';

// Field categories in display order
const CATEGORIES = [
  'Engagement & Project Details',
  'Company Overview',
  'Current IT State & Provider',
  'Microsoft 365 & Licensing',
  'Servers & Infrastructure',
  'Data, Files & Applications',
  'Email & Communication',
  'Network & Connectivity',
  'Devices & Endpoints',
  'Security & Compliance',
  'Backup & Disaster Recovery',
  'Documentation & Handoff',
];

// Map field keys to categories based on row ranges
function getCategory(row: number): string {
  if (row <= 11) return CATEGORIES[0];
  if (row <= 18) return CATEGORIES[1];
  if (row <= 25) return CATEGORIES[2];
  if (row <= 33) return CATEGORIES[3];
  if (row <= 44) return CATEGORIES[4];
  if (row <= 53) return CATEGORIES[5];
  if (row <= 65) return CATEGORIES[6];
  if (row <= 75) return CATEGORIES[7];
  if (row <= 84) return CATEGORIES[8];
  if (row <= 98) return CATEGORIES[9];
  if (row <= 103) return CATEGORIES[10];
  return CATEGORIES[11];
}

export default function ReviewPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<Run | null>(null);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [saving, setSaving] = useState(false);
  const [retryingField, setRetryingField] = useState<string | null>(null);
  const [openCategories, setOpenCategories] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!runId) return;
    getRun(runId).then((data) => {
      setRun(data);
      if (data.answers) setAnswers(data.answers);
    });
  }, [runId]);

  function handleAnswerChange(updated: Answer) {
    setAnswers((prev) =>
      prev.map((a) => (a.field_key === updated.field_key ? updated : a))
    );
  }

  async function handleSave() {
    if (!runId) return;
    setSaving(true);
    await updateAnswers(runId, answers);
    setSaving(false);
  }

  async function handleRetry(fieldKey: string) {
    if (!runId) return;
    setRetryingField(fieldKey);
    try {
      const updated = await retryField(runId, fieldKey);
      setAnswers((prev) =>
        prev.map((a) => (a.field_key === fieldKey ? updated : a))
      );
    } catch {
      // Silently fail — the field just stays unchanged
    } finally {
      setRetryingField(null);
    }
  }

  function toggleCategory(cat: string) {
    setOpenCategories((prev) => {
      const next = new Set(prev);
      next.has(cat) ? next.delete(cat) : next.add(cat);
      return next;
    });
  }

  if (!run) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#1E4488] border-t-transparent" />
      </div>
    );
  }

  const total = answers.length;
  const filled = answers.filter((a) => a.confidence !== 'missing').length;
  const high = answers.filter((a) => a.confidence === 'high').length;
  const medium = answers.filter((a) => a.confidence === 'medium').length;
  const missing = answers.filter((a) => a.confidence === 'missing').length;

  // Group answers by category
  const grouped = CATEGORIES.map((cat) => ({
    name: cat,
    answers: answers.filter((a) => getCategory(a.row) === cat),
  })).filter((g) => g.answers.length > 0);

  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover:text-gray-700">
        &larr; Back to Search
      </button>

      <h2 className="text-xl font-bold text-gray-900">Review: {run.company_name || run.deal_name}</h2>

      {/* Stats bar */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { label: 'Total', value: total, sub: '' },
          { label: 'Filled', value: filled, sub: `${total ? Math.round((filled / total) * 100) : 0}%` },
          { label: 'High Confidence', value: high, sub: '' },
          { label: 'Medium Confidence', value: medium, sub: '' },
          { label: 'Missing', value: missing, sub: '' },
        ].map((s) => (
          <div key={s.label} className="rounded-lg bg-gray-50 p-3 text-center">
            <p className="text-2xl font-bold text-gray-900">{s.value}</p>
            <p className="text-xs text-gray-500">
              {s.label} {s.sub && <span className="text-[#1E4488]">{s.sub}</span>}
            </p>
          </div>
        ))}
      </div>

      {/* Answers by category */}
      <div className="space-y-3">
        {grouped.map(({ name, answers: catAnswers }) => {
          const catFilled = catAnswers.filter((a) => a.confidence !== 'missing').length;
          const isOpen = openCategories.has(name);

          return (
            <div key={name} className="rounded-lg border border-gray-200 bg-white overflow-hidden">
              <button
                onClick={() => toggleCategory(name)}
                className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
              >
                <span className="font-semibold text-gray-900">
                  {name}{' '}
                  <span className="text-sm font-normal text-gray-500">
                    ({catFilled}/{catAnswers.length} filled)
                  </span>
                </span>
                <span className="text-gray-400">{isOpen ? '−' : '+'}</span>
              </button>
              {isOpen && (
                <div className="border-t border-gray-100 px-4 py-2">
                  {catAnswers.map((a) => (
                    <AnswerEditor
                      key={a.field_key}
                      answer={a}
                      onChange={handleAnswerChange}
                      onRetry={handleRetry}
                      retrying={retryingField === a.field_key}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 p-4 -mx-4 flex gap-3 justify-end">
        <button
          onClick={() =>
            navigate('/gather', {
              state: {
                deal: { id: run.deal_id, name: run.deal_name, stage: '', amount: null, close_date: null },
                baselineRunId: run.id,
              },
            })
          }
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Re-run with more data
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Edits'}
        </button>
        <a
          href={getExcelUrl(run.id)}
          className="rounded-lg bg-[#1E4488] px-6 py-2.5 text-sm font-medium text-white hover:bg-[#2a5298] inline-block text-center"
        >
          Download Excel
        </a>
      </div>
    </div>
  );
}
