"use client";

import { CircleCheck, CircleX, Clock, Plus, SearchX, Target } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useMemo, useState } from "react";

import { EvidenceImage, SearchModeBadge, primaryScore } from "@/components/search";
import {
  Alert,
  Badge,
  ButtonLink,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  LoadingState,
  Page,
  PageHeader,
  cn,
} from "@/components/ui";
import { formatClock, formatDateTime, formatPercent } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import { getEvidenceUrl, getMultiSourceResult } from "@/services/api";

export default function MultiSourceResultsPage() {
  const params = useParams<{ id: string }>();
  const multiId = params?.id ?? "";

  const fetchResult = useCallback(() => getMultiSourceResult(multiId), [multiId]);
  const { data, loading, error, reload } = useResource(fetchResult, !!multiId);
  const [sourceFilter, setSourceFilter] = useState("all");

  const matches = useMemo(
    () =>
      (data?.matches ?? [])
        .map((m, i) => ({ ...m, globalRank: i + 1 }))
        .filter((m) => sourceFilter === "all" || m.source_id === sourceFilter),
    [data, sourceFilter]
  );

  if (loading) {
    return (
      <Page>
        <LoadingState label="Loading combined results…" />
      </Page>
    );
  }

  if (error || !data) {
    return (
      <Page>
        <ErrorState
          title="Unable to load results"
          message={error || "This multi-source search could not be found."}
          onRetry={reload}
          action={<ButtonLink href="/history" variant="ghost">Back to history</ButtonLink>}
        />
      </Page>
    );
  }

  const prompt = data.settings?.text_prompt;

  return (
    <Page>
      <PageHeader
        back={{ href: "/history", label: "Case history" }}
        title={prompt ? `“${prompt}”` : "Multi-source results"}
        description={`Searched ${data.source_count} source${data.source_count === 1 ? "" : "s"} · ${formatDateTime(data.created_at)}`}
        meta={
          <>
            <SearchModeBadge mode={data.settings?.search_mode} />
            <Badge tone="ok">{data.successful_sources} completed</Badge>
            {data.failed_sources > 0 && <Badge tone="danger">{data.failed_sources} failed</Badge>}
          </>
        }
        actions={
          <ButtonLink href="/searches/new" icon={Plus}>
            New search
          </ButtonLink>
        }
      />

      {data.status === "partial" && (
        <Alert tone="warn" className="mb-6" title="Some sources could not be searched">
          Matches from the sources that completed are shown below.
        </Alert>
      )}
      {data.status === "failed" && (
        <Alert tone="error" className="mb-6" title="No source completed successfully">
          Check each source&apos;s status below, test its connection on the Video sources page, then try again.
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="min-w-0">
          <CardHeader
            title={`${data.matches.length} combined candidate${data.matches.length === 1 ? "" : "s"}`}
            description="Ranked together across every source that completed."
          />

          {data.sources.length > 1 && (
            <div className="flex flex-wrap gap-1.5 border-b border-line px-5 py-3">
              {[{ source_id: "all", source_name: "All sources" }, ...data.sources].map((s) => (
                <button
                  key={s.source_id}
                  type="button"
                  aria-pressed={sourceFilter === s.source_id}
                  onClick={() => setSourceFilter(s.source_id)}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs transition-colors",
                    sourceFilter === s.source_id
                      ? "border-accent/50 bg-accent/10 text-accent"
                      : "border-line-strong text-muted hover:text-fg"
                  )}
                >
                  {s.source_name}
                </button>
              ))}
            </div>
          )}

          {matches.length === 0 ? (
            <EmptyState
              icon={SearchX}
              title="No candidates found"
              description="None of the searched footage contained a match. Check the source statuses, or try a different reference."
            />
          ) : (
            <ul className="grid gap-4 p-4 sm:grid-cols-2 xl:grid-cols-3">
              {matches.map((m) => {
                const score = primaryScore(m);
                return (
                  <li key={`${m.search_id}-${m.track_id}-${m.frame_number}`}>
                    <Link
                      href={`/searches/evidence/${encodeURIComponent(m.search_id)}?rank=${m.source_rank ?? m.rank}`}
                      className="group block overflow-hidden rounded-lg border border-line-strong bg-surface-2 transition-colors hover:border-accent/50"
                    >
                      <div className="relative aspect-video">
                        <EvidenceImage
                          src={getEvidenceUrl(m.search_id, m.evidence_image)}
                          alt={`${m.class_name} on ${m.source_name}`}
                          className="h-full w-full transition-transform duration-300 group-hover:scale-[1.03]"
                        />
                        <span className="absolute left-2 top-2 rounded-md bg-black/75 px-2 py-0.5 font-mono text-xs font-semibold text-white">
                          #{m.globalRank}
                        </span>
                        <span className="absolute bottom-2 right-2 inline-flex items-center gap-1 rounded-md bg-black/75 px-2 py-0.5 font-mono text-xs text-white">
                          <Clock size={11} aria-hidden />
                          {formatClock(m.timestamp)}
                        </span>
                      </div>
                      <div className="p-3">
                        <p className="truncate text-sm font-semibold capitalize text-fg">{m.class_name || "Object"}</p>
                        <p className="mt-0.5 truncate text-xs text-muted">{m.source_name}</p>
                        <p className="mt-2 inline-flex items-center gap-1 text-xs text-muted">
                          <Target size={12} aria-hidden />
                          {score.label}{" "}
                          <span className="font-semibold tabular-nums text-fg">{formatPercent(score.value)}</span>
                        </p>
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <aside>
          <Card>
            <CardHeader title="Sources" />
            <ul className="divide-y divide-line">
              {data.sources.map((s) => {
                const ok = s.status === "completed";
                return (
                  <li key={s.source_id} className="flex gap-3 px-5 py-4">
                    {ok ? (
                      <CircleCheck size={18} className="mt-0.5 shrink-0 text-ok" aria-label="Completed" />
                    ) : (
                      <CircleX size={18} className="mt-0.5 shrink-0 text-danger" aria-label="Failed" />
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-fg">{s.source_name}</p>
                      <p className="mt-0.5 text-xs text-muted">
                        {s.source_type.toUpperCase()} · {s.match_count} match{s.match_count === 1 ? "" : "es"}
                      </p>
                      {s.message && <p className={cn("mt-1 wrap-break-word text-xs", ok ? "text-faint" : "text-danger")}>{s.message}</p>}
                      {ok && s.search_id && (
                        <Link
                          href={`/searches/results/${encodeURIComponent(s.search_id)}`}
                          className="mt-1.5 inline-block text-xs font-medium text-accent hover:underline"
                        >
                          View this source&apos;s results →
                        </Link>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>
        </aside>
      </div>
    </Page>
  );
}
