"use client";

import type {
  AdminQuery,
  AdminQuestion,
  AdminStats,
  MinistryProfile,
  OfficialResponse,
  OfficialResponseVersion,
  ReviewedAnswer,
  Staff,
} from "./types";

async function adm<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/admin${path}`, { credentials: "include", cache: "no-store", ...init });
  if (res.status === 401) { window.location.href = "/admin/login"; throw new Error("unauthorized"); }
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

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
export const getQueries = (limit = 20, offset = 0, q = "") => adm<AdminQuery[]>(`/queries?limit=${limit}&offset=${offset}&q=${encodeURIComponent(q)}`);
export const getQuestions = (limit = 50, offset = 0, q = "", status = "") =>
  adm<AdminQuestion[]>(`/questions?limit=${limit}&offset=${offset}&q=${encodeURIComponent(q)}&status=${encodeURIComponent(status)}`);
export const getReviewed = () => adm<ReviewedAnswer[]>("/reviewed");
export const createReviewed = (body: { question: string; answer: string; citations?: any[] }) =>
  adm<{ id: string }>("/reviewed", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const updateReviewed = (id: string, body: Partial<{ question: string; answer: string; citations: any[]; enabled: boolean }>) =>
  adm<{ ok: true }>(`/reviewed/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const deleteReviewed = (id: string) => adm<{ ok: true }>(`/reviewed/${id}`, { method: "DELETE" });
export const getOfficialResponses = (status = "", q = "") =>
  adm<OfficialResponse[]>(`/official-responses?status=${encodeURIComponent(status)}&q=${encodeURIComponent(q)}`);
export const createOfficialResponse = (body: { question: string; answer: string; citations?: any[]; service_area?: string | null; status?: string }) =>
  adm<OfficialResponse>("/official-responses", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const updateOfficialResponse = (id: string, body: Partial<{ question: string; answer: string; citations: any[]; service_area: string | null; enabled: boolean; change_note: string }>) =>
  adm<OfficialResponse>(`/official-responses/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
export const submitOfficialResponse = (id: string) => adm<OfficialResponse>(`/official-responses/${id}/submit`, { method: "POST" });
export const approveOfficialResponse = (id: string) => adm<OfficialResponse>(`/official-responses/${id}/approve`, { method: "POST" });
export const archiveOfficialResponse = (id: string) => adm<OfficialResponse>(`/official-responses/${id}/archive`, { method: "POST" });
export const getOfficialVersions = (id: string) => adm<OfficialResponseVersion[]>(`/official-responses/${id}/versions`);
export const getMinistryProfile = () => adm<MinistryProfile>("/ministry-profile");
export const updateMinistryProfile = (contact: Record<string, any>) =>
  adm<{ contact: Record<string, any>; updated_at: string | null }>("/ministry-profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contact }),
  });
