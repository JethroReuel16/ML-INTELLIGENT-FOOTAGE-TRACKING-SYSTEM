/** Display helpers shared across pages. */

export function isNum(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** 0.8731 → "87.3%"; null → "—" */
export function formatPercent(value: number | null | undefined, digits = 1): string {
  return isNum(value) ? `${(value * 100).toFixed(digits)}%` : "—";
}

/** Raw score with fixed precision; null → "—" */
export function formatScore(value: number | null | undefined, digits = 3): string {
  return isNum(value) ? value.toFixed(digits) : "—";
}

/** Seconds → "mm:ss" or "hh:mm:ss". */
export function formatClock(seconds: number | null | undefined): string {
  if (!isNum(seconds) || seconds < 0) return "00:00";

  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n: number) => String(n).padStart(2, "0");

  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

/** Seconds → "1m 05s" style duration for summaries. */
export function formatDuration(seconds: number | null | undefined): string {
  if (!isNum(seconds) || seconds <= 0) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;

  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);

  if (m < 60) return `${m}m ${String(s).padStart(2, "0")}s`;

  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}m`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  const diff = (Date.now() - date.getTime()) / 1000;

  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} d ago`;

  return formatDateTime(value);
}

export function formatResolution(width?: number, height?: number): string {
  return width && height ? `${width} × ${height}` : "—";
}

export function formatNumber(value: number | null | undefined): string {
  return isNum(value) ? value.toLocaleString() : "—";
}
