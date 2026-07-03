"use client";

import type { Ministry } from "@/lib/types";

export function MinistryPicker({
  ministries, selected, onSelect, compact, ministriesLoaded = true,
}: {
  ministries: Ministry[];
  selected: string | null;
  onSelect: (id: string | null) => void;
  compact?: boolean;
  ministriesLoaded?: boolean;
}) {
  if (compact) {
    // While ministries are still loading, render a tiny skeleton row so the
    // user immediately sees that a Focus selector is coming — but doesn't see
    // a phantom selection (which would be confusing on first paint).
    if (!ministriesLoaded && ministries.length === 0) {
      return (
        <div className="flex items-center gap-1 overflow-x-auto scroll-thin" aria-busy="true">
          <span className="skeleton" style={{ height: 22, width: 56, borderRadius: 999 }} />
          <span className="skeleton" style={{ height: 22, width: 64, borderRadius: 999 }} />
          <span className="skeleton" style={{ height: 22, width: 48, borderRadius: 999 }} />
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1 overflow-x-auto scroll-thin">
        {ministries.slice(0, 6).map((m) => (
          <button key={m.id} onClick={() => onSelect(selected === m.id ? null : m.id)}
            className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium transition active:scale-[0.96] whitespace-nowrap"
            style={{
              background: selected === m.id ? `${m.accent_color}20` : "transparent",
              color: selected === m.id ? m.accent_color : "var(--text-tertiary)",
              border: `1px solid ${selected === m.id ? m.accent_color + '44' : 'transparent'}`,
            }}>
            {m.short_name}
          </button>
        ))}
      </div>
    );
  }
  return null;
}
