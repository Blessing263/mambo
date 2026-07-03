/* ============================================================
   Answer blocks — prose, citation cards, contact, badges, footer.
   Handles both live RAG API shape and scripted demo data.
   ============================================================ */
const { useState: _useStateAns } = React;

function renderInline(text, key) {
  const nodes = [];
  const pattern = /\*\*(.+?)\*\*|\[(\d+)\]/g;
  let last = 0, i = 0, m;
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    if (m[1] !== undefined) nodes.push(<strong key={`${key}-b${i++}`}>{m[1]}</strong>);
    else nodes.push(<sup key={`${key}-c${i++}`} className="cite-chip">{m[2]}</sup>);
    last = m.index + m[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function AnswerText({ text }) {
  const blocks = text.trim().split(/\n\s*\n/);
  return (
    <div className="prose">
      {blocks.map((block, bi) => {
        const lines = block.split("\n");
        const isList = lines.length > 0 && lines.every((l) => /^\s*[-*]\s+/.test(l));
        if (isList) {
          return <ul key={bi}>{lines.map((l, li) => <li key={li}>{renderInline(l.replace(/^\s*[-*]\s+/, ""), `${bi}-${li}`)}</li>)}</ul>;
        }
        return <p key={bi}>{lines.map((l, li) => <React.Fragment key={li}>{renderInline(l, `${bi}-${li}`)}{li < lines.length - 1 ? <br /> : null}</React.Fragment>)}</p>;
      })}
    </div>
  );
}

function MinistryBadge({ id }) {
  const m = window.RUZIVO.byId[id];
  if (!m) return null;
  return (
    <span className="min-badge" style={{ borderColor: `${m.color}55`, background: `${m.color}1f`, color: "var(--ink)" }}>
      <span className="dot" style={{ background: m.color }} />{m.short}
    </span>
  );
}

function CitationCard({ c, index }) {
  const m = window.RUZIVO.byId[c.ministry];
  const color = m?.color || "#64748b";
  // n from citation array position; pdf tag from URL
  const n = (c.n != null) ? c.n : (index != null ? index + 1 : "");
  const pdf = c.pdf !== undefined ? c.pdf : String(c.url || "").toLowerCase().endsWith(".pdf");
  return (
    <a href={c.url} target="_blank" rel="noopener noreferrer" className="cite-card scale-in"
      style={{ animationDelay: `${(index || 0) * 70}ms` }}>
      <span className="cite-spine" style={{ background: `linear-gradient(180deg, ${color}, ${color}cc)` }} />
      <span className="cite-num" style={{ background: `${color}22`, color }}>{n}</span>
      <span style={{ minWidth: 0, flex: 1 }}>
        <span className="cite-title">{c.title}{pdf ? <span className="pdf-tag">PDF</span> : null}</span>
        <span className="cite-meta">
          <Ico n={m?.icon || "description"} style={{ fontSize: 13, color }} />
          {m?.short || c.ministry}{c.page ? ` · p.${c.page}` : ""}
        </span>
      </span>
      <Ico n="open_in_new" className="cite-open" style={{ fontSize: 16 }} />
    </a>
  );
}

function ContactCard({ ministryId, contact }) {
  let title = null, icon = null, color = "#64748b", rows = [];
  if (contact) {
    // Live API shape: { ministry, phone, whatsapp, email, address, hours }
    const c = contact;
    title = c.ministry || "Ministry";
    rows = [
      ["call", "Phone", c.phone], ["chat", "WhatsApp", c.whatsapp], ["mail", "Email", c.email],
      ["location_on", "Address", c.address], ["schedule", "Hours", c.hours],
    ].filter(([, , v]) => v);
  } else if (ministryId) {
    const m = window.RUZIVO.byId[ministryId];
    if (!m) return null;
    const c = m.contact || {};
    title = m.short; icon = m.icon; color = m.color;
    rows = [
      ["call", "Phone", c.phone], ["chat", "WhatsApp", c.whatsapp], ["mail", "Email", c.email],
      ["location_on", "Address", c.address], ["schedule", "Hours", c.hours], ["language", "Website", c.url],
    ].filter(([, , v]) => v);
  }
  return (
    <div className="contact-card scale-in">
      <div className="contact-head">
        <span className="src-medallion" style={{ background: `linear-gradient(135deg, ${color}, ${color}cc)`, width: 28, height: 28 }}>
          <Ico n={icon || "account_balance"} fill style={{ fontSize: 15, color: "#fff" }} />
        </span>
        <span>
          <span style={{ display: "block", fontSize: 13.5, fontWeight: 700, color: "var(--ink)" }}>How to reach {title}</span>
        </span>
      </div>
      <div className="contact-rows">
        {rows.map(([ic, label, val]) => (
          <div key={label} className="contact-row">
            <Ico n={ic} style={{ fontSize: 15, color: "var(--ink-faint)" }} />
            <span className="contact-label">{label}</span>
            <span className="contact-val">{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConfidenceFooter({ confident, answerText }) {
  const [fb, setFb] = _useStateAns(null);
  const [copied, setCopied] = _useStateAns(false);
  function copy() {
    navigator.clipboard?.writeText(answerText || "").then(() => { setCopied(true); setTimeout(() => setCopied(false), 1600); }).catch(() => {});
  }
  return (
    <div className="ans-footer">
      <span className="ans-scope">
        <Ico n={confident ? "verified" : "info"} fill style={{ fontSize: 14, color: confident ? "var(--accent)" : "var(--gold)" }} />
        {confident ? "Verified against official sources" : "No official source — routed to the ministry"}
      </span>
      <span style={{ display: "flex", gap: 2 }}>
        <button className="icon-btn" onClick={copy} title="Copy answer" aria-label="Copy"
          style={{ color: copied ? "var(--accent)" : undefined }}>
          <Ico n={copied ? "check" : "content_copy"} style={{ fontSize: 16 }} />
        </button>
        {[1, -1].map((v) => (
          <button key={v} className="icon-btn" onClick={() => setFb(fb === v ? null : v)}
            aria-label={v === 1 ? "Helpful" : "Not helpful"}
            style={{ color: fb === v ? (v === 1 ? "var(--accent)" : "var(--red)") : undefined }}>
            <Ico n={v === 1 ? "thumb_up" : "thumb_down"} style={{ fontSize: 16 }} />
          </button>
        ))}
      </span>
    </div>
  );
}
Object.assign(window, { AnswerText, MinistryBadge, CitationCard, ContactCard, ConfidenceFooter });
