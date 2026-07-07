/* ============================================================
   Sidebar — national masthead + ministry source list.
   ============================================================ */
const { useState: _useStateSidebar } = React;

function Sidebar({ open, selected, onSelect, onClose, theme, onToggleTheme, onNewChat }) {
  const D = window.RUZIVO;
  return (
    <React.Fragment>
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 35, background: "rgba(0,0,0,0.5)",
          backdropFilter: "blur(2px)", opacity: open ? 1 : 0,
          pointerEvents: open ? "auto" : "none", transition: "opacity .25s",
        }}
        className="sb-overlay"
        aria-hidden="true"
      />
      <aside className={`sb${open ? " sb-open" : ""}`} aria-label="Ministry sources">
        {/* vertical flag accent on the inner edge */}
        <span className="flag-ribbon-v" style={{ position: "absolute", top: 0, right: 0, width: 3, height: "100%", opacity: 0.9 }} />

        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
          {/* Masthead */}
          <div style={{ padding: "18px 18px 16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
              <CoatOfArms height={42} />
              <div style={{ lineHeight: 1.1 }}>
                <Wordmark size={20} />
                <div style={{ fontSize: 10.5, letterSpacing: "0.14em", textTransform: "uppercase",
                  color: "var(--ink-faint)", marginTop: 3, fontWeight: 600 }}>
                  Zimbabwe Public Services
                </div>
              </div>
            </div>

            <button onClick={onNewChat} className="btn-new">
              <Ico n="edit_square" style={{ fontSize: 18 }} />
              New question
            </button>
          </div>

          {/* Sources */}
          <div className="scroll" style={{ flex: 1, overflowY: "auto", padding: "4px 10px 10px" }}>
            <div className="sb-label">Official sources</div>

            <SourceItem
              active={selected === null}
              onClick={() => { onSelect(null); onClose(); }}
              icon="public" label="All of Government" sub="Smart routing" color="var(--accent)"
              allgov
            />

            {D.MINISTRIES.map((m) => (
              <SourceItem
                key={m.id}
                active={selected === m.id}
                onClick={() => { onSelect(m.id); onClose(); }}
                icon={m.icon} label={m.short} sub={m.type} color={m.color}
              />
            ))}
          </div>

          {/* Footer */}
          <div style={{ padding: "12px 16px 16px", borderTop: "1px solid var(--line-soft)" }}>
            <button className="theme-toggle" onClick={onToggleTheme}>
              <Ico n={theme === "dark" ? "light_mode" : "dark_mode"} style={{ fontSize: 17 }} />
              {theme === "dark" ? "Light mode" : "Dark mode"}
              <span style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
                <span className="tog-dot" style={{ background: theme === "dark" ? "var(--gold)" : "var(--line-strong)" }} />
                <span className="tog-dot" style={{ background: theme === "light" ? "var(--accent)" : "var(--line-strong)" }} />
              </span>
            </button>

            <div className="trust-strip">
              <Ico n="verified_user" fill style={{ fontSize: 16, color: "var(--gold)" }} />
              <span>Answers from <strong style={{ color: "var(--ink-soft)", fontWeight: 600 }}>retrieved sources only</strong></span>
            </div>
          </div>
        </div>
      </aside>

      <style>{`
        .sb {
          position: fixed; top: 0; left: 0; bottom: 0; width: 276px; z-index: 40;
          background: var(--elev); border-right: 1px solid var(--line);
          transform: translateX(-100%); transition: transform .28s var(--ease);
        }
        .sb-open { transform: translateX(0); }
        @media (min-width: 1040px) {
          .sb { transform: translateX(0); }
          .sb-overlay { display: none !important; }
        }
        .btn-new {
          margin-top: 16px; width: 100%; display: flex; align-items: center; gap: 9px;
          padding: 10px 14px; border-radius: var(--r-md); cursor: pointer;
          font-family: var(--font-ui); font-size: 14px; font-weight: 600;
          color: var(--ink); background: var(--surface);
          border: 1px solid var(--line); transition: all .18s var(--ease);
        }
        .btn-new:hover { border-color: var(--accent-line); background: var(--surface-2); }
        .btn-new .ms { color: var(--accent); }
        .sb-label {
          font-size: 10.5px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;
          color: var(--ink-faint); padding: 10px 10px 8px;
        }
        .src {
          width: 100%; display: flex; align-items: center; gap: 11px; text-align: left;
          padding: 9px 10px; border-radius: var(--r-sm); cursor: pointer; margin-bottom: 2px;
          background: transparent; border: 1px solid transparent; transition: all .15s var(--ease);
        }
        .src:hover { background: var(--surface); }
        .src-medallion {
          width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center;
          flex-shrink: 0; position: relative;
        }
        .theme-toggle {
          width: 100%; display: flex; align-items: center; gap: 9px; padding: 9px 12px;
          border-radius: var(--r-sm); cursor: pointer; font-family: var(--font-ui);
          font-size: 13px; font-weight: 600; color: var(--ink-soft);
          background: var(--surface); border: 1px solid var(--line); transition: all .18s;
        }
        .theme-toggle:hover { color: var(--ink); border-color: var(--accent-line); }
        .tog-dot { width: 7px; height: 7px; border-radius: 99px; }
        .trust-strip {
          margin-top: 12px; display: flex; align-items: center; gap: 8px;
          padding: 9px 11px; border-radius: var(--r-sm); background: var(--gold-soft);
          font-size: 11.5px; color: var(--ink-faint); line-height: 1.3;
        }
      `}</style>
    </React.Fragment>
  );
}

function SourceItem({ active, onClick, icon, label, sub, color, allgov }) {
  return (
    <button onClick={onClick} className="src"
      style={active ? { background: "var(--surface)", borderColor: "var(--line)" } : undefined}>
      <span className="src-medallion" style={{
        background: allgov
          ? "linear-gradient(135deg, var(--accent-deep), var(--accent))"
          : `linear-gradient(135deg, ${color}, ${color}cc)`,
        boxShadow: active ? `0 0 0 2px ${allgov ? "var(--accent-line)" : color + "66"}` : "var(--shadow-sm)",
      }}>
        <Ico n={icon} fill style={{ fontSize: 17, color: "#fff" }} />
      </span>
      <span style={{ minWidth: 0, flex: 1 }}>
        <span style={{ display: "block", fontSize: 13.5, fontWeight: active ? 700 : 600,
          color: active ? "var(--ink)" : "var(--ink-soft)", lineHeight: 1.25 }}>{label}</span>
        <span style={{ display: "block", fontSize: 11, color: "var(--ink-faint)", lineHeight: 1.2 }}>{sub}</span>
      </span>
      {active && <Ico n="check_circle" style={{ fontSize: 16, color: "var(--accent)" }} />}
    </button>
  );
}

Object.assign(window, { Sidebar });
