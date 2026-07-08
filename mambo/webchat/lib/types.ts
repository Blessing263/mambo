export interface Contact {
  ministry?: string;
  phone?: string | null;
  whatsapp?: string | null;
  email?: string | null;
  address?: string | null;
  hours?: string | null;
  office_hours?: string | null;
  service_counter_url?: string | null;
  last_verified_at?: string | null;
  human_review_owner?: string | null;
}

export interface Ministry {
  id: string;
  name: string;
  short_name: string;
  mandate: string;
  contact: Contact;
  accent_color: string;
  source_type?: string;
}

export interface Citation {
  title: string | null;
  page: number | null;
  url: string;
  ministry: string;
  snippet?: string | null;
  doc_type?: "pdf" | "web" | null;
}

export interface DoneMeta {
  source_ministry: string[];
  citations: Citation[];
  confident: boolean;
  fallback_contact: Contact[] | null;
  evidence_status?: "answered" | "partial" | "unsupported" | "declined";
  decline_reason?: string | null;
  service_journey?: string | null;
  reviewed?: boolean;
}

export interface Staff {
  id: string; email: string; name: string; role: string;
  ministry_id: string | null; ministry_short_name: string | null;
}
export interface ReviewedAnswer {
  id: string; question: string; answer: string;
  citations: any[]; enabled: boolean; updated_at: string | null;
}
export interface AdminQuery {
  asked_at: string | null; question: string;
  confident: boolean | null; answered: boolean | null;
  feedback: number | null; latency_ms: number | null; ministries: string[];
}
export interface AdminQuestion extends AdminQuery {
  id: string;
  evidence_status: "answered" | "partial" | "unsupported" | "declined";
  reviewed: boolean;
}
export interface AdminStats {
  total: number; answered: number; fallback_rate: number | null; avg_feedback: number | null;
  token_count: number; avg_latency: number | null;
  top_questions: { question: string; count: number }[];
  top_unanswered: { question: string; count: number }[];
  series: { day: string | null; count: number }[];
}
export type OfficialResponseStatus = "draft" | "pending_review" | "approved" | "archived";
export interface OfficialResponse {
  id: string;
  ministry_id: string;
  question: string;
  answer: string;
  citations: any[];
  service_area: string | null;
  status: OfficialResponseStatus;
  enabled: boolean;
  valid_from: string | null;
  review_due_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  submitted_at: string | null;
  approved_at: string | null;
  archived_at: string | null;
}
export interface OfficialResponseVersion {
  id: string;
  edited_by: string | null;
  old_status: string | null;
  new_status: string | null;
  change_note: string | null;
  created_at: string | null;
}
export interface MinistryProfile {
  id: string;
  name: string;
  short_name: string;
  contact: Contact;
  domains: string[];
  updated_at: string | null;
  sources: { title: string; url: string; fetched_at: string | null; status: string }[];
}

export type StatusStep = "route" | "search" | "read" | "verify";
export interface StatusEvent {
  step?: string;
  text: string;
}

export interface ServiceJourney {
  id: string;
  title: string;
  ministry: string;
  keywords: string[];
  sections: string[];
  icon?: string;
  blurb?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  streaming?: boolean;
  meta?: DoneMeta;
  steps?: StatusEvent[];
  feedback?: 1 | -1 | null;
}

// Material Design 3 icon names (the actual icon codepoints)
export const MINISTRY_ICON: Record<string, string> = {
  ict: "satellite_alt",
  health: "local_hospital",
  home_affairs: "badge",
  finance: "account_balance",
  education: "school",
  zimra: "receipt_long",
  zimsec: "assignment",
  veritas: "gavel",
  zimlii: "balance",
};

// "Ministry" vs "Agency" — used in the sidebar subtitle row.
export const MINISTRY_SUBTITLE: Record<string, string> = {
  ict: "Ministry",
  health: "Ministry",
  home_affairs: "Ministry",
  finance: "Ministry",
  education: "Ministry",
  zimra: "Agency",
  zimsec: "Agency",
  veritas: "Agency",
  zimlii: "Agency",
};
