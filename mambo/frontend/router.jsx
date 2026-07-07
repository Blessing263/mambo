/* ============================================================
   "Find the right office" — the flagship routing experience.
   A modal that visibly *reasons* across ministries, then drops
   a routed, cited answer into the conversation.
   ============================================================ */
const { useState: _useStateR, useEffect: _useEffectR, useRef: _useRefR } = React;

function RouterModal({ open, onClose, onRoute }) {
  const D = window.RUZIVO;
  const [val, setVal] = _useStateR("");
  const [phase, setPhase] = _useStateR("idle"); // idle | scanning | done
  const [scanIdx, setScanIdx] = _useStateR(0);
  const data = D.ROUTING.lost_id; // single scripted route for the demo
  const considered = data.considered;

  _useEffectR(() => {
    if (!open) { setPhase("idle"); setVal(""); setScanIdx(0); }
  }, [open]);

  function run(text) {
    const situation = (text || val).trim() || data.situation;
    setVal(situation);
    setPhase("scanning");
    let i = 0;
    const iv = setInterval(() => {
      i++;
      setScanIdx(i % considered.length);
    }, 280);
    setTimeout(() => {
      clearInterval(iv);
      setPhase("done");
    }, 1900);
  }

  function finish() {
    onClose();
    setTimeout(() => onRoute(val || data.situation), 180);
  }

  if (!open) return null;
  const routed = D.byId[data.routed];

  return (
    <div className="rt-overlay fade-in" onClick={phase === "idle" ? onClose : undefined}>
      <div className="rt-modal scale-in" onClick={(e) => e.stopPropagation()}>
        <FlagRibbon height={4} />
        <div className="rt-body">
          <button className="rt-close" onClick={onClose} aria-label="Close"><Ico n="close" style={{ fontSize: 20 }} /></button>

          <div className="rt-head">
            <span className="rt-head-icon"><Ico n="account_tree" fill style={{ fontSize: 22, color: "var(--gold)" }} /></span>
            <div>
              <div className="rt-title">Find the right office</div>
              <div className="rt-sub">Describe your situation — Mambo finds the relevant covered ministry or source.</div>
            </div>
          </div>

          {phase === "idle" && (
            <React.Fragment>
              <textarea className="rt-input" autoFocus rows={2} value={val}
                onChange={(e) => setVal(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); run(); } }}
                placeholder="e.g. I lost my national ID and need a replacement…" />
              <div className="rt-examples">
                {D.ROUTING.examples.map((ex) => (
                  <button key={ex} className="rt-ex" onClick={() => run(ex)}><Ico n="arrow_outward" style={{ fontSize: 15, color: "var(--ink-faint)" }} />{ex}</button>
                ))}
              </div>
              <button className="rt-go" onClick={() => run()}>
                <Ico n="auto_awesome" style={{ fontSize: 18 }} />
                Route my question
              </button>
            </React.Fragment>
          )}

          {phase !== "idle" && (
            <div className="rt-situation">"{val}"</div>
          )}

          {phase === "scanning" && (
            <div className="rt-scan">
              <div className="rt-scan-label">
                <span className="rt-scan-ring" />
                Checking ministry mandates…
              </div>
              <div className="rt-ministry-grid">
                {considered.map((id, i) => {
                  const m = D.byId[id];
                  const active = i === scanIdx;
                  return (
                    <div key={id} className={`rt-min${active ? " active" : ""}`}
                      style={active ? { borderColor: m.color, boxShadow: `0 0 0 1px ${m.color}, 0 8px 22px -10px ${m.color}88` } : undefined}>
                      <span className="src-medallion" style={{ width: 28, height: 28, background: `linear-gradient(135deg, ${m.color}, ${m.color}cc)` }}>
                        <Ico n={m.icon} fill style={{ fontSize: 15, color: "#fff" }} />
                      </span>
                      <span className="rt-min-name">{m.short}</span>
                      {active && <Ico n="radar" className="rt-min-check" style={{ fontSize: 16, color: m.color }} />}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {phase === "done" && (
            <div className="rt-result fade-up">
              <div className="rt-result-badge"><Ico n="check_circle" fill style={{ fontSize: 15 }} />Match found</div>
              <div className="rt-result-card" style={{ borderColor: `${routed.color}55` }}>
                <span className="rt-result-spine flag-ribbon-v" style={{ background: routed.color }} />
                <div className="rt-result-top">
                  <span className="src-medallion" style={{ width: 40, height: 40, background: `linear-gradient(135deg, ${routed.color}, ${routed.color}cc)` }}>
                    <Ico n={routed.icon} fill style={{ fontSize: 21, color: "#fff" }} />
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="rt-result-name">Ministry of {routed.short}</div>
                    <div className="rt-result-dept">{data.department}</div>
                  </div>
                  <div className="rt-conf">
                    <div className="rt-conf-val" style={{ color: routed.color }}>{Math.round(data.confidence * 100)}%</div>
                    <div className="rt-conf-label">match</div>
                  </div>
                </div>
                <div className="rt-conf-bar"><span style={{ width: `${data.confidence * 100}%`, background: routed.color }} /></div>
                <div className="rt-reason"><Ico n="lightbulb" style={{ fontSize: 14, color: "var(--gold)" }} />{data.reason}</div>
              </div>
              <button className="rt-go" onClick={finish}>
                See the steps & contact
                <Ico n="arrow_forward" style={{ fontSize: 18 }} />
              </button>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .rt-overlay {
          position: fixed; inset: 0; z-index: 60; display: grid; place-items: center; padding: 20px;
          background: rgba(4,8,5,0.62); backdrop-filter: blur(6px);
        }
        .rt-modal {
          width: 100%; max-width: 520px; border-radius: var(--r-xl); overflow: hidden;
          background: var(--elev); border: 1px solid var(--line-strong); box-shadow: var(--shadow-lg);
        }
        .rt-body { padding: 22px 22px 22px; position: relative; }
        .rt-close {
          position: absolute; top: 16px; right: 16px; width: 32px; height: 32px; border-radius: 9px;
          border: none; background: var(--surface-2); color: var(--ink-faint); cursor: pointer;
          display: grid; place-items: center; transition: all .15s;
        }
        .rt-close:hover { color: var(--ink); background: var(--surface-3); }
        .rt-head { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 18px; padding-right: 36px; }
        .rt-head-icon { width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center; flex-shrink: 0; background: var(--gold-soft); border: 1px solid var(--line); }
        .rt-title { font-family: var(--font-display); font-weight: 700; font-size: 19px; color: var(--ink); }
        .rt-sub { font-size: 12.5px; color: var(--ink-faint); margin-top: 2px; line-height: 1.4; }
        .rt-input {
          width: 100%; border-radius: var(--r-md); border: 1px solid var(--line-strong); background: var(--surface);
          padding: 12px 14px; font-family: var(--font-ui); font-size: 15px; color: var(--ink); resize: none; outline: none;
          line-height: 1.5; transition: border-color .2s;
        }
        .rt-input:focus { border-color: var(--accent-line); }
        .rt-input::placeholder { color: var(--ink-faint); }
        .rt-examples { display: flex; flex-direction: column; gap: 7px; margin: 12px 0 16px; }
        .rt-ex {
          text-align: left; padding: 10px 13px; border-radius: var(--r-sm); cursor: pointer;
          border: 1px solid var(--line); background: var(--surface); color: var(--ink-soft);
          font-family: var(--font-ui); font-size: 13px; transition: all .15s; display: flex; align-items: center; gap: 8px;
        }
        .rt-ex { padding-left: 13px; }
        .rt-ex:hover { border-color: var(--gold); color: var(--ink); background: var(--gold-soft); }
        .rt-go {
          width: 100%; display: flex; align-items: center; justify-content: center; gap: 9px; cursor: pointer;
          padding: 13px; border-radius: var(--r-md); border: none; color: #fff;
          background: linear-gradient(135deg, var(--accent), var(--accent-deep));
          font-family: var(--font-ui); font-size: 15px; font-weight: 700;
          box-shadow: 0 10px 26px -10px var(--accent-deep); transition: all .16s;
        }
        .rt-go:hover { transform: translateY(-1px); }
        .rt-situation {
          font-family: var(--font-display); font-size: 16px; font-style: italic; color: var(--ink);
          padding: 12px 16px; border-left: 3px solid var(--gold); background: var(--surface);
          border-radius: 0 var(--r-sm) var(--r-sm) 0; margin-bottom: 18px;
        }
        .rt-scan-label { display: flex; align-items: center; gap: 9px; font-size: 13px; color: var(--ink-soft); font-weight: 600; margin-bottom: 14px; }
        .rt-scan-ring { width: 16px; height: 16px; border-radius: 99px; border: 2px solid var(--line-strong); border-top-color: var(--accent); animation: spin .7s linear infinite; }
        .rt-ministry-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .rt-min {
          display: flex; align-items: center; gap: 9px; padding: 9px 11px; border-radius: var(--r-sm);
          border: 1px solid var(--line); background: var(--surface); opacity: 0.55; transition: all .2s var(--ease);
        }
        .rt-min.active { opacity: 1; transform: translateY(-1px); }
        .rt-min-name { font-size: 13px; font-weight: 600; color: var(--ink); flex: 1; }
        .rt-min-check { animation: spin 1.4s linear infinite; }
        .rt-result-badge {
          display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700;
          color: var(--accent); background: var(--accent-tint); padding: 5px 11px; border-radius: var(--r-pill); margin-bottom: 13px;
        }
        .rt-result-card { position: relative; border: 1px solid; border-radius: var(--r-md); background: var(--surface); padding: 15px 16px 15px 18px; overflow: hidden; margin-bottom: 16px; }
        .rt-result-spine { position: absolute; left: 0; top: 0; bottom: 0; width: 4px; }
        .rt-result-top { display: flex; align-items: center; gap: 12px; }
        .rt-result-name { font-family: var(--font-display); font-weight: 700; font-size: 16px; color: var(--ink); }
        .rt-result-dept { font-size: 12.5px; color: var(--ink-soft); margin-top: 1px; }
        .rt-conf { text-align: right; flex-shrink: 0; }
        .rt-conf-val { font-family: var(--font-mono); font-weight: 700; font-size: 20px; line-height: 1; }
        .rt-conf-label { font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-faint); margin-top: 2px; }
        .rt-conf-bar { height: 5px; border-radius: 99px; background: var(--surface-3); margin: 13px 0; overflow: hidden; }
        .rt-conf-bar span { display: block; height: 100%; border-radius: 99px; transition: width .8s var(--ease-out); }
        .rt-reason { display: flex; gap: 8px; align-items: flex-start; font-size: 12.5px; color: var(--ink-soft); line-height: 1.45; }
        @media (max-width: 480px) { .rt-ministry-grid { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
}

/* ---------- In-thread routing message (after the modal resolves) ---------- */
function RoutingMessage({ m }) {
  const D = window.RUZIVO;
  const data = D.ROUTING.lost_id;
  const routed = D.byId[data.routed];
  return (
    <div className="asst fade-up">
      <div className="asst-head">
        <Mark size={26} radius={8} />
        <span className="asst-name" style={{ fontFamily: "var(--font-display)" }}>Mambo</span>
        <span className="route-tag"><Ico n="account_tree" style={{ fontSize: 13 }} />Routed</span>
        <MinistryBadge id={data.routed} />
      </div>

      {/* compact routing recap */}
      {!m.streaming && (
        <div className="route-recap scale-in">
          <span className="src-medallion" style={{ width: 30, height: 30, background: `linear-gradient(135deg, ${routed.color}, ${routed.color}cc)` }}>
            <Ico n={routed.icon} fill style={{ fontSize: 16, color: "#fff" }} />
          </span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--ink)" }}>Ministry of {routed.short} · {data.department}</div>
            <div style={{ fontSize: 11.5, color: "var(--ink-faint)" }}>{Math.round(data.confidence * 100)}% mandate match</div>
          </div>
          <Ico n="verified" fill style={{ fontSize: 18, color: routed.color }} />
        </div>
      )}

      {m.streaming && !m.text ? <TypingDots /> : (
        <div className={m.streaming ? "caret" : ""} style={{ marginTop: 12 }}>
          <AnswerText text={m.text} />
        </div>
      )}

      {!m.streaming && m.meta && (
        <div className="asst-extras">
          <div>
            <div className="sources-label"><Ico n="menu_book" style={{ fontSize: 14 }} />Source</div>
            <div className="cite-grid">{m.meta.citations.map((c, i) => <CitationCard key={i} c={c} index={i} />)}</div>
          </div>
          <ContactCard ministryId={data.routed} />
          <ConfidenceFooter confident={true} answerText={m.text} />
        </div>
      )}

      <style>{`
        .route-tag {
          display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 700;
          color: var(--gold); background: var(--gold-soft); padding: 3px 9px; border-radius: var(--r-pill);
        }
        .route-recap {
          display: flex; align-items: center; gap: 11px; padding: 11px 13px; border-radius: var(--r-md);
          background: var(--surface); border: 1px solid var(--line); margin-bottom: 4px;
        }
      `}</style>
    </div>
  );
}

Object.assign(window, { RouterModal, RoutingMessage });
