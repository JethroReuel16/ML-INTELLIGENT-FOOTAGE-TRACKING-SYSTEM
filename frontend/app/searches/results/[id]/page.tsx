"use client";

import { Clock, Eye, Plus, SearchX, Target, Trash2, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useMemo, useState } from "react";

import {
  EvidenceImage,
  MatchStatusBadge,
  SearchModeBadge,
  primaryScore,
} from "@/components/search";
import {
  Alert,
  Badge,
  Button,
  ButtonLink,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  KeyValue,
  LoadingState,
  Modal,
  Page,
  PageHeader,
  cn,
} from "@/components/ui";
import {
  formatClock,
  formatDateTime,
  formatDuration,
  formatNumber,
  formatPercent,
  formatResolution,
} from "@/lib/format";
import {
  deleteSearch,
  getEvidenceUrl,
  getSearchResult,
  VisionTraceMatch,
} from "@/services/api";

/** Detector input sizes above this mean the "small objects" option was used. */
const STANDARD_DETECTION_SIZE = 640;
import { useResource } from "@/lib/useResource";

export default function SearchResultPage() {
  const params = useParams<{ id: string }>();
  const searchId = params?.id ?? "";

  const fetchResult = useCallback(() => getSearchResult(searchId), [searchId]);
  const { data: result, loading, error, reload } = useResource(fetchResult, !!searchId);
  const router = useRouter();
  const [classFilter, setClassFilter] = useState("all");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  async function handleDelete() {
    setDeleting(true);
    setDeleteError("");
    try {
      await deleteSearch(searchId);
      router.replace("/history");
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Unable to delete this search.");
      setDeleting(false);
    }
  }

  const matches = useMemo(() => result?.matches ?? [], [result]);
  const classes = useMemo(
    () => Array.from(new Set(matches.map((m) => m.class_name).filter(Boolean))).sort(),
    [matches]
  );
  const visible =
    classFilter === "all" ? matches : matches.filter((m) => m.class_name === classFilter);

  if (loading) {
    return (
      <Page>
        <LoadingState label="Loading search results…" />
      </Page>
    );
  }

  if (error || !result) {
    return (
      <Page>
        <ErrorState
          title="Unable to load results"
          message={error || "This search could not be found."}
          onRetry={reload}
          action={
            <ButtonLink href="/history" variant="ghost">
              Back to history
            </ButtonLink>
          }
        />
      </Page>
    );
  }

  const { search, video } = result;
  const prompt = search.text_prompt ?? result.reference?.text_prompt;
  const textOnly = search.ranking_basis === "detection_confidence";
  const smallObjects = (search.detection_size ?? 0) > STANDARD_DETECTION_SIZE;
  const evidenceHref = (m: VisionTraceMatch) =>
    `/searches/evidence/${encodeURIComponent(result.search_id)}?rank=${m.rank}`;

  return (
    <Page>
      <PageHeader
        back={{ href: "/history", label: "Case history" }}
        title={prompt ? `“${prompt}”` : "Search results"}
        description={`Run ${formatDateTime(result.created_at)}${result.source?.name ? ` on ${result.source.name}` : ""}`}
        meta={
          <>
            <SearchModeBadge mode={search.search_mode} />
            {result.source?.source_type && (
              <Badge>{String(result.source.source_type).toUpperCase()}</Badge>
            )}
            {search.detector && (
              <Badge tone={search.detector.fallback ? "warn" : "neutral"}>
                Detector: {search.detector.active}
                {search.detector.fallback ? " (fallback)" : ""}
              </Badge>
            )}
            {smallObjects && <Badge tone="info">Small objects</Badge>}
          </>
        }
        actions={
          <>
            <Button variant="ghost" icon={Trash2} onClick={() => setConfirmDelete(true)} aria-label="Delete search">
              <span className="hidden sm:inline">Delete</span>
            </Button>
            {matches.length > 0 && (
              <ButtonLink href={evidenceHref(matches[0])} variant="secondary" icon={Eye}>
                Review evidence
              </ButtonLink>
            )}
            <ButtonLink href="/searches/new" icon={Plus}>
              New search
            </ButtonLink>
          </>
        }
      />

      {search.detector?.fallback && search.detector.fallback_reason && (
        <div className="mb-6 flex gap-3 rounded-lg border border-warn/35 bg-warn/10 px-4 py-3 text-sm text-fg-2">
          <TriangleAlert size={18} className="shrink-0 text-warn" aria-hidden />
          The preferred detector was unavailable, so a fallback was used: {search.detector.fallback_reason}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
        {/* Candidates */}
        <Card className="min-w-0">
          <CardHeader
            title={`${matches.length} candidate${matches.length === 1 ? "" : "s"}`}
            description={
              textOnly
                ? "Ranked by detection confidence (no reference image was provided)."
                : "Ranked by visual similarity to your reference image."
            }
          />

          {classes.length > 1 && (
            <div className="flex flex-wrap gap-1.5 border-b border-line px-5 py-3">
              {["all", ...classes].map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setClassFilter(c)}
                  aria-pressed={classFilter === c}
                  className={cn(
                    "rounded-full border px-3 py-1 text-xs capitalize transition-colors",
                    classFilter === c
                      ? "border-accent/50 bg-accent/10 text-accent"
                      : "border-line-strong text-muted hover:text-fg"
                  )}
                >
                  {c === "all" ? `All (${matches.length})` : c}
                </button>
              ))}
            </div>
          )}

          {visible.length === 0 ? (
            <EmptyState
              icon={SearchX}
              title="No candidates found"
              description={
                smallObjects
                  ? "Nothing in this footage matched. Try a clearer reference image, a different description, or a lower minimum confidence."
                  : "Nothing in this footage matched. If the object is small in the frame (a shoe, phone or watch), run the search again with “Detect small objects” under Advanced settings, or lower the minimum confidence."
              }
              action={
                <ButtonLink href="/searches/new" icon={Plus}>
                  Try another search
                </ButtonLink>
              }
            />
          ) : (
            <ul className="grid gap-4 p-4 sm:grid-cols-2 xl:grid-cols-3">
              {visible.map((m) => (
                <li key={`${m.rank}-${m.track_id}`}>
                  <CandidateCard
                    match={m}
                    href={evidenceHref(m)}
                    image={getEvidenceUrl(result.search_id, m.evidence_image)}
                  />
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Summary */}
        <aside className="space-y-6">
          <Card>
            <CardHeader title="Search summary" />
            <dl className="grid grid-cols-2 gap-2 p-4">
              <KeyValue label="Frames analysed" value={formatNumber(search.frames_analyzed)} />
              <KeyValue label="Unique tracks" value={formatNumber(search.unique_tracks)} />
              <KeyValue label="Observations" value={formatNumber(search.candidate_observations)} />
              <KeyValue label="Frame interval" value={`Every ${search.frame_interval}`} />
              <KeyValue label="Min. confidence" value={formatPercent(search.minimum_detection_confidence, 0)} />
              <KeyValue label="Status" value={result.status} />
            </dl>
          </Card>

          <Card>
            <CardHeader title="Footage" />
            <dl className="grid grid-cols-2 gap-2 p-4">
              <KeyValue label="Duration" value={formatDuration(video.duration)} />
              <KeyValue label="Resolution" value={formatResolution(video.width, video.height)} />
              <KeyValue label="Frame rate" value={video.fps ? `${video.fps.toFixed(1)} fps` : "—"} />
              <KeyValue label="Total frames" value={formatNumber(video.frame_count)} />
            </dl>
            <p className="border-t border-line px-4 py-3 font-mono text-[11px] text-faint" title={result.search_id}>
              ID {result.search_id}
            </p>
          </Card>
        </aside>
      </div>

      <Modal
        open={confirmDelete}
        onClose={() => !deleting && setConfirmDelete(false)}
        title="Delete this search?"
        size="sm"
        description="The results, all evidence images and the stored footage for this search are permanently removed. This cannot be undone."
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDelete(false)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="danger" icon={Trash2} loading={deleting} onClick={() => void handleDelete()}>
              Delete search
            </Button>
          </>
        }
      >
        {deleteError && <Alert tone="error">{deleteError}</Alert>}
      </Modal>
    </Page>
  );
}

function CandidateCard({
  match,
  href,
  image,
}: {
  match: VisionTraceMatch;
  href: string;
  image: string;
}) {
  const score = primaryScore(match);

  return (
    <Link
      href={href}
      className="group block overflow-hidden rounded-lg border border-line-strong bg-surface-2 transition-colors hover:border-accent/50"
    >
      <div className="relative aspect-video">
        <EvidenceImage
          src={image}
          alt={`${match.class_name} candidate, track ${match.track_id}`}
          className="h-full w-full transition-transform duration-300 group-hover:scale-[1.03]"
        />
        <span className="absolute left-2 top-2 rounded-md bg-black/75 px-2 py-0.5 font-mono text-xs font-semibold text-white">
          #{match.rank}
        </span>
        <span className="absolute bottom-2 right-2 inline-flex items-center gap-1 rounded-md bg-black/75 px-2 py-0.5 font-mono text-xs text-white">
          <Clock size={11} aria-hidden />
          {formatClock(match.timestamp)}
        </span>
      </div>
      <div className="p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm font-semibold capitalize text-fg">{match.class_name}</p>
          <MatchStatusBadge status={match.match_status} />
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-muted">
          <span className="inline-flex items-center gap-1">
            <Target size={12} aria-hidden />
            {score.label} <span className="font-semibold tabular-nums text-fg">{formatPercent(score.value)}</span>
          </span>
          <span>Track {match.track_id}</span>
        </div>
      </div>
    </Link>
  );
}
