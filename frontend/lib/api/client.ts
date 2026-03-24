import {
  ApiError,
  AuthResponse,
  BillingStatusResponse,
  ClauseRead,
  ComparisonResponse,
  CurrentUserResponse,
  CustomerPortalResponse,
  DashboardData,
  DocumentDetailResponse,
  DocumentListItem,
  DocumentStatusResponse,
  DocumentSummaryResponse,
  DocumentUploadResponse,
  HealthResponse,
  CheckoutSessionResponse,
  ReportGenerateResponse,
  ReportRead,
  RiskRead,
} from "@/lib/api/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type RequestOptions = {
  method?: "GET" | "POST";
  token?: string | null;
  body?: BodyInit | null;
  headers?: HeadersInit;
};

export class ApiClientError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    body: options.body ?? null,
    headers,
  });

  if (!response.ok) {
    let errorPayload: ApiError | null = null;
    try {
      errorPayload = (await response.json()) as ApiError;
    } catch {
      errorPayload = null;
    }
    throw new ApiClientError(
      errorPayload?.error.message ?? "Request failed.",
      errorPayload?.error.code ?? "request_failed",
      response.status,
    );
  }

  return (await response.json()) as T;
}

export const apiClient = {
  getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>("/api/v1/health");
  },

  register(payload: {
    organization_name: string;
    full_name: string;
    email: string;
    password: string;
  }): Promise<AuthResponse> {
    return request<AuthResponse>("/api/v1/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  login(payload: { email: string; password: string }): Promise<AuthResponse> {
    return request<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  getCurrentUser(token: string): Promise<CurrentUserResponse> {
    return request<CurrentUserResponse>("/api/v1/users/me", { token });
  },

  getDocuments(token: string): Promise<DocumentListItem[]> {
    return request<DocumentListItem[]>("/api/v1/documents", { token });
  },

  uploadDocument(token: string, file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append("upload", file);
    return request<DocumentUploadResponse>("/api/v1/documents/upload", {
      method: "POST",
      token,
      body: formData,
    });
  },

  getDocument(token: string, documentId: string): Promise<DocumentDetailResponse> {
    return request<DocumentDetailResponse>(`/api/v1/documents/${documentId}`, { token });
  },

  getDocumentStatus(token: string, documentId: string): Promise<DocumentStatusResponse> {
    return request<DocumentStatusResponse>(`/api/v1/documents/${documentId}/status`, { token });
  },

  getDocumentSummary(token: string, documentId: string): Promise<DocumentSummaryResponse> {
    return request<DocumentSummaryResponse>(`/api/v1/documents/${documentId}/summary`, { token });
  },

  getDocumentClauses(token: string, documentId: string): Promise<ClauseRead[]> {
    return request<ClauseRead[]>(`/api/v1/documents/${documentId}/clauses`, { token });
  },

  getDocumentRisks(token: string, documentId: string): Promise<RiskRead[]> {
    return request<RiskRead[]>(`/api/v1/documents/${documentId}/risks`, { token });
  },

  getReports(token: string, documentId: string): Promise<ReportRead[]> {
    return request<ReportRead[]>(`/api/v1/reports/documents/${documentId}`, { token });
  },

  generateReport(token: string, documentId: string): Promise<ReportGenerateResponse> {
    return request<ReportGenerateResponse>(`/api/v1/reports/documents/${documentId}`, {
      method: "POST",
      token,
    });
  },

  getReport(token: string, reportId: string): Promise<ReportGenerateResponse> {
    return request<ReportGenerateResponse>(`/api/v1/reports/${reportId}`, { token });
  },

  getBillingStatus(token: string): Promise<BillingStatusResponse> {
    return request<BillingStatusResponse>("/api/v1/billing", { token });
  },

  createCheckoutSession(token: string): Promise<CheckoutSessionResponse> {
    return request<CheckoutSessionResponse>("/api/v1/billing/checkout", {
      method: "POST",
      token,
    });
  },

  createCustomerPortalSession(token: string): Promise<CustomerPortalResponse> {
    return request<CustomerPortalResponse>("/api/v1/billing/portal", {
      method: "POST",
      token,
    });
  },

  compareDocuments(
    token: string,
    leftDocumentId: string,
    rightDocumentId: string,
  ): Promise<ComparisonResponse> {
    return request<ComparisonResponse>(
      `/api/v1/comparisons/documents?left_document_id=${leftDocumentId}&right_document_id=${rightDocumentId}`,
      { token },
    );
  },

  async getDashboardData(token: string): Promise<DashboardData> {
    const [currentUser, documents] = await Promise.all([
      this.getCurrentUser(token),
      this.getDocuments(token),
    ]);
    return { currentUser, documents };
  },
};
