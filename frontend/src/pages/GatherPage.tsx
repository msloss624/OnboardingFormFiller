import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  getDealContext,
  searchTranscripts,
  getTranscriptById,
  createRun,
  uploadFile,
  getRun,
  type Deal,
  type DealContext,
  type Transcript,
} from '../api/client';
import TranscriptCheckbox from '../components/TranscriptCheckbox';
import Button from '../components/ui/Button';
import { Card, CardHeader } from '../components/ui/Card';
import { Input, Textarea } from '../components/ui/Input';
import Spinner from '../components/ui/Spinner';

export default function GatherPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const deal = location.state?.deal as Deal | undefined;
  const baselineRunId = location.state?.baselineRunId as string | undefined;

  const [context, setContext] = useState<DealContext | null>(null);
  const [transcripts, setTranscripts] = useState<Transcript[] | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [additionalText, setAdditionalText] = useState('');
  const [manualFields, setManualFields] = useState({ bellwether_team: '', number_of_users: '', number_of_devices: '' });
  const [contractTypes, setContractTypes] = useState<Set<string>>(new Set());
  const [previousSources, setPreviousSources] = useState<string[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<{ name: string; text: string }[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [pasteUrl, setPasteUrl] = useState('');
  const [pasteError, setPasteError] = useState('');
  const [pasteLoading, setPasteLoading] = useState(false);

  useEffect(() => {
    if (!deal) {
      navigate('/');
      return;
    }

    async function load() {
      const ctx = await getDealContext(deal!.id);
      setContext(ctx);

      if (ctx.client_domain) {
        const emails = ctx.contacts
          .filter((c) => c.email && ctx.client_domain && c.email.includes(ctx.client_domain))
          .map((c) => c.email);
        const ts = await searchTranscripts(ctx.client_domain, emails);
        ts.sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
        setTranscripts(ts);
        setSelectedIds(new Set(ts.map((t) => t.id)));
      } else {
        setTranscripts([]);
      }

      if (baselineRunId) {
        const baseline = await getRun(baselineRunId);
        if (baseline.sources_used) setPreviousSources(baseline.sources_used);
      }

      setLoading(false);
    }

    load();
  }, [deal, navigate, baselineRunId]);

  function toggleTranscript(id: string, checked: boolean) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      checked ? next.add(id) : next.delete(id);
      return next;
    });
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';
    setUploading(true);
    try {
      const result = await uploadFile(file);
      setUploadedFiles((prev) => [...prev, { name: result.filename, text: result.text }]);
    } catch {
      alert('Failed to extract text from file. Please check the file and try again.');
    } finally {
      setUploading(false);
    }
  }

  async function handleAddByUrl() {
    setPasteError('');
    const url = pasteUrl.trim();
    if (!url) return;

    const parts = url.split('::');
    if (parts.length < 2) {
      setPasteError('Invalid URL — expected format: https://app.fireflies.ai/view/...::TRANSCRIPT_ID');
      return;
    }
    const transcriptId = parts[parts.length - 1];

    if (transcripts?.some((t) => t.id === transcriptId)) {
      setPasteError('This transcript is already in the list.');
      return;
    }

    setPasteLoading(true);
    try {
      const t = await getTranscriptById(transcriptId);
      setTranscripts((prev) => (prev ? [...prev, t] : [t]));
      setSelectedIds((prev) => new Set([...prev, t.id]));
      setPasteUrl('');
    } catch {
      setPasteError('Transcript not found. Check the URL and try again.');
    } finally {
      setPasteLoading(false);
    }
  }

  function removeUploadedFile(index: number) {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit() {
    if (!deal) return;
    setSubmitting(true);

    const overrides: Record<string, string> = {};
    if (manualFields.bellwether_team.trim()) overrides.bellwether_team = manualFields.bellwether_team;
    if (manualFields.number_of_users.trim()) overrides.number_of_users = manualFields.number_of_users;
    if (manualFields.number_of_devices.trim()) overrides.number_of_devices = manualFields.number_of_devices;
    if (contractTypes.size > 0) overrides.contract_type = Array.from(contractTypes).join(', ');

    const allText = [
      additionalText,
      ...uploadedFiles.map((f) => `--- ${f.name} ---\n${f.text}`),
    ].filter(Boolean).join('\n\n');

    const result = await createRun({
      deal_id: deal.id,
      deal_name: deal.name,
      transcript_ids: Array.from(selectedIds),
      additional_text: allText,
      manual_overrides: overrides,
      baseline_run_id: baselineRunId,
    });

    navigate(`/extracting/${result.id}`);
  }

  if (!deal) return null;
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Spinner />
        <span className="ml-3 text-gray-600">Loading deal data...</span>
      </div>
    );
  }

  const company = context?.company;

  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover:text-gray-700">
        &larr; Back to Search
      </button>

      <h2 className="font-heading text-2xl text-gray-900">Gathering Data: {deal.name}</h2>

      {/* HubSpot Context */}
      {company && (
        <Card>
          <CardHeader>HubSpot Data</CardHeader>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Company</p>
              <p className="font-medium">{company.name}</p>
            </div>
            <div>
              <p className="text-gray-500">Location</p>
              <p className="font-medium">{[company.city, company.state].filter(Boolean).join(', ') || '—'}</p>
            </div>
            <div>
              <p className="text-gray-500">Employees</p>
              <p className="font-medium">{company.employee_count ?? '—'}</p>
            </div>
            <div>
              <p className="text-gray-500">Domain</p>
              <p className="font-medium">{context?.client_domain || '—'}</p>
            </div>
          </div>
          {context?.contacts && context.contacts.length > 0 && (
            <div className="mt-3 text-sm">
              <p className="text-gray-500 mb-1">Contacts</p>
              {context.contacts.map((c) => (
                <p key={c.id} className="text-gray-700">
                  {c.first_name} {c.last_name} — {c.email} {c.job_title && `(${c.job_title})`}
                </p>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Transcripts */}
      <Card>
        <CardHeader>Fireflies Transcripts ({transcripts?.length || 0} found)</CardHeader>
        {transcripts && transcripts.length > 0 ? (
          <div className="space-y-2">
            <label className="flex items-center gap-2 pb-2 border-b border-gray-100 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedIds.size === transcripts.length}
                onChange={(e) =>
                  setSelectedIds(e.target.checked ? new Set(transcripts.map((t) => t.id)) : new Set())
                }
                className="h-4 w-4 rounded border-gray-300 text-primary accent-primary"
              />
              <span className="text-sm font-medium text-gray-700">
                {selectedIds.size === transcripts.length ? 'Deselect all' : 'Select all'}
              </span>
            </label>
            {transcripts.map((t) => (
              <TranscriptCheckbox
                key={t.id}
                transcript={t}
                checked={selectedIds.has(t.id)}
                onChange={(checked) => toggleTranscript(t.id, checked)}
                previousSources={previousSources}
              />
            ))}
            <p className="text-xs text-gray-500 mt-2">
              Total words: {transcripts.filter((t) => selectedIds.has(t.id)).reduce((s, t) => s + t.word_count, 0).toLocaleString()}
            </p>
          </div>
        ) : (
          <p className="text-sm text-gray-500">No transcripts found. You can add one by URL below.</p>
        )}

        {/* Add transcript by Fireflies URL */}
        <div className="mt-3 pt-3 border-t border-gray-100">
          <label className="block text-sm text-gray-600 mb-1">Add transcript by Fireflies URL</label>
          <div className="flex gap-2">
            <Input
              type="text"
              value={pasteUrl}
              onChange={(e) => { setPasteUrl(e.target.value); setPasteError(''); }}
              placeholder="https://app.fireflies.ai/view/Meeting-Title::TRANSCRIPT_ID"
              className="flex-1"
            />
            <Button
              onClick={handleAddByUrl}
              disabled={!pasteUrl.trim()}
              loading={pasteLoading}
              size="sm"
            >
              Add
            </Button>
          </div>
          {pasteError && (
            <p className="text-sm text-red-600 mt-1">{pasteError}</p>
          )}
        </div>
      </Card>

      {/* Additional content */}
      <Card>
        <CardHeader className="normal-case tracking-normal text-base">Additional Sources (optional)</CardHeader>
        <Textarea
          value={additionalText}
          onChange={(e) => setAdditionalText(e.target.value)}
          placeholder="Paste any additional text, meeting notes, or other relevant content..."
          rows={4}
        />

        <div className="mt-3">
          <label className="inline-flex items-center gap-2 cursor-pointer rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
            {uploading ? (
              <>
                <Spinner size="sm" />
                Extracting text...
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Upload PDF or Word file
              </>
            )}
            <input
              type="file"
              accept=".pdf,.docx,.doc"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>

        {uploadedFiles.length > 0 && (
          <div className="mt-2 space-y-1">
            {uploadedFiles.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-gray-700">
                <svg className="h-4 w-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="truncate">{f.name}</span>
                <button
                  onClick={() => removeUploadedFile(i)}
                  className="ml-auto text-gray-400 hover:text-red-500 shrink-0"
                  title="Remove file"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Manual fields */}
      <Card>
        <CardHeader>Client Details</CardHeader>
        <p className="text-xs text-gray-500 mb-3">These fields are filled by the person running the form.</p>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Account Team</label>
            <Input
              type="text"
              value={manualFields.bellwether_team}
              onChange={(e) => setManualFields((p) => ({ ...p, bellwether_team: e.target.value }))}
              placeholder="e.g. John Smith (AE), Jane Doe (TA)"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Number of Users</label>
            <Input
              type="text"
              value={manualFields.number_of_users}
              onChange={(e) => setManualFields((p) => ({ ...p, number_of_users: e.target.value }))}
              placeholder="e.g. 45"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Number of Machines</label>
            <Input
              type="text"
              value={manualFields.number_of_devices}
              onChange={(e) => setManualFields((p) => ({ ...p, number_of_devices: e.target.value }))}
              placeholder="e.g. 50"
            />
          </div>
        </div>
        <div className="mt-4">
          <label className="block text-sm text-gray-600 mb-2">Contract Type</label>
          <div className="flex flex-wrap gap-3">
            {['Fully Managed', 'Infrastructure', 'Service Desk', 'Security'].map((opt) => (
              <label key={opt} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={contractTypes.has(opt)}
                  onChange={(e) =>
                    setContractTypes((prev) => {
                      const next = new Set(prev);
                      e.target.checked ? next.add(opt) : next.delete(opt);
                      return next;
                    })
                  }
                  className="h-4 w-4 rounded border-gray-300 text-primary accent-primary"
                />
                <span className="text-sm text-gray-700">{opt}</span>
              </label>
            ))}
          </div>
        </div>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        <Button variant="ghost" onClick={() => navigate('/')}>
          &larr; Back
        </Button>
        <Button
          variant="accent"
          onClick={handleSubmit}
          loading={submitting}
          className="flex-1"
        >
          Generate Form
        </Button>
      </div>
    </div>
  );
}
