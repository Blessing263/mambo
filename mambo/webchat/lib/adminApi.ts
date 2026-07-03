"use client";

import type { AdminQuery, AdminStats, ReviewedAnswer, Staff } from "./types";

/** Fetch an admin endpoint with the session cookie. On 401 (elsewhere than /me) → redirect to login. */
async function adm<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/admin${path}`, { credentials: "include", cache: "no-store", ...init });
  if (res.status === 401) { window.location.href = "/admin/login"; throw new Error("unauthorized"); }
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

/** /me is special: returns null on 401 (the layout uses it to DECIDE whether to redirect). */
export async function getMe(): Promise<Staff | null> {
  try {
    const res = await fetch("/api/admin/me", { credentials: "include", cache: "no-store" });
    return res.ok ? await res.json() : null;
  } catch { return null; }
}

export const login = (email: string, password: string) =>
  fetch("/api/admin/login", {
    method: "POST", credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
export const logout = () => adm<{ ok: true }>("/logout", { method: "POST" });
export const getStats = (days = 30) => adm<AdminStats>(`/stats?days=${days}`);
export const getQueries = (limit = 20, offset = 0) => adm<AdminQuery[]>(`/queries?limit=${limit}&offset=${offset}`);
export const getReviewed = () => adm<ReviewedAnswer[]>("/reviewed");
export const createReviewed = (body: { question: string; answer: string; citations?: any[] }) =>
  adm<{ id: string }>("/reviewed", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const updateReviewed = (id: string, body: Partial<{ question: string; answer: string; citations: any[]; enabled: boolean }>) =>
  adm<{ ok: true }>(`/reviewed/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const deleteReviewed = (id: string) => adm<{ ok: true }>(`/reviewed/${id}`, { method: "DELETE" });
