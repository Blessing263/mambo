"use client";

import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const current = document.documentElement.getAttribute("data-theme");
    setDark(current === "dark");
  }, []);

  function toggle() {
    const next = dark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    setDark(!dark);
  }

  return (
    <button
      onClick={toggle}
      className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition active:scale-[0.98]"
      style={{ color: "var(--text-secondary)", background: "var(--bg-hover)" }}
    >
      <span className="material-symbols shrink-0" style={{ fontSize: 20, color: "var(--text-tertiary)" }}>
        {dark ? "light_mode" : "dark_mode"}
      </span>
      <span className="text-[14px] font-medium leading-tight">
        {dark ? "Light mode" : "Dark mode"}
      </span>
    </button>
  );
}
