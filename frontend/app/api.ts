export async function api<T = unknown>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const multipart = body instanceof FormData;
  const response = await fetch("/api/v1" + path, {
    method,
    credentials: "same-origin",
    headers: {
      "X-FormFlow": "1",
      ...(!multipart && body !== undefined
        ? { "Content-Type": "application/json" }
        : {}),
    },
    body:
      body === undefined ? undefined : multipart ? body : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return response.json();
}
export type User = {
  id: string;
  handle: string;
  role: "citizen" | "caregiver" | "admin";
};
export type Profile = {
  id: string;
  name: string;
  language: "en" | "kn";
  fictional: boolean;
  authorization: string;
};
export type Doc = {
  id: string;
  category: string;
  content_type: string;
  status: string;
  error: string | null;
  quality: {
    page_count?: number;
    pages?: { warnings: string[] }[];
    classification?: string;
  };
  expires_at: string;
};
export type Fact = {
  id: string;
  key: string;
  value: string;
  original: string;
  review: string;
  confidence: number;
  document_id: string;
  method: string;
  page: number;
  bbox: number[];
};
export type Condition = {
  id: string;
  description: string;
  description_kn: string;
  status: string;
  reason: string;
  clause_id: string;
  clause_text: string;
  expected: string | number;
  actual: string[];
  unit: string;
  evidence: { document_id: string; page: number; bbox: number[] }[];
};
export type Checklist = {
  document_type: string;
  group: string;
  conditions: string[];
  reasons: string[];
};
export type Result = {
  scheme_id: string;
  name: string;
  name_kn: string;
  verdict: string;
  version: number;
  date: string;
  conditions: Condition[];
  checklist: Checklist[];
  category: string;
  department: string;
  evidence_guidance?: {
    unresolved_conditions: string[];
    documents: { document_type: string; resolves: string[] }[];
    no_sufficient_mapping: string[];
    method: string;
  };
};
export type Assessment = {
  id: string;
  created_at: string;
  results: Result[];
  rules_changed?: boolean;
};
export type Scheme = {
  id: string;
  name: string;
  name_kn: string;
  description: string;
  mode: string;
  status: string;
  source_url?: string;
  category: string;
  department: string;
};
export type ResearchField = {
  value: string;
  value_kn?: string;
  passages: string[];
};
export type ResearchScheme = {
  id: string;
  name: string;
  name_kn: string;
  primary_url: string;
  review_status: string;
  assessment_enabled: boolean;
  eligibility: ResearchField[];
  exceptions: ResearchField[];
  benefits: ResearchField[];
  application_documents: ResearchField[];
  application: ResearchField[];
  unresolved: string[];
};
export type ResearchAnswer = {
  answer: string;
  status: string;
  model_status: string;
  citations: {
    id: string;
    url: string;
    section: string;
    page: number | null;
    text: string;
    source_version: string;
  }[];
};
export type ResearchStatus = {
  sources: {
    id: string;
    title: string;
    url: string;
    status: string;
    last_error?: string;
    error?: string;
    content_hash: string | null;
    retrieved_at: string;
    extraction_note?: string;
  }[];
  passage_count: number;
  model_error: string | null;
  dense_model: string | null;
  reranker_model: string | null;
  generation_provider: string;
  generation_model: string;
  evaluation: {
    results: Record<
      string,
      { status: string; recall_at_5?: number; mrr_at_10?: number }
    >;
  } | null;
};
export type Proposal = {
  id: string;
  scheme_id: string;
  old_text: string;
  new_text: string;
  classification: string;
  state: string;
  proposed_rule: Record<string, unknown>;
  regression_cases: Record<string, unknown>[];
  validation: Record<string, unknown>;
  impact?: {
    condition_ids: string[];
    assessment_ids: string[];
    reason: string;
  };
};
export type Overview = {
  proposals: Proposal[];
  versions: {
    id: string;
    version: number;
    approved_by: string;
    created_at: string;
    rule: unknown;
  }[];
  audit: {
    id: string;
    action: string;
    target_id: string;
    created_at: string;
  }[];
  sources: {
    id: string;
    url: string;
    last_error: string | null;
    snapshots: { id: string; content_hash: string; created_at: string }[];
  }[];
};
