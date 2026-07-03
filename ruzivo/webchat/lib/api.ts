import type { DoneMeta, Ministry } from "./types";

let _nonce: string | null = null;
let _nonceExpiry = 0;

async function refreshNonce(): Promise<void> {
  try {
    const res = await fetch("/api/nonce");
    if (!res.ok) return;
    const data = await res.json();
    _nonce = data.nonce;
    _nonceExpiry = Date.now() + (data.expires_in || 300) * 1000;
  } catch { /* best-effort */ }
}

// Eagerly fetch a nonce on module load
refreshNonce();

export async function fetchMinistries(): Promise<Ministry[]> {
  const res = await fetch("/api/ministries", { cache: "no-store" });
  if (!res.ok) throw new Error(`ministries: ${res.status}`);
  return res.json();
}

interface StreamHandlers {
  onDelta: (text: string) => void;
  onDone: (meta: DoneMeta) => void;
  onError: (err: unknown) => void;
}

/** POST /api/ask/stream and parse the Server-Sent Events: delta tokens, then done meta. */
export interface HistoryTurn {
  role: "user" | "assistant";
  content: string;
}

export async function askStream(
  question: string,
  ministryFilter: string | null,
  history: HistoryTurn[],
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  // Backend nonces are single-use, so fetch a FRESH one before every ask (not just
  // when stale). On a 403 (consumed/expired token), refresh and retry once.
  const attempt = async (isRetry: boolean): Promise<void> => {
    await refreshNonce();
    const res = await fetch("/api/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        history,
        ministry_filter: ministryFilter,
        nonce: _nonce,
      }),
      signal,
    });
    if (res.status === 403 && !isRetry) {
      await refreshNonce();
      return attempt(true);
    }
    if (!res.ok || !res.body) {
      handlers.onError(new Error(`ask/stream: ${res.status}`));
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) >= 0) {
        const rawEvent = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const dataLine = rawEvent
          .split("\n")
          .find((l) => l.startsWith("data:"));
        if (!dataLine) continue;
        const payload = JSON.parse(dataLine.slice(5).trim());
        if (payload.type === "delta") handlers.onDelta(payload.text);
        else if (payload.type === "done") handlers.onDone(payload as DoneMeta);
      }
    }
  };

  try {
    await attempt(false);
  } catch (err) {
    if ((err as Error)?.name !== "AbortError") handlers.onError(err);
  }
}
