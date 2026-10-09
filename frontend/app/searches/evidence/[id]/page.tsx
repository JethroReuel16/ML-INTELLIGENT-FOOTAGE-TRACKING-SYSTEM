
"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  useParams,
  useRouter,
  useSearchParams,
} from "next/navigation";

import {
  getApiBaseUrl,
  getEvidenceUrl,
  getSearchResult,
  VisionTraceMatch,
  VisionTraceResult,
} from "@/services/api";

export default function EvidenceViewerPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();

  const searchId = params?.id as string;
  const requestedRank = Number(
    searchParams.get("rank") || "1"
  );

  const videoRef = useRef<HTMLVideoElement>(null);

  const [result, setResult] =
    useState<VisionTraceResult | null>(null);

  const [currentIndex, setCurrentIndex] =
    useState(0);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] = useState("");
  const [videoError, setVideoError] = useState("");
  const [currentTime, setCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);

  const matches = result?.matches ?? [];
  const currentMatch = matches[currentIndex] ?? null;

  const videoUrl = searchId
    ? `${getApiBaseUrl()}/api/search/${encodeURIComponent(
        searchId
      )}/video`
    : "";

  const evidenceUrl =
    result && currentMatch
      ? getEvidenceUrl(
          result.search_id,
          currentMatch.evidence_image
        )
      : "";

  // Start five seconds before the detected object when requested.
  const getMatchStartTime = useCallback(
    (match: VisionTraceMatch) =>
      Math.max(0, match.timestamp - 5),
    []
  );

  // Load the search result and select the requested candidate.
  useEffect(() => {
    if (!searchId) return;

    let cancelled = false;

    async function loadResult() {
      try {
        setLoading(true);
        setError("");

        const data = await getSearchResult(searchId);

        if (cancelled) return;

        setResult(data);

        const index = (data.matches ?? []).findIndex(
          (match: { rank: number; }) => match.rank === requestedRank
        );

        setCurrentIndex(index >= 0 ? index : 0);
      } catch (err) {
        if (cancelled) return;

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load search evidence."
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadResult();

    return () => {
      cancelled = true;
    };
  }, [searchId, requestedRank]);

  // When the selected candidate changes, reposition the video.
  useEffect(() => {
    const player = videoRef.current;

    if (
      !player ||
      !currentMatch ||
      player.readyState < 1
    ) {
      return;
    }

    player.pause();

    const startTime = getMatchStartTime(currentMatch);

    player.currentTime = startTime;
    setCurrentTime(startTime);
  }, [currentMatch, getMatchStartTime]);

  // Seek to the requested point and optionally start playback.
  // Exact-match playback continues to the end of the original video.
  const seekToMatch = useCallback(
    (
      playAfterSeeking: boolean,
      exactMatch = false
    ) => {
      const player = videoRef.current;

      if (!player || !currentMatch) return;

      const targetTime = exactMatch
        ? currentMatch.timestamp
        : getMatchStartTime(currentMatch);

      let cancelled = false;

      const seekAndPlay = async () => {
        if (cancelled) return;

        const duration = Number.isFinite(player.duration)
          ? player.duration
          : targetTime;

        player.currentTime = Math.min(
          targetTime,
          duration
        );

        setCurrentTime(player.currentTime);
        setVideoError("");

        if (playAfterSeeking) {
          try {
            await player.play();
          } catch {
            setVideoError(
              "Playback could not start automatically. Press Play on the video controls."
            );
          }
        } else {
          player.pause();
        }
      };

      if (player.readyState >= 1) {
        void seekAndPlay();
      } else {
        const onLoadedMetadata = () => {
          void seekAndPlay();
        };

        player.addEventListener(
          "loadedmetadata",
          onLoadedMetadata,
          { once: true }
        );

        // Return value is not used by React, but the listener is
        // removed if the selected candidate changes before metadata loads.
        return () => {
          cancelled = true;
          player.removeEventListener(
            "loadedmetadata",
            onLoadedMetadata
          );
        };
      }
    },
    [currentMatch, getMatchStartTime]
  );

  const goToCandidate = (index: number) => {
    if (
      index < 0 ||
      index >= matches.length
    ) {
      return;
    }

    const nextMatch = matches[index];

    setCurrentIndex(index);

    router.replace(
      `/searches/evidence/${encodeURIComponent(
        searchId
      )}?rank=${nextMatch.rank}`,
      { scroll: false }
    );
  };

  const goPrevious = () => {
    if (matches.length <= 1) return;

    goToCandidate(
      currentIndex === 0
        ? matches.length - 1
        : currentIndex - 1
    );
  };

  const goNext = () => {
    if (matches.length <= 1) return;

    goToCandidate(
      currentIndex === matches.length - 1
        ? 0
        : currentIndex + 1
    );
  };

  const handleLoadedMetadata = () => {
    const player = videoRef.current;

    if (!player) return;

    setVideoDuration(
      Number.isFinite(player.duration)
        ? player.duration
        : 0
    );

    setVideoError("");

    if (currentMatch) {
      const startTime =
        getMatchStartTime(currentMatch);

      player.currentTime = startTime;
      setCurrentTime(startTime);
    }
  };

  const handleVideoError = () => {
    setVideoError(
      "The original video could not be played. Check that the backend is running and the uploaded video still exists."
    );
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-6">
        <div className="text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

          <p className="text-gray-600">
            Loading investigation evidence...
          </p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-6">
        <div className="w-full max-w-lg rounded-2xl border bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-bold text-gray-900">
            Unable to Load Evidence
          </h1>

          <p className="mt-3 text-sm text-red-600">
            {error}
          </p>

          <button
            onClick={() =>
              router.push(
                `/searches/results/${searchId}`
              )
            }
            className="mt-6 rounded-xl bg-black px-6 py-3 font-semibold text-white hover:bg-gray-800"
          >
            Back to Results
          </button>
        </div>
      </main>
    );
  }

  if (!result || !currentMatch) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-6">
        <div className="w-full max-w-lg rounded-2xl border bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-bold text-gray-900">
            No Candidate Evidence
          </h1>

          <p className="mt-3 text-sm text-gray-500">
            This search does not contain a candidate to display.
          </p>

          <button
            onClick={() =>
              router.push(
                `/searches/results/${searchId}`
              )
            }
            className="mt-6 rounded-xl bg-black px-6 py-3 font-semibold text-white hover:bg-gray-800"
          >
            Back to Results
          </button>
        </div>
      </main>
    );
  }

  const progress =
    videoDuration > 0
      ? Math.min(
          100,
          (currentTime / videoDuration) * 100
        )
      : 0;

  const matchPosition =
    videoDuration > 0
      ? Math.min(
          100,
          (currentMatch.timestamp / videoDuration) * 100
        )
      : 0;

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-7xl">
        <header className="mb-7 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <button
              onClick={() =>
                router.push(
                  `/searches/results/${searchId}`
                )
              }
              className="mb-3 text-sm text-gray-500 hover:text-gray-900"
            >
              ← Back to Search Results
            </button>

            <h1 className="text-3xl font-bold text-gray-900">
              Evidence Viewer
            </h1>

            <p className="mt-2 break-all text-sm text-gray-500">
              Search ID: {result.search_id}
            </p>
          </div>

          <button
            onClick={() =>
              router.push("/searches/new")
            }
            className="rounded-xl bg-black px-6 py-3 font-semibold text-white hover:bg-gray-800"
          >
            New Search
          </button>
        </header>

        <section className="mb-6 rounded-2xl border bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-500">
                Selected candidate
              </p>

              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-gray-900 px-3 py-1 text-xs font-semibold text-white">
                  Rank #{currentMatch.rank}
                </span>

                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                  Track {currentMatch.track_id}
                </span>

                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                  {currentMatch.class_name}
                </span>

                <StatusBadge
                  status={currentMatch.match_status}
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={goPrevious}
                disabled={matches.length <= 1}
                className="rounded-xl border px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40"
              >
                ← Previous
              </button>

              <span className="whitespace-nowrap text-sm text-gray-500">
                {currentIndex + 1} of {matches.length}
              </span>

              <button
                onClick={goNext}
                disabled={matches.length <= 1}
                className="rounded-xl bg-black px-4 py-2.5 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </div>
        </section>

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(320px,1fr)]">
          <div className="space-y-6">
            <section className="overflow-hidden rounded-2xl border bg-white shadow-sm">
              <div className="border-b px-5 py-4">
                <h2 className="text-lg font-bold text-gray-900">
                  Original Video Footage
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                  Play the complete original video, seek anywhere
                  in the footage, and continue to the end after
                  reaching a detection.
                </p>
              </div>

              <div className="bg-black">
                <video
                  ref={videoRef}
                  key={videoUrl}
                  src={videoUrl}
                  controls
                  playsInline
                  preload="metadata"
                  onLoadedMetadata={handleLoadedMetadata}
                  onTimeUpdate={(event) =>
                    setCurrentTime(
                      event.currentTarget.currentTime
                    )
                  }
                  onError={handleVideoError}
                  className="max-h-162.5 min-h-60 w-full bg-black"
                />
              </div>

              {videoError && (
                <div className="border-t border-red-200 bg-red-50 p-4 text-sm text-red-700">
                  {videoError}
                </div>
              )}

              <div className="space-y-4 border-t p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                      Detected object timestamp
                    </p>

                    <p className="mt-1 text-xl font-bold text-gray-900">
                      {formatTime(currentMatch.timestamp)}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() =>
                        seekToMatch(true, false)
                      }
                      className="rounded-xl bg-black px-4 py-2.5 text-sm font-semibold text-white hover:bg-gray-800"
                    >
                      ▶ Play from before match
                    </button>

                    <button
                      onClick={() =>
                        seekToMatch(true, true)
                      }
                      className="rounded-xl border px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                    >
                      ▶ Play from exact detection
                    </button>
                  </div>
                </div>

                <div>
                  <div className="mb-2 flex justify-between text-xs text-gray-500">
                    <span>
                      Playback: {formatTime(currentTime)}
                    </span>

                    <span>
                      {videoDuration > 0
                        ? formatTime(videoDuration)
                        : "Duration loading"}
                    </span>
                  </div>

                  <div
                    className="relative h-3 overflow-hidden rounded-full bg-gray-200"
                    aria-label="Video timeline with detected match position"
                    title={`Match found at ${formatTime(
                      currentMatch.timestamp
                    )}`}
                  >
                    <div
                      className="absolute inset-y-0 left-0 rounded-full bg-gray-500"
                      style={{
                        width: `${progress}%`,
                      }}
                    />

                    <div
                      className="absolute bottom-0 top-0 w-1 -translate-x-1/2 rounded bg-red-600"
                      style={{
                        left: `${matchPosition}%`,
                      }}
                    />
                  </div>

                  <p className="mt-2 text-xs text-gray-500">
                    <span className="font-semibold text-red-600">
                      Red marker
                    </span>{" "}
                    indicates where the object was detected.
                  </p>
                </div>
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl border bg-white shadow-sm">
              <div className="border-b px-5 py-4">
                <h2 className="text-lg font-bold text-gray-900">
                  Saved Evidence Image
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                  The candidate image saved by the ML search pipeline.
                </p>
              </div>

              <div className="flex min-h-64 items-center justify-center bg-gray-950 p-4">
                {evidenceUrl ? (
                  <img
                    src={evidenceUrl}
                    alt={`Saved evidence for track ${currentMatch.track_id}`}
                    className="max-h-125 max-w-full rounded-lg object-contain"
                  />
                ) : (
                  <p className="text-sm text-gray-400">
                    Evidence image unavailable
                  </p>
                )}
              </div>
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-2xl border bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900">
                Match Analysis
              </h2>

              <div className="mt-5 space-y-5">
                <ScoreRow
                  label="Visual similarity"
                  value={currentMatch.similarity_score}
                />

                <ScoreRow
                  label="Ranking score"
                  value={currentMatch.ranking_score}
                />

                <ScoreRow
                  label="Top-three average"
                  value={currentMatch.top3_average}
                />

                <ScoreRow
                  label="Average similarity"
                  value={currentMatch.average_similarity}
                />
              </div>

              <p className="mt-5 rounded-xl bg-gray-50 p-3 text-xs leading-5 text-gray-500">
                Similarity scores are visual comparison measurements,
                not calibrated probabilities that the object is an
                exact identity match. Verify candidates against the
                footage.
              </p>
            </section>

            <section className="rounded-2xl border bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900">
                Detection Details
              </h2>

              <div className="mt-5 grid grid-cols-2 gap-3">
                <Detail
                  label="Object class"
                  value={currentMatch.class_name}
                />

                <Detail
                  label="Track ID"
                  value={currentMatch.track_id}
                />

                <Detail
                  label="Candidate rank"
                  value={`#${currentMatch.rank}`}
                />

                <Detail
                  label="Frame number"
                  value={currentMatch.frame_number}
                />

                <Detail
                  label="Detection confidence"
                  value={formatScore(
                    currentMatch.detection_confidence
                  )}
                />

                <Detail
                  label="Frames observed"
                  value={currentMatch.frames_observed}
                />

                <Detail
                  label="Match timestamp"
                  value={formatTime(
                    currentMatch.timestamp
                  )}
                />

                <Detail
                  label="Video FPS"
                  value={result.video.fps}
                />
              </div>

              <div className="mt-4 rounded-xl bg-gray-50 p-4">
                <p className="text-xs text-gray-500">
                  Bounding box [x1, y1, x2, y2]
                </p>

                <p className="mt-2 wrap-break-words font-mono text-sm text-gray-900">
                  [{currentMatch.bbox.join(", ")}]
                </p>
              </div>
            </section>

            <section className="rounded-2xl border bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900">
                Video Information
              </h2>

              <div className="mt-4 space-y-3 text-sm">
                <InfoRow
                  label="Resolution"
                  value={`${result.video.width} × ${result.video.height}`}
                />

                <InfoRow
                  label="Duration"
                  value={formatTime(result.video.duration)}
                />

                <InfoRow
                  label="Total frames"
                  value={result.video.frame_count.toLocaleString()}
                />

                <InfoRow
                  label="Frames analyzed"
                  value={result.search.frames_analyzed.toLocaleString()}
                />
              </div>
            </section>
          </aside>
        </div>

        <footer className="mt-8 flex flex-wrap justify-between gap-3">
          <button
            onClick={() =>
              router.push(
                `/searches/results/${searchId}`
              )
            }
            className="rounded-xl border bg-white px-5 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50"
          >
            ← Back to Results
          </button>

          <div className="flex gap-3">
            <button
              onClick={goPrevious}
              disabled={matches.length <= 1}
              className="rounded-xl border bg-white px-5 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-40"
            >
              Previous Evidence
            </button>

            <button
              onClick={goNext}
              disabled={matches.length <= 1}
              className="rounded-xl bg-black px-5 py-3 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-40"
            >
              Next Evidence →
            </button>
          </div>
        </footer>
      </div>
    </main>
  );
}

function StatusBadge({
  status,
}: {
  status: string;
}) {
  let classes = "bg-gray-100 text-gray-600";

  if (status === "TOP CANDIDATE") {
    classes = "bg-green-100 text-green-800";
  } else if (status === "CANDIDATE") {
    classes = "bg-blue-100 text-blue-800";
  }

  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold ${classes}`}
    >
      {status}
    </span>
  );
}

function Detail({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl bg-gray-50 p-3">
      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="mt-1 wrap-break-word text-sm font-semibold text-gray-900">
        {value}
      </p>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-gray-500">
        {label}
      </span>

      <span className="text-right font-medium text-gray-900">
        {value}
      </span>
    </div>
  );
}

function ScoreRow({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  const percentage = Math.max(
    0,
    Math.min(100, value * 100)
  );

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-sm text-gray-600">
          {label}
        </span>

        <span className="text-sm font-bold text-gray-900">
          {formatScore(value)}
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-black"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>
    </div>
  );
}

function formatScore(value: number): string {
  return Number.isFinite(value)
    ? value.toFixed(4)
    : "N/A";
}

function formatTime(value: number): string {
  if (!Number.isFinite(value) || value < 0) {
    return "00:00";
  }

  const totalSeconds = Math.floor(value);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor(
    (totalSeconds % 3600) / 60
  );
  const seconds = totalSeconds % 60;

  const clock = [minutes, seconds]
    .map((part) => String(part).padStart(2, "0"))
    .join(":");

  return hours > 0
    ? `${String(hours).padStart(2, "0")}:${clock}`
    : clock;
}