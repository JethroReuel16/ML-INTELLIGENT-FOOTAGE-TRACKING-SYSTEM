"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";

import {
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

  const [result, setResult] =
    useState<VisionTraceResult | null>(null);

  const [currentIndex, setCurrentIndex] =
    useState(0);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    if (!searchId) return;

    const loadResult = async () => {
      try {
        setLoading(true);
        setError("");

        const data =
          await getSearchResult(searchId);

        setResult(data);

        const requestedIndex =
          data.matches.findIndex(
            (match: { rank: number; }) =>
              match.rank === requestedRank
          );

        if (requestedIndex >= 0) {
          setCurrentIndex(requestedIndex);
        } else {
          setCurrentIndex(0);
        }
      } catch (err) {
        console.error(err);

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load evidence."
        );
      } finally {
        setLoading(false);
      }
    };

    loadResult();
  }, [searchId, requestedRank]);

  const matches = result?.matches ?? [];

  const currentMatch =
    matches.length > 0
      ? matches[currentIndex]
      : null;

  const evidenceUrl = useMemo(() => {
    if (!result || !currentMatch) {
      return "";
    }

    return getEvidenceUrl(
      result.search_id,
      currentMatch.evidence_image
    );
  }, [result, currentMatch]);

  const goPrevious = () => {
    if (matches.length === 0) return;

    setCurrentIndex((index) =>
      index === 0
        ? matches.length - 1
        : index - 1
    );
  };

  const goNext = () => {
    if (matches.length === 0) return;

    setCurrentIndex((index) =>
      index === matches.length - 1
        ? 0
        : index + 1
    );
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-6">
        <div className="text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

          <p className="text-gray-600">
            Loading evidence...
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
            className="mt-6 rounded-xl bg-black px-6 py-3 font-semibold text-white transition hover:bg-gray-800"
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
            No Evidence Found
          </h1>

          <p className="mt-3 text-sm text-gray-500">
            This search does not contain any
            candidate evidence.
          </p>

          <button
            onClick={() =>
              router.push(
                `/searches/results/${searchId}`
              )
            }
            className="mt-6 rounded-xl bg-black px-6 py-3 font-semibold text-white transition hover:bg-gray-800"
          >
            Back to Results
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-8">
      <div className="mx-auto max-w-7xl">

        {/* HEADER */}
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <button
              onClick={() =>
                router.push(
                  `/searches/results/${searchId}`
                )
              }
              className="mb-3 text-sm text-gray-500 transition hover:text-gray-900"
            >
              ← Back to Results
            </button>

            <h1 className="text-3xl font-bold text-gray-900">
              Evidence Viewer
            </h1>

            <p className="mt-2 text-sm text-gray-500">
              Search ID: {result.search_id}
            </p>
          </div>

          <button
            onClick={() =>
              router.push("/searches/new")
            }
            className="rounded-xl bg-black px-6 py-3 font-semibold text-white transition hover:bg-gray-800"
          >
            New Search
          </button>
        </div>

        {/* CANDIDATE NAVIGATION */}
        <div className="mb-6 flex flex-col gap-4 rounded-2xl border bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-gray-500">
              Evidence Candidate
            </p>

            <p className="mt-1 text-xl font-bold text-gray-900">
              {currentIndex + 1} of {matches.length}
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={goPrevious}
              disabled={matches.length <= 1}
              className="rounded-xl border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ← Previous
            </button>

            <button
              onClick={goNext}
              disabled={matches.length <= 1}
              className="rounded-xl bg-black px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        </div>

        {/* MAIN CONTENT */}
        <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">

          {/* EVIDENCE IMAGE */}
          <section className="overflow-hidden rounded-2xl border bg-white shadow-sm">
            <div className="border-b px-6 py-5">
              <div className="flex flex-wrap items-center gap-2">
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
                  status={
                    currentMatch.match_status
                  }
                />
              </div>
            </div>

            <div className="flex min-h-125 items-center justify-center bg-gray-950 p-4">
              {evidenceUrl ? (
                <img
                  src={evidenceUrl}
                  alt={`Evidence for track ${currentMatch.track_id}`}
                  className="max-h-162.5 max-w-full rounded-lg object-contain"
                />
              ) : (
                <div className="text-gray-400">
                  Evidence image unavailable
                </div>
              )}
            </div>

            <div className="border-t bg-gray-50 px-6 py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
                Evidence File
              </p>

              <p className="mt-1 break-all font-mono text-sm text-gray-700">
                {currentMatch.evidence_image}
              </p>
            </div>
          </section>

          {/* DETAILS */}
          <section className="space-y-6">

            {/* OBJECT INFORMATION */}
            <div className="rounded-2xl border bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900">
                Object Information
              </h2>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <Detail
                  label="Object Class"
                  value={
                    currentMatch.class_name
                  }
                />

                <Detail
                  label="Track ID"
                  value={
                    currentMatch.track_id
                  }
                />

                <Detail
                  label="Rank"
                  value={`#${currentMatch.rank}`}
                />

                <Detail
                  label="Frame Number"
                  value={
                    currentMatch.frame_number
                  }
                />
              </div>
            </div>

            {/* MATCHING ANALYSIS */}
            <div className="rounded-2xl border bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900">
                Matching Analysis
              </h2>

              <div className="mt-5 space-y-5">
                <ScoreRow
                  label="Similarity Score"
                  value={
                    currentMatch.similarity_score
                  }
                />

                <ScoreRow
                  label="Ranking Score"
                  value={
                    currentMatch.ranking_score
                  }
                />

                <ScoreRow
                  label="Top 3 Average"
                  value={
                    currentMatch.top3_average
                  }
                />

                <ScoreRow
                  label="Average Similarity"
                  value={
                    currentMatch.average_similarity
                  }
                />
              </div>
            </div>

            {/* DETECTION INFORMATION */}
            <div className="rounded-2xl border bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900">
                Detection Information
              </h2>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <Detail
                  label="Detection Confidence"
                  value={formatScore(
                    currentMatch.detection_confidence
                  )}
                />

                <Detail
                  label="Frames Observed"
                  value={
                    currentMatch.frames_observed
                  }
                />

                <Detail
                  label="Timestamp"
                  value={formatTime(
                    currentMatch.timestamp
                  )}
                />

                <Detail
                  label="Frame Number"
                  value={
                    currentMatch.frame_number
                  }
                />
              </div>
            </div>

            {/* BOUNDING BOX */}
            <div className="rounded-2xl border bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold text-gray-900">
                Bounding Box
              </h2>

              <div className="mt-4 rounded-xl bg-gray-50 p-4">
                <p className="font-mono text-sm text-gray-900">
                  [
                  {currentMatch.bbox.join(
                    ", "
                  )}
                  ]
                </p>
              </div>

              <p className="mt-3 text-xs text-gray-500">
                Coordinates are represented as
                [x1, y1, x2, y2].
              </p>
            </div>
          </section>
        </div>

        {/* BOTTOM NAVIGATION */}
        <div className="mt-8 flex items-center justify-between rounded-2xl border bg-white p-5 shadow-sm">
          <button
            onClick={goPrevious}
            disabled={matches.length <= 1}
            className="rounded-xl border border-gray-300 px-5 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            ← Previous Evidence
          </button>

          <p className="hidden text-sm text-gray-500 sm:block">
            Candidate {currentIndex + 1} of{" "}
            {matches.length}
          </p>

          <button
            onClick={goNext}
            disabled={matches.length <= 1}
            className="rounded-xl bg-black px-5 py-3 text-sm font-semibold text-white transition hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next Evidence →
          </button>
        </div>
      </div>
    </main>
  );
}

function StatusBadge({
  status,
}: {
  status: string;
}) {
  let classes =
    "bg-gray-100 text-gray-600";

  if (status === "TOP CANDIDATE") {
    classes =
      "bg-green-100 text-green-800";
  }

  if (status === "CANDIDATE") {
    classes =
      "bg-blue-100 text-blue-800";
  }

  if (status === "LOW SIMILARITY") {
    classes =
      "bg-gray-100 text-gray-600";
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
    <div className="rounded-xl bg-gray-50 p-4">
      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="mt-1 font-semibold capitalize text-gray-900">
        {value}
      </p>
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
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm text-gray-600">
          {label}
        </span>

        <span className="font-semibold text-gray-900">
          {value.toFixed(4)}
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-black transition-all"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>
    </div>
  );
}

function formatScore(
  value: number
): string {
  return value.toFixed(4);
}

function formatTime(
  value: number
): string {
  return `${value.toFixed(2)}s`;
}