export type ApiError = {
  error: {
    code: string;
    message: string;
    details?: Array<Record<string, string>>;
  };
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
};

export type User = {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: User;
  organization: Organization;
};

export type CurrentUserResponse = User & {
  organization: Organization;
};

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

export type DocumentListItem = {
  id: string;
  filename: string;
  status: string;
  latest_version_number: number;
  created_at: string;
  updated_at: string;
  overall_risk_score: number | null;
};

export type DocumentUploadResponse = {
  document_id: string;
  document_version_id: string;
  job_id: string;
  job_status: string;
};

export type DocumentStatusResponse = {
  document_id: string;
  document_version_id: string;
  document_status: string;
  job_id: string;
  job_status: string;
  current_stage: string;
  error_stage?: string | null;
  error_code?: string | null;
  updated_at: string;
};

export type DocumentDetailResponse = {
  id: string;
  filename: string;
  status: string;
  latest_version_number: number;
  created_at: string;
  updated_at: string;
  current_job_status?: string | null;
  current_stage?: string | null;
  overall_risk_score?: number | null;
};

export type SummaryIssue = {
  risk_id: string;
  category: string;
  title: string;
  severity: string;
  score: number;
  rationale: string;
  recommendation: string;
  clause_id?: string | null;
  citations: Array<Record<string, unknown>>;
};

export type MissingProtectionSummary = {
  category: string;
  title: string;
  risk_id: string;
  recommendation: string;
};

export type NegotiationPrioritySummary = {
  priority_rank: number;
  risk_id: string;
  title: string;
  category: string;
  recommendation: string;
  severity: string;
};

export type ClauseCoverageItem = {
  clause_type: string;
  detected: boolean;
  clause_count: number;
  clause_ids: string[];
};

export type DocumentSummaryResponse = {
  document_id: string;
  document_version_id: string;
  analysis_job_id?: string | null;
  generated_from_status: string;
  overall_risk_score: number;
  top_issues: SummaryIssue[];
  missing_protections: MissingProtectionSummary[];
  negotiation_priorities: NegotiationPrioritySummary[];
  clause_coverage_summary: ClauseCoverageItem[];
  updated_at: string;
};

export type ClauseRead = {
  id: string;
  document_version_id: string;
  chunk_id?: string | null;
  clause_type: string;
  title?: string | null;
  text: string;
  normalized_text?: string | null;
  confidence: number;
  source_method: string;
  page_start?: number | null;
  page_end?: number | null;
  start_char?: number | null;
  end_char?: number | null;
  created_at: string;
  updated_at: string;
};

export type RiskRead = {
  id: string;
  document_id: string;
  document_version_id: string;
  clause_id?: string | null;
  analysis_job_id?: string | null;
  scope: string;
  severity: string;
  category: string;
  title: string;
  summary: string;
  score: number;
  rationale: string;
  recommendation: string;
  confidence: number;
  citations: Array<Record<string, unknown>>;
  deterministic_rule_code?: string | null;
  evidence_text?: string | null;
  created_at: string;
  updated_at: string;
};

export type DashboardData = {
  currentUser: CurrentUserResponse;
  documents: DocumentListItem[];
};

export type ReportRead = {
  id: string;
  document_id: string;
  document_version_id?: string | null;
  analysis_job_id?: string | null;
  filename: string;
  storage_key: string;
  report_type: string;
  status: string;
  file_size_bytes?: number | null;
  generated_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type ReportGenerateResponse = {
  report: ReportRead;
  download_url: string;
};

export type BillingStatusResponse = {
  subscription_status: string;
  stripe_customer_id?: string | null;
  stripe_subscription_id?: string | null;
  stripe_price_id?: string | null;
  premium_access: boolean;
};

export type CheckoutSessionResponse = {
  checkout_url: string;
};

export type CustomerPortalResponse = {
  portal_url: string;
};

export type ClauseDiffItem = {
  clause_type: string;
  left_present: boolean;
  right_present: boolean;
  changed: boolean;
  left_clause_ids: string[];
  right_clause_ids: string[];
};

export type RiskDiffItem = {
  category: string;
  title: string;
  change_type: string;
  left_score?: number | null;
  right_score?: number | null;
  left_severity?: string | null;
  right_severity?: string | null;
  explanation: string;
};

export type ComparisonResponse = {
  left_document_id: string;
  right_document_id: string;
  left_filename: string;
  right_filename: string;
  left_overall_score: number;
  right_overall_score: number;
  score_delta: number;
  clause_differences: ClauseDiffItem[];
  risk_differences: RiskDiffItem[];
  new_risks_introduced: RiskDiffItem[];
  protections_removed: string[];
  protections_added: string[];
};
