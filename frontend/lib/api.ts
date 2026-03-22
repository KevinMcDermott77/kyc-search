const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('kyc_token');
}

export function setToken(token: string) {
  localStorage.setItem('kyc_token', token);
}

export function clearToken() {
  localStorage.removeItem('kyc_token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

// Auth
export const login = (email: string, password: string) =>
  request<{ access_token: string; token_type: string }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

export const getMe = () => request<{ id: number; email: string; is_admin: boolean }>('/auth/me');

// Search
export const searchCompanies = (q: string, page = 1) =>
  request<{
    items: CompanySearchResult[];
    total_results: number;
    items_per_page: number;
    start_index: number;
  }>(`/search?q=${encodeURIComponent(q)}&page=${page}`);

// Company
export const getCompany = (number: string) =>
  request<CompanyDetail>(`/companies/${number}`);

export const getOfficers = (number: string) =>
  request<Officer[]>(`/companies/${number}/officers`);

export const getPscs = (number: string) =>
  request<Psc[]>(`/companies/${number}/pscs`);

export const getFilings = (number: string) =>
  request<Filing[]>(`/companies/${number}/filings`);

// Ownership
export const getOwnershipTree = (number: string) =>
  request<{ root: OwnershipNode | null; ch_sources: Record<string, string> }>(`/ownership/${number}`);

// Screening
export const getScreening = (number: string) =>
  request<ScreeningResult>(`/screening/${number}`);

// Cases
export const listCases = (status?: string, companyNumber?: string, page = 1) => {
  const params = new URLSearchParams({ page: String(page) });
  if (status) params.set('status', status);
  if (companyNumber) params.set('company_number', companyNumber);
  return request<CaseListItem[]>(`/cases?${params}`);
};
export const getCase = (id: number) => request<CaseDetail>(`/cases/${id}`);
export const createCase = (data: CreateCaseInput) =>
  request<CaseDetail>('/cases', { method: 'POST', body: JSON.stringify(data) });
export const updateCase = (id: number, data: UpdateCaseInput) =>
  request<CaseDetail>(`/cases/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
export const addCaseNote = (id: number, text: string) =>
  request<CaseNote>(`/cases/${id}/notes`, { method: 'POST', body: JSON.stringify({ text }) });

// Admin
export const listUsers = () => request<User[]>('/admin/users');
export const createUser = (data: { email: string; password: string; is_admin: boolean }) =>
  request<User>('/admin/users', { method: 'POST', body: JSON.stringify(data) });
export const updateUser = (id: number, data: { is_active?: boolean; is_admin?: boolean }) =>
  request<User>(`/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) });
export const listAuditLogs = (page = 1) =>
  request<AuditLogEntry[]>(`/audit?page=${page}`);

// Types
export interface CompanySearchResult {
  company_number: string;
  company_name: string;
  company_status: string | null;
  company_type: string | null;
  date_of_creation: string | null;
  registered_office_address: Record<string, string> | null;
  snippet: string | null;
}

export interface CompanyDetail {
  company_number: string;
  company_name: string;
  company_status: string | null;
  company_type: string | null;
  date_of_creation: string | null;
  date_of_cessation: string | null;
  registered_office_address: Record<string, string> | null;
  sic_codes: string[] | null;
  accounts_overdue: boolean;
  confirmation_statement_overdue: boolean;
  has_charges: boolean;
  has_insolvency_history: boolean;
  jurisdiction: string | null;
  risk_flags: string[] | null;
  total_officers: number;
  total_pscs: number;
  cached_at: string;
}

export interface Officer {
  id: number;
  name: string;
  role: string;
  appointed_on: string | null;
  resigned_on: string | null;
  nationality: string | null;
  occupation: string | null;
  birth_month: number | null;
  birth_year: number | null;
  service_address_line1: string | null;
  service_address_locality: string | null;
  service_address_postal_code: string | null;
  service_address_country: string | null;
}

export interface Psc {
  id: number;
  name: string;
  kind: string;
  linked_company_number: string | null;
  natures_of_control: string[] | null;
  notified_on: string | null;
  ceased_on: string | null;
  birth_month: number | null;
  birth_year: number | null;
  nationality: string | null;
  country_of_residence: string | null;
}

export interface Filing {
  id: number;
  transaction_id: string;
  description: string | null;
  category: string | null;
  type: string | null;
  date: string | null;
  document_url: string | null;
}

export interface OwnershipNode {
  company_number: string;
  company_name: string;
  company_status: string | null;
  ch_url: string;
  natures_of_control: string[];
  percentage_label: string;
  children: OwnershipNode[];
}

export interface User {
  id: number;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AuditLogEntry {
  id: number;
  user_id: number | null;
  action: string;
  target: string | null;
  source: string;
  endpoint: string | null;
  status_code: number | null;
  detail: string | null;
  created_at: string;
}

export interface SanctionsHit {
  name: string;
  regime: string;
  entity_type: string;
  unique_id: string;
}

export interface SanctionsResult {
  name: string;
  type: string;
  hits: SanctionsHit[];
  match: boolean;
}

export interface PepIndicator {
  name: string;
  type: string;
  role: string | null;
  occupation: string | null;
  nationality: string | null;
}

export interface CountryRisk {
  country: string;
  risk: 'high' | 'elevated';
  list: string;
  flagged_for: string;
  person_type: string;
}

export interface SectorRisk {
  sic_code: string;
  sector_label: string;
  risk: 'high' | 'medium' | 'low';
  reason: string;
}

export interface AdverseMediaArticle {
  title: string;
  url: string;
  domain: string;
  date: string;
  sourcecountry: string;
}

export interface ScreeningResult {
  overall_score: number;
  overall_label: 'HIGH' | 'MEDIUM' | 'LOW';
  overall_color: 'red' | 'yellow' | 'green';
  sanctions: SanctionsResult[];
  pep_indicators: PepIndicator[];
  country_risks: CountryRisk[];
  sector_risks: SectorRisk[];
  adverse_media: { articles: AdverseMediaArticle[]; source: string; error?: string };
  screened_names: number;
  sanctions_api_source: string;
  pep_source: string;
  country_source: string;
  sector_source: string;
  adverse_media_source: string;
}

export interface CaseNote {
  id: number;
  text: string;
  user_email: string | null;
  created_at: string | null;
}

export interface CaseListItem {
  id: number;
  company_number: string;
  company_name: string;
  status: 'pending' | 'approved' | 'flagged' | 'closed';
  risk_score: number | null;
  risk_label: 'LOW' | 'MEDIUM' | 'HIGH' | null;
  assigned_to_email: string | null;
  created_by_email: string | null;
  created_at: string | null;
}

export interface CaseDetail extends CaseListItem {
  screening_snapshot: ScreeningResult | null;
  updated_at: string | null;
  notes: CaseNote[];
}

export interface CreateCaseInput {
  company_number: string;
  company_name: string;
  risk_score?: number;
  risk_label?: string;
  screening_snapshot?: ScreeningResult;
}

export interface UpdateCaseInput {
  status?: string;
  assigned_to_id?: number;
}
