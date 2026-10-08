"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  getSearchHistory,
  SearchHistoryItem,
} from "@/services/api";

export default function HistoryPage() {
  const router = useRouter();

  const [searches, setSearches] = useState<
    SearchHistoryItem[]
  >([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getSearchHistory();

      console.log(
        "VISIONTRACE SEARCH HISTORY:",
        data
      );

      setSearches(data);
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load search history."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleViewResults = (
    searchId: string
  ) => {
    router.push(
      `/searches/results/${searchId}`
    );
  };

  const handleNewSearch = () => {
    router.push("/searches/new");
  };

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-7xl">

        {/* ================================================== */}
        {/* HEADER */}
        {/* ================================================== */}

        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">

          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Search History
            </h1>

            <p className="mt-2 text-gray-600">
              View and manage your previous VisionTrace
              object searches.
            </p>
          </div>

          <button
            type="button"
            onClick={handleNewSearch}
            className="rounded-xl bg-black px-6 py-3 font-semibold text-white transition hover:bg-gray-800"
          >
            + New Search
          </button>
        </div>

        {/* ================================================== */}
        {/* LOADING */}
        {/* ================================================== */}

        {loading && (
          <div className="rounded-2xl border bg-white p-12 text-center shadow-sm">
            <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

            <p className="text-gray-600">
              Loading search history...
            </p>
          </div>
        )}

        {/* ================================================== */}
        {/* ERROR */}
        {/* ================================================== */}

        {!loading && error && (
          <div className="rounded-2xl border border-red-200 bg-white p-8 shadow-sm">

            <div className="rounded-xl bg-red-50 p-5">
              <h2 className="font-semibold text-red-800">
                Unable to load search history
              </h2>

              <p className="mt-2 text-sm text-red-600">
                {error}
              </p>
            </div>

            <button
              type="button"
              onClick={loadHistory}
              className="mt-5 rounded-xl bg-black px-6 py-3 font-semibold text-white hover:bg-gray-800"
            >
              Try Again
            </button>
          </div>
        )}

        {/* ================================================== */}
        {/* EMPTY STATE */}
        {/* ================================================== */}

        {!loading &&
          !error &&
          searches.length === 0 && (
            <div className="rounded-2xl border bg-white p-12 text-center shadow-sm">

              <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-gray-100 text-2xl">
                🔎
              </div>

              <h2 className="text-xl font-bold text-gray-900">
                No searches yet
              </h2>

              <p className="mx-auto mt-2 max-w-md text-gray-500">
                Your completed VisionTrace object searches
                will appear here.
              </p>

              <button
                type="button"
                onClick={handleNewSearch}
                className="mt-6 rounded-xl bg-black px-6 py-3 font-semibold text-white hover:bg-gray-800"
              >
                Start Your First Search
              </button>
            </div>
          )}

        {/* ================================================== */}
        {/* SEARCH LIST */}
        {/* ================================================== */}

        {!loading &&
          !error &&
          searches.length > 0 && (
            <div className="space-y-5">

              {searches.map((search) => (
                <SearchHistoryCard
                  key={search.search_id}
                  search={search}
                  onViewResults={
                    handleViewResults
                  }
                />
              ))}

            </div>
          )}

      </div>
    </main>
  );
}


// ============================================================
// SEARCH HISTORY CARD
// ============================================================

function SearchHistoryCard({
  search,
  onViewResults,
}: {
  search: SearchHistoryItem;
  onViewResults: (
    searchId: string
  ) => void;
}) {
  const topMatch =
    search.top_match;

  return (
    <div className="overflow-hidden rounded-2xl border bg-white shadow-sm transition hover:shadow-md">

      <div className="p-6">

        {/* ================================================== */}
        {/* TOP ROW */}
        {/* ================================================== */}

        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">

          <div>

            <div className="flex flex-wrap items-center gap-2">

              <StatusBadge
                status={search.status}
              />

              {topMatch && (
                <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                  Top:{" "}
                  {topMatch.class_name}
                </span>
              )}

            </div>

            <h2 className="mt-3 break-all text-lg font-bold text-gray-900">
              {search.search_id}
            </h2>

            <p className="mt-1 text-sm text-gray-500">
              {formatDate(
                search.created_at
              )}
            </p>

          </div>

          <button
            type="button"
            onClick={() =>
              onViewResults(
                search.search_id
              )
            }
            className="rounded-xl bg-black px-5 py-3 text-sm font-semibold text-white transition hover:bg-gray-800"
          >
            View Results
          </button>

        </div>

        {/* ================================================== */}
        {/* SEARCH INFORMATION */}
        {/* ================================================== */}

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

          <InfoItem
            label="Candidates"
            value={
              search.search.candidates
            }
          />

          <InfoItem
            label="Unique Tracks"
            value={
              search.search.unique_tracks
            }
          />

          <InfoItem
            label="Frames Analyzed"
            value={
              search.search.frames_analyzed
            }
          />

          <InfoItem
            label="Video Duration"
            value={formatDuration(
              search.video.duration
            )}
          />

        </div>

        {/* ================================================== */}
        {/* TOP MATCH */}
        {/* ================================================== */}

        {topMatch ? (
          <div className="mt-6 rounded-xl bg-gray-50 p-5">

            <div className="mb-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                Top Candidate
              </p>

              <div className="mt-1 flex flex-wrap items-center gap-2">

                <h3 className="font-bold text-gray-900">
                  {topMatch.class_name}
                </h3>

                <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-800">
                  {topMatch.match_status}
                </span>

              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

              <InfoItem
                label="Similarity Score"
                value={formatScore(
                  topMatch.similarity_score
                )}
              />

              <InfoItem
                label="Ranking Score"
                value={formatScore(
                  topMatch.ranking_score
                )}
              />

              <InfoItem
                label="Track ID"
                value={
                  `Track ${topMatch.track_id}`
                }
              />

              <InfoItem
                label="Timestamp"
                value={formatTimestamp(
                  topMatch.timestamp
                )}
              />

            </div>

          </div>
        ) : (
          <div className="mt-6 rounded-xl bg-gray-50 p-5">
            <p className="text-sm text-gray-500">
              No candidate matches were recorded
              for this search.
            </p>
          </div>
        )}

      </div>
    </div>
  );
}


// ============================================================
// INFO ITEM
// ============================================================

function InfoItem({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4">

      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="mt-1 font-bold text-gray-900">
        {value}
      </p>

    </div>
  );
}


// ============================================================
// STATUS BADGE
// ============================================================

function StatusBadge({
  status,
}: {
  status: string;
}) {
  const normalizedStatus =
    status.toLowerCase();

  let classes =
    "bg-gray-100 text-gray-700";

  if (
    normalizedStatus ===
      "completed" ||
    normalizedStatus ===
      "complete"
  ) {
    classes =
      "bg-green-100 text-green-800";
  }

  if (
    normalizedStatus ===
      "failed" ||
    normalizedStatus ===
      "error"
  ) {
    classes =
      "bg-red-100 text-red-800";
  }

  if (
    normalizedStatus ===
      "processing" ||
    normalizedStatus ===
      "running"
  ) {
    classes =
      "bg-yellow-100 text-yellow-800";
  }

  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold ${classes}`}
    >
      {status}
    </span>
  );
}


// ============================================================
// FORMAT DATE
// ============================================================

function formatDate(
  value: string
): string {
  if (!value) {
    return "Unknown date";
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return value;
  }

  return date.toLocaleString(
    undefined,
    {
      dateStyle: "medium",
      timeStyle: "short",
    }
  );
}


// ============================================================
// FORMAT SCORE
// ============================================================

function formatScore(
  value: number
): string {
  if (
    typeof value !== "number" ||
    Number.isNaN(value)
  ) {
    return "N/A";
  }

  return value.toFixed(4);
}


// ============================================================
// FORMAT TIMESTAMP
// ============================================================

function formatTimestamp(
  value: number
): string {
  if (
    typeof value !== "number" ||
    Number.isNaN(value)
  ) {
    return "N/A";
  }

  return `${value.toFixed(2)}s`;
}


// ============================================================
// FORMAT VIDEO DURATION
// ============================================================

function formatDuration(
  seconds: number
): string {
  if (
    typeof seconds !== "number" ||
    Number.isNaN(seconds)
  ) {
    return "N/A";
  }

  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }

  const minutes =
    Math.floor(seconds / 60);

  const remainingSeconds =
    Math.floor(seconds % 60);

  return `${minutes}m ${remainingSeconds}s`;
}