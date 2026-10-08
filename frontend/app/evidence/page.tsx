"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  FileSearch,
  Eye,
  Clock,
} from "lucide-react";

import {
  getSearchHistory,
  SearchHistoryItem,
} from "../../services/api";

export default function EvidencePage() {
  const router = useRouter();

  const [searches, setSearches] =
    useState<SearchHistoryItem[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    const loadEvidence = async () => {
      try {
        setLoading(true);
        setError("");

        const data =
          await getSearchHistory();

        setSearches(data);
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

    loadEvidence();
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-8">
      <div className="mx-auto max-w-7xl">

        <header className="mb-8">
          <button
            onClick={() =>
              router.push("/dashboard")
            }
            className="mb-3 flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900"
          >
            <ArrowLeft size={16} />
            Dashboard
          </button>

          <h1 className="text-3xl font-bold text-gray-900">
            Evidence
          </h1>

          <p className="mt-2 text-gray-500">
            Review evidence generated from VisionTrace
            object searches.
          </p>
        </header>

        {loading && (
          <div className="rounded-2xl border bg-white p-10 text-center shadow-sm">
            <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

            <p className="text-gray-500">
              Loading evidence...
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
            <h2 className="font-semibold text-red-800">
              Unable to load evidence
            </h2>

            <p className="mt-2 text-sm text-red-600">
              {error}
            </p>
          </div>
        )}

        {!loading &&
          !error &&
          searches.length === 0 && (
            <div className="rounded-2xl border bg-white p-12 text-center shadow-sm">
              <FileSearch
                size={42}
                className="mx-auto text-gray-300"
              />

              <h2 className="mt-4 text-xl font-bold text-gray-900">
                No Evidence Available
              </h2>

              <p className="mt-2 text-gray-500">
                Evidence will appear here after a
                search is completed.
              </p>

              <button
                onClick={() =>
                  router.push("/searches/new")
                }
                className="mt-6 rounded-xl bg-black px-6 py-3 font-semibold text-white"
              >
                Start Search
              </button>
            </div>
          )}

        {!loading &&
          !error &&
          searches.length > 0 && (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {searches.map((search) => (
                <EvidenceCard
                  key={search.search_id}
                  search={search}
                  onOpen={() =>
                    router.push(
                      `/searches/results/${search.search_id}`
                    )
                  }
                />
              ))}
            </div>
          )}
      </div>
    </main>
  );
}

function EvidenceCard({
  search,
  onOpen,
}: {
  search: SearchHistoryItem;
  onOpen: () => void;
}) {
  const topMatch =
    search.top_match;

  return (
    <div className="overflow-hidden rounded-2xl border bg-white shadow-sm transition hover:shadow-md">

      <div className="flex h-52 items-center justify-center bg-gray-100">
        <FileSearch
          size={48}
          className="text-gray-300"
        />
      </div>

      <div className="p-6">

        <div className="flex items-center justify-between">
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700">
            {search.search.candidates}{" "}
            candidates
          </span>

          <span className="flex items-center gap-1 text-xs text-gray-500">
            <Clock size={13} />

            {search.video.duration.toFixed(
              2
            )}
            s
          </span>
        </div>

        <h2 className="mt-4 font-bold text-gray-900">
          Search Evidence
        </h2>

        <p className="mt-1 truncate font-mono text-xs text-gray-500">
          {search.search_id}
        </p>

        {topMatch ? (
          <div className="mt-5 rounded-xl bg-gray-50 p-4">
            <p className="text-xs text-gray-500">
              Top Candidate
            </p>

            <p className="mt-1 font-semibold capitalize text-gray-900">
              {topMatch.class_name}
            </p>

            <div className="mt-3 grid grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-gray-500">
                  Similarity
                </p>

                <p className="font-bold text-gray-900">
                  {topMatch.similarity_score.toFixed(
                    4
                  )}
                </p>
              </div>

              <div>
                <p className="text-xs text-gray-500">
                  Timestamp
                </p>

                <p className="font-bold text-gray-900">
                  {topMatch.timestamp.toFixed(
                    2
                  )}
                  s
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-5 rounded-xl bg-gray-50 p-4">
            <p className="text-sm text-gray-500">
              No candidate evidence available.
            </p>
          </div>
        )}

        <button
          onClick={onOpen}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-black px-5 py-3 text-sm font-semibold text-white hover:bg-gray-800"
        >
          <Eye size={16} />
          Open Evidence
        </button>
      </div>
    </div>
  );
}