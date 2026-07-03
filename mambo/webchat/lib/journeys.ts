import type { ServiceJourney } from "./types";

// Static mirror of registry/journeys.json (version-stamped) + per-journey UI icon/blurb.
// Regenerate from the registry when it changes; keep JOURNEYS_VERSION in sync.
// Static = instant render, offline, zero extra requests (the registry changes rarely).
export const JOURNEYS_VERSION = "2026-06-29";

export const JOURNEYS: ServiceJourney[] = [
  {
    id: "lost_national_id", title: "Replacing a lost national ID", ministry: "home_affairs",
    icon: "badge", blurb: "Replace a lost or damaged national identity card.",
    keywords: ["lost id", "lost national id", "replace id", "replace national id", "id card lost", "replacement id", "national id replacement", "lost identity card"],
    sections: ["Eligibility", "What to bring", "Steps", "Fees", "Where to apply", "Expected timeline"],
  },
  {
    id: "passport", title: "Applying for a passport", ministry: "home_affairs",
    icon: "card_travel", blurb: "Apply for or renew a Zimbabwean passport.",
    keywords: ["passport", "e-passport", "epassport", "apply for a passport", "renew passport", "passport application", "passport requirements", "new passport"],
    sections: ["Eligibility", "What to bring", "Steps", "Fees", "Where to apply", "Expected timeline"],
  },
  {
    id: "tax_clearance", title: "Getting a tax clearance certificate", ministry: "zimra",
    icon: "receipt_long", blurb: "Get a ZIMRA tax clearance (good standing).",
    keywords: ["tax clearance", "tax clearance certificate", "clearance certificate", "good standing tax", "zimra clearance"],
    sections: ["Eligibility", "What you need", "Steps", "Fees", "Where to apply", "Expected timeline"],
  },
  {
    id: "birth_certificate", title: "Registering a birth certificate", ministry: "home_affairs",
    icon: "child_care", blurb: "Register a birth certificate for a newborn or late registration.",
    keywords: ["birth certificate", "register a birth", "newborn birth certificate", "birth registration", "late birth registration"],
    sections: ["Eligibility", "What to bring", "Steps", "Fees", "Where to apply", "Expected timeline"],
  },
  {
    id: "business_tax_registration", title: "Registering a business for tax", ministry: "zimra",
    icon: "store", blurb: "Register a new business with ZIMRA.",
    keywords: ["register a business", "business registration tax", "register company tax", "taxpayer registration", "new business tax"],
    sections: ["Eligibility", "What you need", "Steps", "Fees", "Where to register", "Expected timeline"],
  },
  {
    id: "exam_results_certificate", title: "Exam results & certificates", ministry: "zimsec",
    icon: "school", blurb: "Check ZIMSEC results or replace a certificate.",
    keywords: ["exam results", "examination results", "zimsec results", "replace certificate", "lost zimsec certificate", "remark exam", "grade 7 results", "o level results", "a level results"],
    sections: ["Eligibility", "What to bring", "Steps", "Fees", "Where to apply", "Expected timeline"],
  },
];

export function getJourney(id: string | null | undefined): ServiceJourney | undefined {
  return id ? JOURNEYS.find((j) => j.id === id) : undefined;
}
