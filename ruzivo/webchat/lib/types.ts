export interface Contact {
  ministry?: string;
  phone?: string | null;
  whatsapp?: string | null;
  email?: string | null;
  address?: string | null;
  hours?: string | null;
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
}

export interface DoneMeta {
  source_ministry: string[];
  citations: Citation[];
  confident: boolean;
  fallback_contact: Contact[] | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  streaming?: boolean;
  meta?: DoneMeta;
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
};
