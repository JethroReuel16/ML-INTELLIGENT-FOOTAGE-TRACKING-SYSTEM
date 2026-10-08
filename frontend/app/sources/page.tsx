"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Camera,
  ArrowLeft,
  Search,
  Video,
  Clock,
} from "lucide-react";

import {
  getSearchHistory,
  SearchHistoryItem,
} from "../../services/api";

export default function SourcesPage() {
  const router = useRouter();

  const [searches, setSearches] =
    useState<SearchHistoryItem[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    const loadSources = async () => {
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
            : "Unable to load video sources."
        );
      } finally {
        setLoading(false);
      }
    };

    loadSources();
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-8">
      <div className="mx-auto max-w-7xl">

        <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
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
              Video Sources
            </h1>

            <p className="mt-2 text-gray-500">
              Video sources used by VisionTrace AI
              searches.
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

        {loading && (
          <div className="rounded-2xl border bg-white p-10 text-center shadow-sm">
            <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

            <p className="text-gray-500">
              Loading video sources...
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
            <h2 className="font-semibold text-red-800">
              Unable to load sources
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
              <Camera
                size={40}
                className="mx-auto text-gray-300"
              />

              <h2 className="mt-4 text-xl font-bold text-gray-900">
                No Video Sources
              </h2>

              <p className="mt-2 text-gray-500">
                Start your first object search to
                add video footage.
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
            <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {searches.map((search) => (
                <SourceCard
                  key={search.search_id}
                  search={search}
                  onView={() =>
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

function SourceCard({
  search,
  onView,
}: {
  search: SearchHistoryItem;
  onView: () => void;
}) {
  const duration =
    search.video.duration || 0;

  return (
    <div className="rounded-2xl border bg-white p-6 shadow-sm transition hover:shadow-md">

      <div className="flex items-start justify-between">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100">
          <Camera
            size={22}
            className="text-gray-700"
          />
        </div>

        <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
          Available
        </span>
      </div>

      <h2 className="mt-5 text-lg font-bold text-gray-900">
        Video Source
      </h2>

      <p className="mt-1 truncate text-xs text-gray-500">
        {search.search_id}
      </p>

      <div className="mt-5 space-y-3">
        <InfoRow
          icon={<Video size={16} />}
          label="Resolution"
          value={`${search.video.width} × ${search.video.height}`}
        />

        <InfoRow
          icon={<Clock size={16} />}
          label="Duration"
          value={`${duration.toFixed(2)} seconds`}
        />

        <InfoRow
          icon={<Search size={16} />}
          label="Searches"
          value="1"
        />
      </div>

      <button
        onClick={onView}
        className="mt-6 w-full rounded-xl border border-gray-300 px-4 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50"
      >
        View Search
      </button>
    </div>
  );
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 text-gray-500">
        {icon}

        <span className="text-sm">
          {label}
        </span>
      </div>

      <span className="text-sm font-semibold text-gray-900">
        {value}
      </span>
    </div>
  );
}