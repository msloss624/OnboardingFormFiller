import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

// In production with MSAL, we'd attach the Bearer token here.
// For now, the backend uses dev auth when no Azure AD is configured.
export function setAuthToken(token: string) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
}

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

export function getExcelUrl(runId: string) {
  return `/api/runs/${runId}/excel`;
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
}

export interface CreateRunRequest {
  deal_id: string;
  deal_name: string;
  transcript_ids: string[];
  additional_text: string;
  manual_overrides: Record<string, string>;
  baseline_run_id?: string;
}
