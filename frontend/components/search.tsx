"use client";

/** Search-domain display components shared by results, evidence and history. */

import {
  ChevronRight,
  Clock,
  Film,
  ImageOff,
  Image as ImageIcon,
  Layers,
  Type,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import type { SearchHistoryItem, SearchInputMode } from "@/services/api";
import {
  formatClock,
  formatDuration,
  formatPercent,
  formatRelative,
  formatResolution,
  isNum,
} from "@/lib/format";
import { Badge, cn, type Tone } from "./ui";

/** One search in a list (dashboard + history). */
export function HistoryRow({ item }: { item: SearchHistoryItem }) {
  const top = item.top_match;
  const score = top
    ? isNum(top.similarity_score)
      ? `${formatPercent(top.similarity_score)} similarity`
      : `${formatPercent(top.ranking_score)} confidence`
    : null;
  const failed = item.status && !["completed", "complete", "success"].includes(item.status.toLowerCase());

  return (
    <Link
      href={`/searches/results/${encodeURIComponent(item.search_id)}`}
      className="group flex items-center gap-4 px-5 py-4 transition-colors hover:bg-surface-2"
    >
      <span className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-line-strong bg-surface-2 text-muted sm:flex">
        <Film size={18} aria-hidden />
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-sm font-semibold text-fg">
            {item.search.text_prompt
              ? `“${item.search.text_prompt}”`
              : top?.class_name
                ? `Reference match · ${top.class_name}`
                : "Reference image search"}
          </p>
          <SearchModeBadge mode={item.search.search_mode} />
          {failed && <Badge tone="danger">{item.status}</Badge>}
        </div>
        <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          <span className="inline-flex items-center gap-1">
            <Clock size={12} aria-hidden />
            {formatRelative(item.created_at)}
          </span>
          {item.source && <span className="text-fg-2">{item.source.name}</span>}
          <span>{formatDuration(item.video?.duration)} footage</span>
          <span className="hidden sm:inline">
            {formatResolution(item.video?.width, item.video?.height)}
          </span>
          <span>
            {item.search.candidates} candidate{item.search.candidates === 1 ? "" : "s"}
          </span>
        </p>
      </div>

      <div className="hidden shrink-0 text-right md:block">
        {top ? (
          <>
            <p className="text-sm font-semibold tabular-nums text-fg">{score}</p>
            <p className="mt-0.5 text-xs text-muted">
              Top match at {formatClock(top.timestamp)}
            </p>
          </>
        ) : (
          <p className="text-xs text-faint">No matches</p>
        )}
      </div>

      <ChevronRight
        size={18}
        className="shrink-0 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-fg-2"
        aria-hidden
      />
    </Link>
  );
}

export function matchStatusTone(status: string | undefined): Tone {
  switch ((status || "").toUpperCase()) {
    case "TOP CANDIDATE":
      return "ok";
    case "CANDIDATE":
      return "info";
    case "DETECTED":
      return "accent";
    default:
      return "neutral";
  }
}

export function MatchStatusBadge({ status }: { status: string }) {
  return <Badge tone={matchStatusTone(status)}>{prettyStatus(status)}</Badge>;
}

function prettyStatus(status: string) {
  const lower = (status || "unknown").toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

const MODES: Record<SearchInputMode, { label: string; icon: typeof ImageIcon }> = {
  image: { label: "Image search", icon: ImageIcon },
  text: { label: "Text search", icon: Type },
  image_text: { label: "Image + text", icon: Layers },
};

export function searchModeLabel(mode?: SearchInputMode | null) {
  return MODES[mode ?? "image"]?.label ?? "Image search";
}

export function SearchModeBadge({ mode }: { mode?: SearchInputMode | null }) {
  const entry = MODES[mode ?? "image"] ?? MODES.image;
  return (
    <Badge tone="accent" icon={entry.icon}>
      {entry.label}
    </Badge>
  );
}

/** Horizontal score meter (0–1). */
export function ScoreBar({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | null | undefined;
  hint?: string;
}) {
  const pct = isNum(value) ? Math.max(0, Math.min(100, value * 100)) : 0;

  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <span className="text-sm text-fg-2" title={hint}>
          {label}
        </span>
        <span className="text-sm font-semibold tabular-nums text-fg">
          {formatPercent(value)}
        </span>
      </div>
      <div
        className="h-1.5 overflow-hidden rounded-full bg-surface-3"
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(pct)}
      >
        <div
          className={cn("h-full rounded-full", isNum(value) ? "bg-accent" : "bg-transparent")}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Evidence images are served by the API behind the session cookie, so a
 * plain <img> is used (the Next image optimiser cannot forward cookies).
 */
export function EvidenceImage({
  src,
  alt,
  className,
  fit = "cover",
}: {
  src: string;
  alt: string;
  className?: string;
  fit?: "cover" | "contain";
}) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const failed = !src || failedSrc === src;

  if (failed) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center gap-2 bg-surface-2 text-xs text-faint",
          className
        )}
      >
        <ImageOff size={20} aria-hidden />
        Image unavailable
      </div>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailedSrc(src)}
      className={cn(
        "bg-black",
        fit === "cover" ? "object-cover" : "object-contain",
        className
      )}
    />
  );
}

/** Headline score for a match: similarity when available, else detection confidence. */
export function primaryScore(match: {
  similarity_score: number | null;
  detection_confidence: number;
}) {
  return isNum(match.similarity_score)
    ? { label: "Similarity", value: match.similarity_score }
    : { label: "Confidence", value: match.detection_confidence };
}
