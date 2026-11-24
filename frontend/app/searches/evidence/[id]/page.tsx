"use client";

import {
  ChevronLeft,
  ChevronRight,
  Download,
  Play,
  SkipBack,
  VideoOff,
} from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  EvidenceImage,
  MatchStatusBadge,
  ScoreBar,
} from "@/components/search";
import {
  Button,
  ButtonLink,
  Card,
  CardHeader,
  ErrorState,
  KeyValue,
  LoadingState,
  Page,
  PageHeader,
  buttonClass,
  cn,
} from "@/components/ui";
import { formatClock, formatNumber, formatPercent, isNum } from "@/lib/format";
import {
  getEvidenceUrl,
  getSearchResult,
  getSearchVideoUrl,
  VisionTraceMatch,
} from "@/services/api";
import { useResource } from "@/lib/useResource";

/** Seconds of context shown before a detection. */
const LEAD_IN = 5;

export default function EvidencePage() {
  return (
    <Suspense fallback={<Page><LoadingState label="Loading evidence…" /></Page>}>
      <EvidenceViewer />
    </Suspense>
  );
}

function EvidenceViewer() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  const searchId = params?.id ?? "";
  const requestedRank = Number(searchParams.get("rank") || "1");
  const resultsHref = `/searches/results/${encodeURIComponent(searchId)}`;

  const videoRef = useRef<HTMLVideoElement>(null);

  const fetchResult = useCallback(() => getSearchResult(searchId), [searchId]);
  const { data: result, loading, error, reload } = useResource(fetchResult, !!searchId);
  const [videoFailed, setVideoFailed] = useState(false);
  const [videoNotice, setVideoNotice] = useState("");
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const matches = useMemo(() => result?.matches ?? [], [result]);
  const foundIndex = matches.findIndex((m) => m.rank === requestedRank);
  const index = foundIndex >= 0 ? foundIndex : 0;
  const match: VisionTraceMatch | undefined = matches[index];

  const goTo = useCallback(
    (i: number) => {
      if (matches.length === 0) return;
      const next = matches[(i + matches.length) % matches.length];
      router.replace(`/searches/evidence/${encodeURIComponent(searchId)}?rank=${next.rank}`, {
        scroll: false,
      });
    },
    [matches, router, searchId]
  );

  // Keyboard navigation between candidates.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && ["INPUT", "TEXTAREA", "SELECT", "VIDEO"].includes(el.tagName)) return;
      if (e.key === "ArrowRight") goTo(index + 1);
      if (e.key === "ArrowLeft") goTo(index - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goTo, index]);

  // Cue the player to just before the selected detection.
  useEffect(() => {
    const player = videoRef.current;
    if (!player || !match || player.readyState < 1) return;
    player.pause();
    player.currentTime = Math.max(0, match.timestamp - LEAD_IN);
  }, [match]);

  const seek = useCallback(
    async (time: number, play: boolean) => {
      const player = videoRef.current;
      if (!player) return;

      const apply = async () => {
        const max = Number.isFinite(player.duration) ? player.duration : time;
        player.currentTime = Math.max(0, Math.min(time, max));
        if (!play) return;
        try {
          await player.play();
          setVideoNotice("");
        } catch {
          setVideoNotice("Playback could not start automatically — press play on the video.");
        }
      };

      if (player.readyState >= 1) await apply();
      else player.addEventListener("loadedmetadata", () => void apply(), { once: true });
    },
    []
  );

  if (loading) {
    return (
      <Page>
        <LoadingState label="Loading evidence…" />
      </Page>
    );
  }

  if (error || !result) {
    return (
      <Page>
        <ErrorState
          title="Unable to load evidence"
          message={error || "This search could not be found."}
          onRetry={reload}
          action={<ButtonLink href="/history" variant="ghost">Back to history</ButtonLink>}
        />
      </Page>
    );
  }

  if (!match) {
    return (
      <Page>
        <ErrorState
          title="No evidence to review"
          message="This search did not produce any candidates."
          action={<ButtonLink href={resultsHref} variant="secondary">Back to results</ButtonLink>}
        />
      </Page>
    );
  }

  const evidenceUrl = getEvidenceUrl(result.search_id, match.evidence_image);
  const videoUrl = getSearchVideoUrl(result.search_id);
  const timelineLength = duration || result.video.duration || 0;
  const pct = (t: number) => (timelineLength > 0 ? Math.min(100, (t / timelineLength) * 100) : 0);

  return (
    <Page>
      <PageHeader
        back={{ href: resultsHref, label: "Search results" }}
        title={
          <span className="flex flex-wrap items-center gap-3">
            <span className="capitalize">{match.class_name}</span>
            <span className="font-mono text-lg font-normal text-muted">#{match.rank}</span>
            <MatchStatusBadge status={match.match_status} />
          </span>
        }
        description={`Track ${match.track_id} · first seen at ${formatClock(match.timestamp)} · observed in ${match.frames_observed} frame${match.frames_observed === 1 ? "" : "s"}`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="secondary" icon={ChevronLeft} onClick={() => goTo(index - 1)} disabled={matches.length < 2} aria-label="Previous candidate">
              <span className="hidden sm:inline">Previous</span>
            </Button>
            <span className="px-1 text-sm tabular-nums text-muted">
              {index + 1} / {matches.length}
            </span>
            <Button variant="secondary" onClick={() => goTo(index + 1)} disabled={matches.length < 2} aria-label="Next candidate">
              <span className="hidden sm:inline">Next</span>
              <ChevronRight size={16} aria-hidden />
            </Button>
          </div>
        }
      />

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-6">
          {/* Footage */}
          <Card className="overflow-hidden">
            <CardHeader
              title="Original footage"
              description={`The player is cued ${LEAD_IN}s before the detection.`}
              action={
                !videoFailed && (
                  <>
                    <Button size="sm" variant="secondary" icon={SkipBack} onClick={() => void seek(match.timestamp - LEAD_IN, true)}>
                      From {LEAD_IN}s before
                    </Button>
                    <Button size="sm" icon={Play} onClick={() => void seek(match.timestamp, true)}>
                      At detection
                    </Button>
                  </>
                )
              }
            />

            {videoFailed ? (
              <div className="flex aspect-video flex-col items-center justify-center gap-3 bg-black/60 px-6 text-center">
                <VideoOff size={28} className="text-faint" aria-hidden />
                <p className="text-sm font-medium text-fg-2">Original footage is not available for playback</p>
                <p className="max-w-sm text-xs text-muted">
                  The server could not stream the video for this search. The saved evidence image and
                  detection details below are still available.
                </p>
              </div>
            ) : (
              <video
                ref={videoRef}
                key={videoUrl}
                src={videoUrl}
                controls
                playsInline
                preload="metadata"
                onLoadedMetadata={(e) => {
                  const p = e.currentTarget;
                  setDuration(Number.isFinite(p.duration) ? p.duration : 0);
                  p.currentTime = Math.max(0, match.timestamp - LEAD_IN);
                }}
                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
                onError={() => setVideoFailed(true)}
                className="aspect-video w-full bg-black"
              />
            )}

            {videoNotice && <p className="border-t border-line px-5 py-2 text-xs text-warn">{videoNotice}</p>}

            {/* Timeline with every detection marked */}
            <div className="border-t border-line px-5 py-4">
              <div className="mb-2 flex justify-between font-mono text-xs text-muted">
                <span>{formatClock(currentTime)}</span>
                <span>{timelineLength ? formatClock(timelineLength) : "--:--"}</span>
              </div>
              <div className="relative h-6">
                <button
                  type="button"
                  aria-label="Seek in footage"
                  disabled={videoFailed || !timelineLength}
                  onClick={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    void seek(((e.clientX - rect.left) / rect.width) * timelineLength, false);
                  }}
                  className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 overflow-hidden rounded-full bg-surface-3 disabled:cursor-default"
                >
                  <span className="absolute inset-y-0 left-0 bg-fg-2/40" style={{ width: `${pct(currentTime)}%` }} />
                </button>
                {matches.map((m, i) => (
                  <button
                    key={`${m.rank}-${m.track_id}`}
                    type="button"
                    onClick={() => goTo(i)}
                    title={`#${m.rank} ${m.class_name} at ${formatClock(m.timestamp)}`}
                    aria-label={`Candidate ${m.rank} at ${formatClock(m.timestamp)}`}
                    className={cn(
                      "absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full transition-all",
                      i === index ? "z-10 h-5 w-1.5 bg-accent" : "h-3 w-1 bg-warn/70 hover:h-4 hover:bg-warn"
                    )}
                    style={{ left: `${pct(m.timestamp)}%` }}
                  />
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">
                <span className="mr-1 inline-block h-2 w-2 rounded-full bg-accent align-middle" /> selected candidate
                <span className="ml-4 mr-1 inline-block h-2 w-2 rounded-full bg-warn/70 align-middle" /> other detections — click to jump
              </p>
            </div>
          </Card>

          {/* Candidate strip */}
          {matches.length > 1 && (
            <Card>
              <CardHeader title="All candidates" description="Use ← and → to step through them." />
              <ul className="flex gap-3 overflow-x-auto p-4">
                {matches.map((m, i) => (
                  <li key={`${m.rank}-${m.track_id}`} className="shrink-0">
                    <button
                      type="button"
                      onClick={() => goTo(i)}
                      aria-current={i === index}
                      className={cn(
                        "block w-32 overflow-hidden rounded-lg border text-left transition-colors",
                        i === index ? "border-accent ring-1 ring-accent/50" : "border-line-strong hover:border-fg-2/40"
                      )}
                    >
                      <EvidenceImage
                        src={getEvidenceUrl(result.search_id, m.evidence_image)}
                        alt={`Candidate ${m.rank}`}
                        className="aspect-video w-full"
                      />
                      <span className="flex justify-between px-2 py-1.5 text-xs">
                        <span className="font-mono font-semibold text-fg">#{m.rank}</span>
                        <span className="font-mono text-muted">{formatClock(m.timestamp)}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        {/* Side panel */}
        <aside className="space-y-6">
          <Card className="overflow-hidden">
            <CardHeader
              title="Saved evidence"
              action={
                evidenceUrl && (
                  <a href={evidenceUrl} target="_blank" rel="noreferrer" download className={buttonClass("ghost", "sm")}>
                    <Download size={14} aria-hidden /> Open
                  </a>
                )
              }
            />
            <EvidenceImage
              src={evidenceUrl}
              alt={`Evidence for track ${match.track_id}`}
              fit="contain"
              className="aspect-4/3 w-full"
            />
          </Card>

          <Card>
            <CardHeader title="Match analysis" />
            <div className="space-y-4 p-5">
              {isNum(match.similarity_score) ? (
                <>
                  <ScoreBar label="Visual similarity" value={match.similarity_score} />
                  <ScoreBar label="Top-3 average" value={match.top3_average} />
                  <ScoreBar label="Average similarity" value={match.average_similarity} />
                </>
              ) : (
                <p className="text-sm text-muted">
                  No reference image was used, so this candidate is ranked by detection confidence.
                </p>
              )}
              <ScoreBar label="Detection confidence" value={match.detection_confidence} />
              <p className="rounded-lg bg-surface-2 p-3 text-xs leading-relaxed text-muted">
                Scores measure visual resemblance — they are not a probability of identity. Always verify a
                candidate against the footage.
              </p>
            </div>
          </Card>

          <Card>
            <CardHeader title="Detection details" />
            <dl className="grid grid-cols-2 gap-2 p-4">
              <KeyValue label="Timestamp" value={formatClock(match.timestamp)} mono />
              <KeyValue label="Frame" value={formatNumber(match.frame_number)} mono />
              <KeyValue label="Track ID" value={match.track_id} mono />
              <KeyValue label="Ranking score" value={formatPercent(match.ranking_score)} />
              <div className="col-span-2">
                <KeyValue label="Bounding box (x1, y1, x2, y2)" value={match.bbox.map((v) => Math.round(v)).join(", ")} mono />
              </div>
            </dl>
          </Card>
        </aside>
      </div>
    </Page>
  );
}
