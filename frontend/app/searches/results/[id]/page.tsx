"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import {
  getEvidenceUrl,
  getSearchResult,
  VisionTraceMatch,
  VisionTraceResult,
} from "../../../../services/api";

export default function SearchResultDetailsPage() {
  const params = useParams();
  const router = useRouter();

  const searchId = params?.id as string;

  const [result, setResult] =
    useState<VisionTraceResult | null>(null);

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

        console.log(
          "VISIONTRACE RESULT:",
          data
        );

        setResult(data);
      } catch (err) {
        console.error(err);

        setError(
          err instanceof Error
            ? err.message
            : "Unable to load search result."
        );
      } finally {
        setLoading(false);
      }
    };

    loadResult();
  }, [searchId]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50 px-6">
        <div className="text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

          <p className="text-gray-600">
            Loading VisionTrace results...
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
            Unable to Load Results
          </h1>

          <p className="mt-3 text-sm text-red-600">
            {error}
          </p>

          <button
            onClick={() =>
              router.push("/searches/new")
            }
            className="mt-6 rounded-xl bg-black px-6 py-3 font-semibold text-white transition hover:bg-gray-800"
          >
            Start New Search
          </button>
        </div>
      </main>
    );
  }

  if (!result) {
    return null;
  }

  const matches = result.matches ?? [];

  const topMatch =
    matches.length > 0
      ? matches[0]
      : null;

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-7xl">

        {/* HEADER */}
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <button
              onClick={() =>
                router.push("/searches/new")
              }
              className="mb-3 text-sm text-gray-500 transition hover:text-gray-900"
            >
              ← New Search
            </button>

            <h1 className="text-3xl font-bold text-gray-900">
              Search Results
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

        {/* SUMMARY */}
        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard
            title="Candidates"
            value={
              result.search.candidates
            }
          />

          <SummaryCard
            title="Unique Tracks"
            value={
              result.search.unique_tracks
            }
          />

          <SummaryCard
            title="Frames Analyzed"
            value={
              result.search.frames_analyzed
            }
          />

          <SummaryCard
            title="Status"
            value={result.status}
          />
        </div>

        {/* TOP CANDIDATE */}
        {topMatch && (
          <section className="mb-8 rounded-2xl border bg-white p-6 shadow-sm">
            <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Top Candidate
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                  Highest-ranked visual candidate
                  found in the footage.
                </p>
              </div>

              <button
                onClick={() =>
                  router.push(
                    `/searches/evidence/${searchId}?rank=${topMatch.rank}`
                  )
                }
                className="rounded-xl bg-black px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-gray-800"
              >
                Open Evidence
              </button>
            </div>

            <MatchCard
              match={topMatch}
              searchId={searchId}
              featured
            />
          </section>
        )}

        {/* ALL CANDIDATES */}
        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <div className="mb-6">
            <h2 className="text-xl font-bold text-gray-900">
              All Candidates
            </h2>

            <p className="mt-1 text-sm text-gray-500">
              Candidates ranked by the VisionTrace
              visual similarity pipeline.
            </p>
          </div>

          {matches.length === 0 ? (
            <div className="rounded-xl bg-gray-50 p-10 text-center">
              <p className="font-medium text-gray-900">
                No matching candidates found.
              </p>

              <p className="mt-2 text-sm text-gray-500">
                Try another reference image or
                video.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {matches.map((match) => (
                <MatchCard
                  key={`${match.rank}-${match.track_id}`}
                  match={match}
                  searchId={searchId}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function SummaryCard({
  title,
  value,
}: {
  title: string;
  value: string | number;
}) {
  return (
    <div className="rounded-2xl border bg-white p-5 shadow-sm">
      <p className="text-sm text-gray-500">
        {title}
      </p>

      <p className="mt-2 text-2xl font-bold text-gray-900">
        {value}
      </p>
    </div>
  );
}

function MatchCard({
  match,
  searchId,
  featured = false,
}: {
  match: VisionTraceMatch;
  searchId: string;
  featured?: boolean;
}) {
  const evidenceUrl =
    getEvidenceUrl(
      searchId,
      match.evidence_image
    );

  const evidencePage =
    `/searches/evidence/${searchId}?rank=${match.rank}`;

  return (
    <div
      className={`overflow-hidden rounded-xl border ${
        featured
          ? "border-gray-300"
          : "border-gray-200"
      }`}
    >
      <div className="grid md:grid-cols-[260px_1fr]">

        {/* EVIDENCE IMAGE */}
        <button
          type="button"
          onClick={() =>
            window.location.href =
              evidencePage
          }
          className="group flex min-h-[200px] items-center justify-center bg-gray-100 text-left"
        >
          {evidenceUrl ? (
            <img
              src={evidenceUrl}
              alt={`Evidence for track ${match.track_id}`}
              className="h-full min-h-[200px] w-full object-cover transition duration-200 group-hover:scale-[1.02]"
            />
          ) : (
            <div className="text-sm text-gray-400">
              No evidence image
            </div>
          )}
        </button>

        {/* DETAILS */}
        <div className="p-5">

          <div className="mb-5 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-gray-900 px-3 py-1 text-xs font-semibold text-white">
              #{match.rank}
            </span>

            <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
              Track {match.track_id}
            </span>

            <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
              {match.class_name}
            </span>

            <StatusBadge
              status={match.match_status}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric
              label="Similarity Score"
              value={formatScore(
                match.similarity_score
              )}
            />

            <Metric
              label="Ranking Score"
              value={formatScore(
                match.ranking_score
              )}
            />

            <Metric
              label="Detection Confidence"
              value={formatScore(
                match.detection_confidence
              )}
            />

            <Metric
              label="Frames Observed"
              value={
                match.frames_observed
              }
            />
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Metric
              label="Top 3 Average"
              value={formatScore(
                match.top3_average
              )}
            />

            <Metric
              label="Average Similarity"
              value={formatScore(
                match.average_similarity
              )}
            />

            <Metric
              label="Timestamp"
              value={formatTime(
                match.timestamp
              )}
            />

            <Metric
              label="Frame Number"
              value={
                match.frame_number
              }
            />
          </div>

          <div className="mt-5 rounded-xl bg-gray-50 p-4">
            <p className="text-xs font-medium text-gray-500">
              Detected Bounding Box
            </p>

            <p className="mt-1 font-mono text-sm text-gray-900">
              [{match.bbox.join(", ")}]
            </p>
          </div>

          {/* VIEW EVIDENCE */}
          <div className="mt-5 flex justify-end">
            <button
              type="button"
              onClick={() =>
                window.location.href =
                  evidencePage
              }
              className="rounded-xl bg-black px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-gray-800"
            >
              View Evidence →
            </button>
          </div>
        </div>
      </div>
    </div>
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

function Metric({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg bg-gray-50 p-3">
      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="mt-1 font-bold text-gray-900">
        {value}
      </p>
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