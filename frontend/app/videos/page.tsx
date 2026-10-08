"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Video,
  Clock,
  Search,
  Play,
} from "lucide-react";

import {
  getSearchHistory,
  SearchHistoryItem,
} from "../../services/api";

export default function VideosPage() {
  const router = useRouter();

  const [searches, setSearches] =
    useState<SearchHistoryItem[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    const loadVideos = async () => {
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
            : "Unable to load videos."
        );
      } finally {
        setLoading(false);
      }
    };

    loadVideos();
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
              Video Footage
            </h1>

            <p className="mt-2 text-gray-500">
              Video footage processed by VisionTrace
              AI.
            </p>
          </div>

          <button
            onClick={() =>
              router.push("/searches/new")
            }
            className="rounded-xl bg-black px-6 py-3 font-semibold text-white hover:bg-gray-800"
          >
            Process New Video
          </button>
        </header>

        {loading && (
          <div className="rounded-2xl border bg-white p-10 text-center shadow-sm">
            <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

            <p className="text-gray-500">
              Loading video footage...
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
            <h2 className="font-semibold text-red-800">
              Unable to load videos
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
              <Video
                size={42}
                className="mx-auto text-gray-300"
              />

              <h2 className="mt-4 text-xl font-bold text-gray-900">
                No Videos Processed
              </h2>

              <p className="mt-2 text-gray-500">
                Upload video footage to begin an
                object search.
              </p>

              <button
                onClick={() =>
                  router.push("/searches/new")
                }
                className="mt-6 rounded-xl bg-black px-6 py-3 font-semibold text-white"
              >
                Upload Video
              </button>
            </div>
          )}

        {!loading &&
          !error &&
          searches.length > 0 && (
            <div className="overflow-hidden rounded-2xl border bg-white shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="border-b bg-gray-50">
                    <tr>
                      <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Video
                      </th>

                      <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Resolution
                      </th>

                      <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Duration
                      </th>

                      <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Frames
                      </th>

                      <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Status
                      </th>

                      <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Action
                      </th>
                    </tr>
                  </thead>

                  <tbody className="divide-y">
                    {searches.map((search) => (
                      <VideoRow
                        key={search.search_id}
                        search={search}
                        onView={() =>
                          router.push(
                            `/searches/results/${search.search_id}`
                          )
                        }
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
      </div>
    </main>
  );
}

function VideoRow({
  search,
  onView,
}: {
  search: SearchHistoryItem;
  onView: () => void;
}) {
  return (
    <tr className="transition hover:bg-gray-50">

      <td className="px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100">
            <Video
              size={18}
              className="text-gray-700"
            />
          </div>

          <div>
            <p className="font-semibold text-gray-900">
              Video Footage
            </p>

            <p className="max-w-[260px] truncate text-xs text-gray-500">
              {search.search_id}
            </p>
          </div>
        </div>
      </td>

      <td className="px-6 py-5 text-sm text-gray-600">
        {search.video.width} ×{" "}
        {search.video.height}
      </td>

      <td className="px-6 py-5 text-sm text-gray-600">
        {search.video.duration.toFixed(2)}s
      </td>

      <td className="px-6 py-5 text-sm text-gray-600">
        {search.video.frame_count}
      </td>

      <td className="px-6 py-5">
        <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
          Completed
        </span>
      </td>

      <td className="px-6 py-5">
        <button
          onClick={onView}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
        >
          <Play size={14} />
          View
        </button>
      </td>
    </tr>
  );
}