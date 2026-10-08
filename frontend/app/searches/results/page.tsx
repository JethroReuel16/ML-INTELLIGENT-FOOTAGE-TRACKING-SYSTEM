"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  getSearchResult,
  VisionTraceResult,
} from "../../../services/api";

export default function ResultsPage() {
  const router = useRouter();

  const [searches, setSearches] = useState<
    VisionTraceResult[]
  >([]);

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    /*
     * Search history/listing will be connected to the
     * backend database later.
     *
     * For now this page serves as the results landing page.
     */

    setLoading(false);
  }, []);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-gray-600">
          Loading searches...
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Search Results
            </h1>

            <p className="mt-2 text-gray-600">
              Review your VisionTrace object searches.
            </p>
          </div>

          <button
            onClick={() => router.push("/searches/new")}
            className="rounded-xl bg-black px-5 py-3 font-semibold text-white hover:bg-gray-800"
          >
            New Search
          </button>
        </div>

        <div className="rounded-2xl border bg-white p-10 text-center shadow-sm">
          <div className="text-5xl">⌕</div>

          <h2 className="mt-4 text-xl font-semibold text-gray-900">
            No searches listed yet
          </h2>

          <p className="mx-auto mt-2 max-w-md text-gray-500">
            Completed searches will appear here once
            search history is connected to the backend.
          </p>

          <button
            onClick={() => router.push("/searches/new")}
            className="mt-6 rounded-xl bg-black px-6 py-3 font-semibold text-white hover:bg-gray-800"
          >
            Start a Search
          </button>
        </div>
      </div>
    </main>
  );
}