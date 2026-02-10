import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

// In production with MSAL, we'd attach the Bearer token here.
// For now, the backend uses dev auth when no Azure AD is configured.
export function setAuthToken(token: string) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
}

// Token acquisition function set by MsalProvider — used by interceptor
// to get a fresh token before every API call
let acquireToken: (() => Promise<string>) | null = null;

export function setTokenAcquirer(fn: () => Promise<string>) {
  acquireToken = fn;
}

api.interceptors.request.use(async (config) => {
  if (acquireToken) {
    const token = await acquireToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Deals ---

export async function searchDeals(query: string) {
  const { data } = await api.get('/deals/search', { params: { q: query } });
  return data as Deal[];
}

export async function getDealContext(dealId: string) {
  const { data } = await api.get(`/deals/${dealId}/context`);
  return data as DealContext;
}

// --- Transcripts ---

export async function searchTranscripts(domain: string, emails: string[]) {
  const { data } = await api.get('/transcripts', {
    params: { domain, emails: emails.join(',') },
  });
  return data as Transcript[];
}

export async function getTranscriptById(id: string) {
  const { data } = await api.get(`/transcripts/${id}`);
  return data as Transcript;
}

// --- Runs ---

export async function createRun(req: CreateRunRequest) {
  const { data } = await api.post('/runs', req);
  return data as { id: string; status: string };
}

export async function getRun(runId: string) {
  const { data } = await api.get(`/runs/${runId}`);
  return data as Run;
}

export async function updateAnswers(runId: string, answers: Answer[]) {
  const { data } = await api.put(`/runs/${runId}/answers`, { answers });
  return data;
}

export async function listRuns(dealId?: string) {
  const { data } = await api.get('/runs', { params: dealId ? { deal_id: dealId } : {} });
  return data as RunSummary[];
}

export async function retryField(runId: string, fieldKey: string, promptHint?: string) {
  const { data } = await api.post(`/runs/${runId}/retry-field`, {
    field_key: fieldKey,
    prompt_hint: promptHint || '',
  });
  return data as Answer;
}

export async function deleteRun(runId: string) {
  const { data } = await api.delete(`/runs/${runId}`);
  return data;
}

export async function uploadFile(file: File) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/runs/upload', form);
  return data as { filename: string; text: string };
}

export async function getEmailPreview(runId: string) {
  const { data } = await api.get(`/runs/${runId}/email-preview`);
  return data as EmailPreview;
}

export async function sendToAccountTeam(
  runId: string,
  subject: string,
  recipients: string[],
  fields: Record<string, string>,
  sow?: File,
  msa?: File,
) {
  const form = new FormData();
  form.append('subject', subject);
  form.append('recipients', recipients.join(','));
  form.append('fields_json', JSON.stringify(fields));
  if (sow) form.append('sow', sow);
  if (msa) form.append('msa', msa);
  const { data } = await api.post(`/runs/${runId}/send-email`, form);
  return data as { status: string; email_sent_at: string; recipients: string[] };
}

export async function downloadExcel(runId: string) {
  const { data, headers } = await api.get(`/runs/${runId}/excel`, {
    responseType: 'blob',
  });
  const disposition = headers['content-disposition'] || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : `run-${runId}.xlsx`;
  const url = URL.createObjectURL(data);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// --- Types ---

export interface Deal {
  id: string;
  name: string;
  stage: string;
  amount: string | null;
  close_date: string | null;
}

export interface Contact {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  job_title: string | null;
}

export interface Company {
  id: string;
  name: string;
  domain: string | null;
  city: string | null;
  state: string | null;
  industry: string | null;
  employee_count: number | null;
}

export interface DealContext {
  company: Company | null;
  contacts: Contact[];
  notes: { body: string; timestamp: string }[];
  client_domain: string | null;
  deal_owner: string | null;
  close_date: string | null;
  error?: string;
}

export interface Transcript {
  id: string;
  title: string;
  date: string;
  speakers: string[];
  word_count: number;
  summary: string;
}

export interface Answer {
  field_key: string;
  question: string;
  answer: string | null;
  confidence: 'high' | 'medium' | 'low' | 'missing';
  source: string;
  evidence: string;
  row: number;
}

export interface Run {
  id: string;
  deal_id: string;
  deal_name: string;
  company_name: string | null;
  status: 'pending' | 'extracting' | 'completed' | 'failed';
  answers: Answer[] | null;
  sources_used: string[] | null;
  stats: RunStats | null;
  excel_blob_path: string | null;
  baseline_run_id: string | null;
  created_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  email_sent_at: string | null;
  email_sent_by: string | null;
}

export interface RunStats {
  total_fields: number;
  filled: number;
  completion_pct: number;
  by_confidence: Record<string, number>;
}

export interface RunSummary {
  id: string;
  deal_id: string;
  deal_name: string;
  company_name: string | null;
  status: string;
  stats: RunStats | null;
  created_at: string | null;
  completed_at: string | null;
  email_sent_at: string | null;
}

export interface EmailPreview {
  subject: string;
  fields: Record<string, string>;
  recipients: string[];
  email_sent_at: string | null;
}

export interface CreateRunRequest {
  deal_id: string;
  deal_name: string;
  transcript_ids: string[];
  additional_text: string;
  manual_overrides: Record<string, string>;
  baseline_run_id?: string;
}
