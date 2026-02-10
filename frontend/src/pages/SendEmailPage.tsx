import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getEmailPreview, sendToAccountTeam } from '../api/client';

const CONTRACT_TYPE_OPTIONS = ['Fully Managed', 'Infrastructure', 'Service Desk', 'Security'];

const FIELD_LABELS: Record<string, string> = {
  client_name: 'Client Name',
  company_description: 'Company Description',
  contract_amount: 'Contract Amount',
  account_team: 'Account Team',
  number_of_users: '# of Users',
  number_of_devices: '# of Machines',
  pain_points: 'Top Challenges / Why Switching',
  service_scope: 'Contract Type',
  go_live_date: 'Onboarding Start Date',
  primary_contact: 'Primary Contact',
};

const FIELD_ORDER = [
  'client_name',
  'company_description',
  'primary_contact',
  'contract_amount',
  'service_scope',
  'go_live_date',
  'number_of_users',
  'number_of_devices',
  'account_team',
  'pain_points',
];

function buildPreviewHtml(fields: Record<string, string>): string {
  const f = (key: string) => fields[key] || '';

  const contractParts = [f('contract_amount'), f('service_scope'), f('go_live_date') ? `Onboarding start: ${f('go_live_date')}` : ''].filter(Boolean);
  const contractLine = contractParts.length ? contractParts.join(' | ') : '\u2014';

  const envParts = [f('number_of_users') ? `${f('number_of_users')} users` : '', f('number_of_devices') ? `${f('number_of_devices')} machines` : ''].filter(Boolean);
  const envLine = envParts.length ? envParts.join(', ') : '\u2014';

  const painPoints = f('pain_points');
  let painHtml = '<p style="margin:0">\u2014</p>';
  if (painPoints) {
    const points = painPoints.replace(/\n/g, '. ').split('. ').map((p) => p.trim()).filter(Boolean);
    if (points.length > 1) {
      painHtml = `<ul style="margin:4px 0 0 0;padding-left:20px">${points.map((p) => `<li>${p.replace(/\.$/, '')}</li>`).join('')}</ul>`;
    } else {
      painHtml = `<p style="margin:4px 0 0 0">${painPoints.replace(/\n/g, '<br>')}</p>`;
    }
  }

  const h = 'color:#1E4488;font-size:14px;font-weight:700;margin:20px 0 6px 0';

  return `
<div style="font-family:Arial,sans-serif;color:#1f2937;line-height:1.6;font-size:14px">
<p>Team,</p>
<p>We've signed a new client &mdash; here's what you need to know:</p>

<p>${f('company_description') || f('client_name') || 'New Client'}</p>

<p style="${h}">Primary Contact</p>
<p style="margin:0">${f('primary_contact') || '\u2014'}</p>

<p style="${h}">Contract</p>
<p style="margin:0"><strong>${contractLine}</strong></p>

<p style="${h}">Environment</p>
<p style="margin:0">${envLine}</p>

<p style="${h}">Account Team</p>
<p style="margin:0">${f('account_team') || '\u2014'}</p>

<p style="${h}">Why They're Switching</p>
${painHtml}

<p style="margin-top:24px">The full onboarding workbook is attached, along with the signed SOW and MSA.</p>
</div>`;
}

export default function SendEmailPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [subject, setSubject] = useState('');
  const [recipients, setRecipients] = useState<string[]>([]);
  const [newRecipient, setNewRecipient] = useState('');
  const [fields, setFields] = useState<Record<string, string>>({});
  const [sowFile, setSowFile] = useState<File | null>(null);
  const [msaFile, setMsaFile] = useState<File | null>(null);
  const [contractTypes, setContractTypes] = useState<Set<string>>(new Set());
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState('');
  const [sentAt, setSentAt] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    getEmailPreview(runId).then((data) => {
      setSubject(data.subject);
      setRecipients(data.recipients);
      setFields(data.fields);
      setSentAt(data.email_sent_at);
      // Parse comma-separated contract types into the Set
      const ct = data.fields.service_scope || '';
      setContractTypes(new Set(ct.split(',').map((s: string) => s.trim()).filter(Boolean)));
      setLoading(false);
    });
  }, [runId]);

  function toggleContractType(opt: string) {
    setContractTypes((prev) => {
      const next = new Set(prev);
      next.has(opt) ? next.delete(opt) : next.add(opt);
      const joined = Array.from(next).join(', ');
      setFields((f) => ({ ...f, service_scope: joined }));
      return next;
    });
  }

  function updateField(key: string, value: string) {
    setFields((prev) => ({ ...prev, [key]: value }));
  }

  function addRecipient() {
    const email = newRecipient.trim().toLowerCase();
    if (!email || !email.includes('@')) return;
    if (recipients.some((r) => r.toLowerCase() === email)) return;
    setRecipients((prev) => [...prev, email]);
    setNewRecipient('');
  }

  function removeRecipient(email: string) {
    setRecipients((prev) => prev.filter((r) => r !== email));
  }

  async function handleSend() {
    if (!runId) return;
    if (recipients.length === 0) {
      setSendError('At least one recipient is required');
      return;
    }
    setSending(true);
    setSendError('');
    try {
      const result = await sendToAccountTeam(
        runId,
        subject,
        recipients,
        fields,
        sowFile || undefined,
        msaFile || undefined,
      );
      setSentAt(result.email_sent_at);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to send email';
      setSendError(msg);
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#1E4488] border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate(`/review/${runId}`)}
        className="text-sm text-gray-500 hover:text-gray-700"
      >
        &larr; Back to Review
      </button>

      <h2 className="text-xl font-bold text-gray-900">Send to Account Team</h2>

      {sentAt && (
        <div className="rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-700">
          Previously sent on {new Date(sentAt).toLocaleString()}. You can re-send with updated content.
        </div>
      )}

      {/* Recipients */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-900">Recipients</h3>
        <div className="flex flex-wrap gap-2">
          {recipients.map((email) => (
            <span
              key={email}
              className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700"
            >
              {email}
              <button
                onClick={() => removeRecipient(email)}
                className="ml-1 text-blue-400 hover:text-blue-600"
              >
                x
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="email"
            value={newRecipient}
            onChange={(e) => setNewRecipient(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addRecipient())}
            placeholder="Add recipient email..."
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1E4488] focus:outline-none"
          />
          <button
            onClick={addRecipient}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Add
          </button>
        </div>
      </div>

      {/* Subject */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2">
        <h3 className="text-sm font-semibold text-gray-900">Subject</h3>
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1E4488] focus:outline-none"
        />
      </div>

      {/* Two-column: Edit fields | Live preview */}
      <div className="grid grid-cols-2 gap-6">
        {/* Left: Editable fields */}
        <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-4">
          <h3 className="text-sm font-semibold text-gray-900">Edit Fields</h3>
          {FIELD_ORDER.map((key) => {
            const isMultiline = key === 'pain_points' || key === 'company_description';
            return (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  {FIELD_LABELS[key] || key}
                </label>
                {key === 'service_scope' ? (
                  <div className="flex flex-wrap gap-3 py-1">
                    {CONTRACT_TYPE_OPTIONS.map((opt) => (
                      <label key={opt} className="flex items-center gap-2 cursor-pointer text-sm">
                        <input
                          type="checkbox"
                          checked={contractTypes.has(opt)}
                          onChange={() => toggleContractType(opt)}
                          className="rounded border-gray-300"
                        />
                        {opt}
                      </label>
                    ))}
                  </div>
                ) : isMultiline ? (
                  <textarea
                    value={fields[key] || ''}
                    onChange={(e) => updateField(key, e.target.value)}
                    rows={3}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1E4488] focus:outline-none"
                  />
                ) : (
                  <input
                    type="text"
                    value={fields[key] || ''}
                    onChange={(e) => updateField(key, e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-[#1E4488] focus:outline-none"
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Right: Live email preview */}
        <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2">
          <h3 className="text-sm font-semibold text-gray-900">Email Preview</h3>
          <div className="rounded border border-gray-100 bg-gray-50 p-4">
            <p className="text-xs text-gray-500 mb-1">
              <strong>To:</strong> {recipients.join(', ') || '(no recipients)'}
            </p>
            <p className="text-xs text-gray-500 mb-3">
              <strong>Subject:</strong> {subject}
            </p>
            <div
              className="border-t border-gray-200 pt-3"
              dangerouslySetInnerHTML={{ __html: buildPreviewHtml(fields) }}
            />
          </div>
        </div>
      </div>

      {/* Attachments */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-900">Attachments</h3>
        <p className="text-xs text-gray-500">The onboarding Excel is attached automatically.</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Signed SOW (optional)</label>
            <input
              type="file"
              accept=".pdf,.docx,.doc"
              onChange={(e) => setSowFile(e.target.files?.[0] || null)}
              className="text-sm text-gray-700 file:mr-3 file:rounded file:border-0 file:bg-gray-200 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-gray-300"
            />
            {sowFile && <p className="text-xs text-gray-500 mt-1">{sowFile.name}</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Signed MSA (optional)</label>
            <input
              type="file"
              accept=".pdf,.docx,.doc"
              onChange={(e) => setMsaFile(e.target.files?.[0] || null)}
              className="text-sm text-gray-700 file:mr-3 file:rounded file:border-0 file:bg-gray-200 file:px-3 file:py-1.5 file:text-sm file:font-medium hover:file:bg-gray-300"
            />
            {msaFile && <p className="text-xs text-gray-500 mt-1">{msaFile.name}</p>}
          </div>
        </div>
      </div>

      {/* Error */}
      {sendError && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {sendError}
        </div>
      )}

      {/* Actions */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 p-4 -mx-4 flex gap-3 justify-end">
        <button
          onClick={() => navigate(`/review/${runId}`)}
          className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Back to Review
        </button>
        <button
          onClick={handleSend}
          disabled={sending || recipients.length === 0}
          className="rounded-lg bg-[#F78E28] px-6 py-2.5 text-sm font-medium text-white hover:bg-[#e07d1e] disabled:opacity-50"
        >
          {sending ? 'Sending...' : 'Send Email'}
        </button>
      </div>
    </div>
  );
}
