/* ============================================================
   RUZIVO live data — ministry registry + live RAG API client.
   Real answers from the RAG backend at /api/ask/stream.
   ============================================================ */
window.RUZIVO = (function () {
  const MINISTRIES = [
    { id: "ict", short: "ICT", type: "Ministry", icon: "satellite_alt", color: "#1F8A4C",
      name: "Information Communication Technology, Postal & Courier Services",
      mandate: "ICT & telecoms policy, data protection, the digital economy, the National AI Strategy.",
      contact: { phone: "+263 242 707347", email: "postmaster@ictministry.gov.zw", address: "76 Samora Machel Avenue, Bank Chambers, Harare", hours: "Mon–Fri 08:00–16:30" } },
    { id: "health", short: "Health", type: "Ministry", icon: "local_hospital", color: "#C0392B",
      name: "Health and Child Care",
      mandate: "Hospitals, clinics, medicines, immunisation and public-health policy.",
      contact: { phone: "+263 242 798537", email: "pr@mohcc.gov.zw", address: "Kaguvi Building, 4th Floor, Central Avenue, Harare", hours: "Mon–Fri 08:00–16:30" } },
    { id: "home_affairs", short: "Home Affairs", type: "Ministry", icon: "badge", color: "#2C3E70",
      name: "Home Affairs and Cultural Heritage",
      mandate: "National IDs, passports, civil registration, immigration and heritage.",
      contact: { phone: "+263 242 703641", email: "thesecretary@moha.gov.zw", address: "11th Floor, Mukwati Building, Harare", hours: "Mon–Fri 08:00–16:30" } },
    { id: "finance", short: "Finance", type: "Ministry", icon: "account_balance", color: "#B8860B",
      name: "Finance, Economic Development and Investment Promotion",
      mandate: "The National Budget, fiscal & tax policy, revenue and investment promotion.",
      contact: { phone: "+263 8688003449", whatsapp: "+263 719 567 051", email: "communications@zimtreasury.co.zw", address: "New Government Complex, Harare", hours: "Mon–Fri 08:00–16:30" } },
    { id: "education", short: "Education", type: "Ministry", icon: "school", color: "#2E86C1",
      name: "Primary and Secondary Education",
      mandate: "Schooling policy, curriculum, ECD, assessment and the running of all schools.",
      contact: { phone: "+263 242 799914", email: "admin@mopse.gov.zw", address: "Ambassador House, Kwame Nkrumah Avenue, Harare", hours: "Mon–Fri 08:00–16:30" } },
    { id: "zimra", short: "ZIMRA", type: "Agency", icon: "receipt_long", color: "#D4A017",
      name: "Zimbabwe Revenue Authority",
      mandate: "Revenue collection, tax administration, customs and excise.",
      contact: { phone: "+263 242 790731", email: "pr@zimra.co.zw", address: "ZIMRA House, Harare", hours: "Mon–Fri 08:00–16:30" } },
    { id: "zimsec", short: "ZIMSEC", type: "Agency", icon: "assignment", color: "#6C3483",
      name: "Zimbabwe School Examinations Council",
      mandate: "National examinations at Grade 7, O-Level and A-Level; syllabi and certificates.",
      contact: { phone: "+263 242 304119", whatsapp: "0712 737 759", address: "Upper East Road, Mount Pleasant, Harare", hours: "Mon–Fri 08:00–16:30" } },
    { id: "veritas", short: "Veritas", type: "Legal source", icon: "gavel", color: "#8B4513",
      name: "Veritas Zimbabwe — Acts, Bills & Statutory Instruments",
      mandate: "Public access to Zimbabwean legislation: Acts, SIs, Bills and the Constitution.",
      contact: { url: "veritaszim.net" } },
  ];
  const byId = Object.fromEntries(MINISTRIES.map((m) => [m.id, m]));
  // Per-ministry example questions — shown when that ministry is selected.
  // null key = "All of Government" (the default landing).
  const EXAMPLES_BY_MINISTRY = {
    null: [
      { q: "What is the National AI Strategy?", icon: "smart_toy" },
      { q: "I lost my national ID — how do I get a replacement?", icon: "badge" },
      { q: "What taxes do employers need to pay?", icon: "payments" },
      { q: "How do I import a car from abroad?", icon: "directions_car" },
    ],
    ict: [
      { q: "What is the National AI Strategy?", icon: "smart_toy" },
      { q: "What does the Cyber and Data Protection Act cover?", icon: "shield" },
      { q: "What is the National Broadband Plan?", icon: "wifi" },
      { q: "What is the Ministry's vision for a digital economy?", icon: "trending_up" },
    ],
    health: [
      { q: "What health services does the government provide?", icon: "local_hospital" },
      { q: "How do I register as a health professional?", icon: "badge" },
      { q: "What is the policy on maternal and child health?", icon: "child_care" },
      { q: "How does the Ministry handle disease outbreaks?", icon: "coronavirus" },
    ],
    home_affairs: [
      { q: "How do I replace a lost national ID?", icon: "badge" },
      { q: "What do I need to apply for a passport?", icon: "travel" },
      { q: "How do I register a birth or death?", icon: "description" },
      { q: "What are the immigration rules for visitors?", icon: "flight_land" },
    ],
    finance: [
      { q: "What is in the 2026 National Budget?", icon: "account_balance" },
      { q: "How does the government promote investment?", icon: "trending_up" },
      { q: "What is the public debt situation?", icon: "receipt_long" },
      { q: "What infrastructure programmes are planned?", icon: "construction" },
    ],
    education: [
      { q: "What is the curriculum structure for schools?", icon: "school" },
      { q: "What support is there for early childhood education?", icon: "child_care" },
      { q: "How are schools managed and registered?", icon: "apartment" },
      { q: "What is the BEAM programme for school fees?", icon: "payments" },
    ],
    zimra: [
      { q: "What taxes do employers need to pay?", icon: "payments" },
      { q: "How do I import a car from abroad?", icon: "directions_car" },
      { q: "How do I register a new business for tax?", icon: "storefront" },
      { q: "What are the current customs duty rates?", icon: "receipt_long" },
    ],
    zimsec: [
      { q: "What are the exam regulations for candidates?", icon: "assignment" },
      { q: "How do I register for O-Level exams?", icon: "edit_note" },
      { q: "What special needs provisions does ZIMSEC offer?", icon: "accessibility" },
      { q: "When are exam results released?", icon: "event" },
    ],
    veritas: [
      { q: "What is the Labour Act about?", icon: "gavel" },
      { q: "What does the Constitution say about fundamental rights?", icon: "balance" },
      { q: "What is the Cyber and Data Protection Act?", icon: "shield" },
      { q: "How are statutory instruments published?", icon: "description" },
    ],
  };

  function getExamples(ministryId) {
    return EXAMPLES_BY_MINISTRY[ministryId] || EXAMPLES_BY_MINISTRY[null];
  }

  async function askLive(question, history, ministryFilter, handlers) {
    try {
      const body = JSON.stringify({ question, history: history || [], ministry_filter: ministryFilter || null });
      const res = await fetch("/api/ask/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let sep;
        while ((sep = buf.indexOf("\n\n")) >= 0) {
          const raw = buf.slice(0, sep);
          buf = buf.slice(sep + 2);
          const lines = raw.split("\n").filter((l) => l.startsWith("data:"));
          for (const l of lines) {
            try {
              const obj = JSON.parse(l.slice(5).trim());
              if (obj.type === "delta") { if (handlers.onDelta) handlers.onDelta(obj.text); }
              else if (obj.type === "status") { if (handlers.onStatus) handlers.onStatus(obj.text); }
              else if (obj.type === "done" && handlers.onDone) handlers.onDone(obj);
            } catch(_) {}
          }
        }
      }
    } catch(e) { if (handlers.onError) handlers.onError(e); }
  }

  return { MINISTRIES, byId, getExamples, askLive, META: { docs: 3058, sources: 8, updated: "8 June 2026" } };
})();
