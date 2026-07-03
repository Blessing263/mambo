/* ============================================================
   Chat — landing hero, live thread, composer.
   Visual components unchanged; streaming via live RAG API.
   ============================================================ */
const { useState, useRef, useEffect, useMemo } = React;

function Chat({ started, selected, onSelect, messages, busy, onSend, composerRef }) {
  const bottomRef = useRef(null);
  useEffect(() => { bottomRef.current?.scrollTo({ top: bottomRef.current.scrollHeight, behavior: "smooth" }); }, [messages]);

  if (!started) {
    return <Landing selected={selected} onSelect={onSelect} onSend={onSend} busy={busy} />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      <div ref={bottomRef} className="scroll" style={{ flex: 1, overflowY: "auto" }}>
        <div className="thread">
          {messages.map((m) => m.role === "user" ? (
            <div key={m.id} className="user-row fade-up">
              <div className="user-bubble">{m.text}</div>
            </div>
          ) : (
            <AssistantMessage key={m.id} m={m} />
          ))}
        </div>
      </div>
      <Composer selected={selected} onSelect={onSelect} onSend={onSend} busy={busy} inputRef={composerRef} placeholder="Ask a follow-up…" />
    </div>
  );
}

/* ---------- Landing ---------- */
function Landing({ selected, onSelect, onSend, busy }) {
  const [val, setVal] = useState("");
  const D = window.RUZIVO;
  const examples = D.getExamples(selected);
  const ref = useRef(null);
  useEffect(() => { ref.current?.focus(); }, []);
  const submit = () => { if (val.trim()) { onSend(val.trim()); setVal(""); } };

  return (
    <div className="scroll" style={{ flex: 1, overflowY: "auto" }}>
      <div className="landing fade-up">
        <div className="crest">
          <CoatOfArms height={104} glow />
        </div>
        <div className="kicker">
          <span className="flag-ribbon" style={{ width: 26, height: 3, borderRadius: 9 }} />
          Government of Zimbabwe
          <span className="flag-ribbon" style={{ width: 26, height: 3, borderRadius: 9 }} />
        </div>
        <h1 className="hero-h1">
          Ask the Government,<br /><span className="hero-em">get a clear answer.</span>
        </h1>
        <p className="hero-sub">
          Ruzivo answers in plain language using <strong>only official ministry documents</strong> —
          and shows you the source, every time. Free, day and night, on any device.
        </p>
        <div className="ask-wrap">
          <div className="ask-box">
            <textarea ref={ref} value={val}
              onChange={(e) => setVal(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
              rows={1} placeholder="Ask a question in plain language…" className="ask-input"
            />
            <div className="ask-row">
              <button className="send-btn" onClick={submit} disabled={busy || !val.trim()} aria-label="Send">
                {busy ? <span className="spin send-spin" /> : <Ico n="arrow_upward" style={{ fontSize: 19 }} />}
              </button>
            </div>
          </div>
          <div className="ask-hint">
            <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
          </div>
        </div>
        <div className="ex-grid">
          {examples.map((ex, i) => (
            <button key={ex.q} className="ex-card" style={{ animationDelay: `${120 + i * 60}ms` }}
              onClick={() => onSend(ex.q)}>
              <span className="ex-icon"><Ico n={ex.icon} style={{ fontSize: 18 }} /></span>
              <span className="ex-q">{ex.q}</span>
              <Ico n="arrow_outward" className="ex-arrow" style={{ fontSize: 16 }} />
            </button>
          ))}
        </div>
      </div>

      <style>{`
        .landing { max-width: 760px; margin: 0 auto; padding: 40px 22px 56px; text-align: center; }
        .crest { display: flex; justify-content: center; margin-bottom: 18px; }
        .kicker {
          display: inline-flex; align-items: center; gap: 10px; font-size: 12px; font-weight: 700;
          letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-faint); margin-bottom: 16px;
        }
        .hero-h1 {
          font-family: var(--font-display); font-weight: 700; font-size: clamp(34px, 5.2vw, 56px);
          line-height: 1.04; letter-spacing: -0.02em; color: var(--ink); margin: 0 0 18px;
          text-wrap: balance;
        }
        .hero-em { color: var(--accent); font-style: italic; }
        .hero-sub {
          font-size: clamp(15px, 1.8vw, 18px); line-height: 1.6; color: var(--ink-soft);
          max-width: 560px; margin: 0 auto 30px; text-wrap: pretty;
        }
        .hero-sub strong { color: var(--ink); font-weight: 600; }
        .ask-wrap { max-width: 640px; margin: 0 auto; }
        .ask-box {
          background: var(--elev); border: 1px solid var(--line-strong); border-radius: var(--r-lg);
          padding: 14px 14px 12px; box-shadow: var(--shadow-lg); text-align: left;
          transition: border-color .2s;
        }
        .ask-box:focus-within { border-color: var(--accent-line); }
        .ask-input {
          width: 100%; border: none; background: transparent; resize: none; outline: none;
          font-family: var(--font-ui); font-size: 17px; color: var(--ink); line-height: 1.5;
          min-height: 30px; max-height: 160px; padding: 4px 6px;
        }
        .ask-input::placeholder { color: var(--ink-faint); }
        .ask-row { display: flex; align-items: center; justify-content: flex-end; gap: 10px; margin-top: 8px; }
        .send-btn {
          width: 42px; height: 42px; border-radius: 13px; flex-shrink: 0; cursor: pointer; border: none;
          display: grid; place-items: center; color: #fff;
          background: linear-gradient(135deg, var(--accent), var(--accent-deep));
          box-shadow: 0 6px 18px -6px var(--accent-deep); transition: all .16s;
        }
        .send-btn:hover:not(:disabled) { transform: translateY(-1px) scale(1.03); }
        .send-btn:active:not(:disabled) { transform: scale(0.95); }
        .send-btn:disabled { opacity: 0.4; cursor: default; box-shadow: none; }
        .send-spin { width: 18px; height: 18px; border-radius: 99px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; }
        .ask-hint { text-align: center; font-size: 11.5px; color: var(--ink-faint); margin-top: 10px; }
        .ask-hint kbd {
          font-family: var(--font-mono); font-size: 10px; padding: 1px 5px; border-radius: 5px;
          border: 1px solid var(--line); background: var(--surface); color: var(--ink-soft);
        }
        .ex-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 30px; }
        .ex-card {
          display: flex; align-items: center; gap: 11px; text-align: left; cursor: pointer;
          padding: 13px 14px; border-radius: var(--r-md); background: var(--surface);
          border: 1px solid var(--line); transition: all .18s var(--ease); animation: fadeUp .5s var(--ease-out) both;
        }
        .ex-card:hover { border-color: var(--accent-line); transform: translateY(-2px); box-shadow: var(--shadow-md); }
        .ex-icon {
          width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; flex-shrink: 0;
          background: var(--accent-tint); color: var(--accent);
        }
        .ex-q { flex: 1; font-size: 13.5px; font-weight: 500; color: var(--ink-soft); line-height: 1.35; }
        .ex-arrow { color: var(--ink-faint); transition: all .15s; }
        .ex-card:hover .ex-arrow { color: var(--accent); transform: translate(2px, -2px); }
        .ex-card:hover .ex-q { color: var(--ink); }
        .trust-row { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 26px; }
        @media (max-width: 560px) {
          .ex-grid { grid-template-columns: 1fr; }
          .landing { padding: 28px 18px 44px; }
        }
      `}</style>
    </div>
  );
}

/* ---------- Assistant message ---------- */
function AssistantMessage({ m }) {
  const ministries = m.meta?.source_ministry || [];
  return (
    <div className="asst fade-up">
      <div className="asst-head">
        <Mark size={26} radius={8} />
        <span className="asst-name">Ruzivo</span>
        {ministries.map((id) => <MinistryBadge key={id} id={id} />)}
      </div>

      {m.streaming && !m.text ? (
        <TypingDots label="searching official documents…" />
      ) : m.status ? (
        <TypingDots label={m.status} />
      ) : (
        <div className={m.streaming ? "caret" : ""}>
          <AnswerText text={m.text} />
        </div>
      )}

      {!m.streaming && m.meta && (
        <div className="asst-extras">
          {m.meta.citations?.length > 0 && (
            <div>
              <div className="sources-label">
                <Ico n="menu_book" style={{ fontSize: 14 }} />
                {m.meta.citations.length === 1 ? "Source" : `${m.meta.citations.length} sources`}
              </div>
              <div className="cite-grid">
                {m.meta.citations.map((c, i) => <CitationCard key={i} c={c} />)}
              </div>
            </div>
          )}
          {m.meta.fallback_contact?.length > 0 && (
            m.meta.fallback_contact.map((c, i) => <ContactCard key={i} contact={c} />)
          )}
          <ConfidenceFooter confident={m.meta.confident} answerText={m.text} />
        </div>
      )}

      <style>{`
        .asst { margin-bottom: 30px; }
        .asst-head { display: flex; align-items: center; gap: 9px; margin-bottom: 11px; flex-wrap: wrap; }
        .asst-name { font-size: 13.5px; font-weight: 700; color: var(--ink); font-family: var(--font-display); }
        .asst-extras { margin-top: 16px; display: flex; flex-direction: column; gap: 12px; }
        .sources-label {
          display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700;
          letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-faint); margin-bottom: 9px;
        }
        .cite-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }
        @media (max-width: 640px) { .cite-grid { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
}

function TypingDots({ label = "searching official documents…" }) {
  return (
    <div className="typing">
      {[0, 1, 2].map((i) => <span key={i} className="tdot" style={{ animationDelay: `${i * 0.16}s` }} />)}
      <span className="typing-label">{label}</span>
      <style>{`
        .typing { display: flex; align-items: center; gap: 6px; padding: 4px 0; }
        .tdot { width: 7px; height: 7px; border-radius: 99px; background: var(--accent); animation: pulseDot 1.3s ease-in-out infinite; }
        .typing-label { margin-left: 6px; font-size: 12px; color: var(--ink-faint); }
      `}</style>
    </div>
  );
}

/* ---------- Composer ---------- */
function Composer({ selected, onSelect, onSend, busy, inputRef, placeholder }) {
  const [val, setVal] = useState("");
  const D = window.RUZIVO;
  const localRef = useRef(null);
  const ref = inputRef || localRef;
  const submit = () => { if (val.trim() && !busy) { onSend(val.trim()); setVal(""); } };

  return (
    <div className="composer-wrap">
      <div className="composer">
        <div className="composer-box">
          <textarea ref={ref} value={val}
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            rows={1} placeholder={placeholder} className="composer-input"
          />
          <button className="send-btn-sm" onClick={submit} disabled={busy || !val.trim()} aria-label="Send">
            {busy ? <span className="spin send-spin-sm" /> : <Ico n="arrow_upward" style={{ fontSize: 17 }} />}
          </button>
        </div>
        <div className="focus-row scroll">
          <span className="focus-label">Focus</span>
          <button className={`focus-pill${selected === null ? " on" : ""}`} onClick={() => onSelect(null)}>
            <Ico n="public" style={{ fontSize: 14 }} />All of Government
          </button>
          {D.MINISTRIES.slice(0, 6).map((m) => (
            <button key={m.id} className={`focus-pill${selected === m.id ? " on" : ""}`}
              onClick={() => onSelect(selected === m.id ? null : m.id)}
              style={selected === m.id ? { borderColor: m.color, color: m.color, background: `${m.color}1a` } : undefined}>
              {m.short}
            </button>
          ))}
        </div>
      </div>
      <style>{`
        .composer-wrap { border-top: 1px solid var(--line); background: var(--bg); padding: 12px 16px 14px; }
        .composer { max-width: 720px; margin: 0 auto; }
        .composer-box {
          display: flex; align-items: flex-end; gap: 8px; padding: 8px 8px 8px 14px;
          border-radius: var(--r-lg); background: var(--elev); border: 1px solid var(--line-strong);
          box-shadow: var(--shadow-md); transition: border-color .2s;
        }
        .composer-box:focus-within { border-color: var(--accent-line); }
        .composer-input {
          flex: 1; border: none; background: transparent; resize: none; outline: none;
          font-family: var(--font-ui); font-size: 15.5px; color: var(--ink); line-height: 1.5;
          padding: 7px 0; max-height: 140px;
        }
        .composer-input::placeholder { color: var(--ink-faint); }
        .send-btn-sm {
          width: 38px; height: 38px; border-radius: 11px; flex-shrink: 0; cursor: pointer; border: none;
          display: grid; place-items: center; color: #fff;
          background: linear-gradient(135deg, var(--accent), var(--accent-deep)); transition: all .16s;
        }
        .send-btn-sm:hover:not(:disabled) { transform: scale(1.05); }
        .send-btn-sm:disabled { opacity: 0.4; cursor: default; }
        .send-spin-sm { width: 16px; height: 16px; border-radius: 99px; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; }
        .focus-row { display: flex; align-items: center; gap: 6px; margin-top: 9px; overflow-x: auto; padding-bottom: 2px; }
        .focus-label { font-size: 11px; font-weight: 600; color: var(--ink-faint); flex-shrink: 0; margin-right: 2px; }
        .focus-pill {
          display: inline-flex; align-items: center; gap: 5px; flex-shrink: 0; cursor: pointer;
          padding: 5px 11px; border-radius: var(--r-pill); white-space: nowrap;
          border: 1px solid var(--line); background: transparent;
          font-family: var(--font-ui); font-size: 12px; font-weight: 600; color: var(--ink-faint);
          transition: all .15s;
        }
        .focus-pill:hover { color: var(--ink-soft); border-color: var(--line-strong); }
        .focus-pill.on { color: var(--accent); border-color: var(--accent-line); background: var(--accent-tint); }
      `}</style>
    </div>
  );
}

Object.assign(window, { Chat, Landing, AssistantMessage, Composer, TypingDots });
