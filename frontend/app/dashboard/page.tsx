"use client";

import {
  Activity,
  Camera,
  FileSearch,
  FolderSearch,
  Search,
  ShieldCheck,
  Video,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  getSearchHistory,
  SearchHistoryItem,
} from "../../services/api";

export default function DashboardPage() {
  const router = useRouter();

  const [searches, setSearches] = useState<
    SearchHistoryItem[]
  >([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const data =
        await getSearchHistory();

      console.log(
        "VISIONTRACE DASHBOARD DATA:",
        data
      );

      setSearches(data);
    } catch (err) {
      console.error(err);

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load dashboard data."
      );
    } finally {
      setLoading(false);
    }
  };

  // ==========================================================
  // REAL DASHBOARD STATISTICS
  // ==========================================================

  const totalSearches =
    searches.length;

  const totalCandidates =
    searches.reduce(
      (total, search) =>
        total +
        (search.search.candidates || 0),
      0
    );

  const totalTracks =
    searches.reduce(
      (total, search) =>
        total +
        (search.search.unique_tracks || 0),
      0
    );

  /*
   * The current backend stores searches and
   * their video information, but it does not
   * have a separate video-source database yet.
   *
   * Therefore we use the number of searches
   * with video data as the current source
   * indicator.
   */
  const videoSources =
    searches.length;

  const recentSearches =
    searches.slice(0, 5);

  return (
    <main className="min-h-screen bg-slate-100">
      <div className="flex">

        {/* ================================================== */}
        {/* SIDEBAR */}
        {/* ================================================== */}

        <aside className="hidden md:flex w-64 min-h-screen bg-slate-950 text-white flex-col">

          <div className="p-6 border-b border-slate-800">
            <div className="flex items-center gap-3">

              <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center">
                <Search size={22} />
              </div>

              <div>
                <h1 className="font-bold">
                  VisionTrace
                </h1>

                <p className="text-xs text-slate-400">
                  AI Investigation
                </p>
              </div>

            </div>
          </div>

          <nav className="p-4 space-y-2">

            <NavItem
              icon={
                <Activity size={19} />
              }
              label="Dashboard"
              active
              onClick={() =>
                router.push(
                  "/dashboard"
                )
              }
            />

            <NavItem
              icon={
                <Search size={19} />
              }
              label="Object Search"
              onClick={() =>
                router.push(
                  "/searches/new"
                )
              }
            />

            <NavItem
              icon={
                <Camera size={19} />
              }
              label="Video Sources"
              onClick={() =>
                router.push(
                  "/sources"
                )
              }
            />

            <NavItem
              icon={
                <Video size={19} />
              }
              label="Videos"
              onClick={() =>
                router.push(
                  "/videos"
                )
              }
            />

            <NavItem
              icon={
                <FileSearch size={19} />
              }
              label="Evidence"
              onClick={() =>
                router.push(
                  "/evidence"
                )
              }
            />

            <NavItem
              icon={
                <FolderSearch size={19} />
              }
              label="Search History"
              onClick={() =>
                router.push(
                  "/history"
                )
              }
            />

          </nav>

          {/* System Status */}

          <div className="mt-auto p-4 border-t border-slate-800">

            <div className="text-sm">

              <p className="font-medium">
                System Status
              </p>

              <div className="flex items-center gap-2 mt-2 text-emerald-400">

                <span className="w-2 h-2 rounded-full bg-emerald-400" />

                All systems operational

              </div>

            </div>

          </div>

        </aside>

        {/* ================================================== */}
        {/* MAIN CONTENT */}
        {/* ================================================== */}

        <section className="flex-1">

          {/* HEADER */}

          <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">

            <div>

              <h2 className="text-xl font-semibold text-slate-900">
                Dashboard
              </h2>

              <p className="text-sm text-slate-500">
                Intelligent video investigation workspace
              </p>

            </div>

            <div className="flex items-center gap-3">

              <div className="hidden sm:block text-right">

                <p className="text-sm font-semibold text-slate-900">
                  Investigator
                </p>

                <p className="text-xs text-slate-500">
                  Authorized User
                </p>

              </div>

              <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-semibold">
                IV
              </div>

            </div>

          </header>

          <div className="p-6">

            {/* ================================================== */}
            {/* WELCOME */}
            {/* ================================================== */}

            <div className="mb-7">

              <h1 className="text-2xl font-bold text-slate-900">
                Good afternoon
              </h1>

              <p className="text-slate-500 mt-1">
                Search your video footage intelligently.
              </p>

            </div>

            {/* ================================================== */}
            {/* ERROR */}
            {/* ================================================== */}

            {error && (
              <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-5">

                <p className="font-semibold text-red-800">
                  Unable to load dashboard data
                </p>

                <p className="mt-1 text-sm text-red-600">
                  {error}
                </p>

                <button
                  type="button"
                  onClick={loadDashboard}
                  className="mt-4 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
                >
                  Try Again
                </button>

              </div>
            )}

            {/* ================================================== */}
            {/* STATS */}
            {/* ================================================== */}

            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">

              <DashboardStat
                title="Total Searches"
                value={
                  loading
                    ? "..."
                    : totalSearches
                }
                icon={FolderSearch}
              />

              <DashboardStat
                title="Video Sources"
                value={
                  loading
                    ? "..."
                    : videoSources
                }
                icon={Camera}
              />

              <DashboardStat
                title="Objects Tracked"
                value={
                  loading
                    ? "..."
                    : totalTracks
                }
                icon={Video}
              />

              <DashboardStat
                title="Matches Found"
                value={
                  loading
                    ? "..."
                    : totalCandidates
                }
                icon={FileSearch}
              />

            </div>

            {/* ================================================== */}
            {/* NEW SEARCH */}
            {/* ================================================== */}

            <div className="mt-6 bg-slate-950 rounded-2xl p-7 text-white flex flex-col lg:flex-row lg:items-center justify-between gap-5">

              <div>

                <h2 className="text-xl font-semibold">
                  Search for an object
                </h2>

                <p className="text-slate-400 mt-1">
                  Upload a reference image and search your
                  video footage.
                </p>

              </div>

              <button
                type="button"
                onClick={() =>
                  router.push(
                    "/searches/new"
                  )
                }
                className="bg-indigo-600 hover:bg-indigo-700 px-6 py-3 rounded-xl font-semibold transition"
              >
                + New Object Search
              </button>

            </div>

            {/* ================================================== */}
            {/* RECENT SEARCHES */}
            {/* ================================================== */}

            <div className="mt-8">

              <div className="flex items-center justify-between mb-4">

                <div>

                  <h2 className="text-lg font-semibold text-slate-900">
                    Recent Searches
                  </h2>

                  <p className="text-sm text-slate-500">
                    Latest object investigation activity
                  </p>

                </div>

                <button
                  type="button"
                  onClick={() =>
                    router.push(
                      "/history"
                    )
                  }
                  className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                >
                  View all
                </button>

              </div>

              <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">

                {loading ? (
                  <LoadingSearches />
                ) : recentSearches.length === 0 ? (
                  <EmptySearches
                    onNewSearch={() =>
                      router.push(
                        "/searches/new"
                      )
                    }
                  />
                ) : (
                  recentSearches.map(
                    (search) => (
                      <RecentSearch
                        key={
                          search.search_id
                        }
                        search={search}
                        onView={() =>
                          router.push(
                            `/searches/results/${search.search_id}`
                          )
                        }
                      />
                    )
                  )
                )}

              </div>

            </div>

            {/* ================================================== */}
            {/* TOP MATCH SUMMARY */}
            {/* ================================================== */}

            {!loading &&
              recentSearches.length > 0 && (
                <TopMatchSummary
                  search={
                    recentSearches[0]
                  }
                  onView={() =>
                    router.push(
                      `/searches/results/${recentSearches[0].search_id}`
                    )
                  }
                />
              )}

            {/* ================================================== */}
            {/* SECURITY NOTICE */}
            {/* ================================================== */}

            <div className="mt-6 flex gap-3 items-start bg-white border border-slate-200 rounded-2xl p-5">

              <ShieldCheck
                className="text-indigo-600 mt-0.5"
                size={22}
              />

              <div>

                <p className="font-medium text-slate-900">
                  Secure investigation environment
                </p>

                <p className="text-sm text-slate-500 mt-1">
                  Access to video footage, searches and
                  evidence is restricted to authorized users
                  and will be audited.
                </p>

              </div>

            </div>

          </div>

        </section>

      </div>
    </main>
  );
}


// ============================================================
// DASHBOARD STAT
// ============================================================

function DashboardStat({
  title,
  value,
  icon: Icon,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
}) {
  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200">

      <div className="flex items-center justify-between">

        <div>

          <p className="text-sm text-slate-500">
            {title}
          </p>

          <p className="text-3xl font-bold text-slate-900 mt-2">
            {value}
          </p>

        </div>

        <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
          <Icon size={22} />
        </div>

      </div>

    </div>
  );
}


// ============================================================
// RECENT SEARCH
// ============================================================

function RecentSearch({
  search,
  onView,
}: {
  search: SearchHistoryItem;
  onView: () => void;
}) {
  const topMatch =
    search.top_match;

  return (
    <div className="p-5 border-b last:border-b-0 border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">

      <div className="min-w-0">

        <p className="font-semibold text-slate-900">
          {topMatch
            ? topMatch.class_name
            : "Object Search"}
        </p>

        <p className="text-sm text-slate-500 mt-1 break-all">
          {search.search_id}
        </p>

        <p className="text-xs text-slate-400 mt-1">
          {formatDate(
            search.created_at
          )}
        </p>

      </div>

      <div className="flex flex-wrap items-center gap-5">

        <div>

          <p className="text-xs text-slate-400">
            Candidates
          </p>

          <p className="font-semibold text-slate-900">
            {search.search.candidates}
          </p>

        </div>

        <div>

          <p className="text-xs text-slate-400">
            Similarity
          </p>

          <p className="font-semibold text-slate-900">
            {topMatch
              ? formatScore(
                  topMatch.similarity_score
                )
              : "N/A"}
          </p>

        </div>

        <span className="px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
          {search.status}
        </span>

        <button
          type="button"
          onClick={onView}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          View
        </button>

      </div>

    </div>
  );
}


// ============================================================
// TOP MATCH SUMMARY
// ============================================================

function TopMatchSummary({
  search,
  onView,
}: {
  search: SearchHistoryItem;
  onView: () => void;
}) {
  const topMatch =
    search.top_match;

  if (!topMatch) {
    return null;
  }

  return (
    <div className="mt-6 bg-white border border-slate-200 rounded-2xl p-6">

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">

        <div>

          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Latest Top Candidate
          </p>

          <div className="flex flex-wrap items-center gap-3 mt-2">

            <h2 className="text-xl font-bold text-slate-900">
              {topMatch.class_name}
            </h2>

            <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
              {topMatch.match_status}
            </span>

          </div>

          <p className="text-sm text-slate-500 mt-2">
            Track {topMatch.track_id}
            {" • "}
            detected at{" "}
            {formatTimestamp(
              topMatch.timestamp
            )}
          </p>

        </div>

        <div className="flex items-center gap-5">

          <div>

            <p className="text-xs text-slate-400">
              Similarity
            </p>

            <p className="text-2xl font-bold text-slate-900">
              {formatScore(
                topMatch.similarity_score
              )}
            </p>

          </div>

          <div>

            <p className="text-xs text-slate-400">
              Ranking
            </p>

            <p className="text-2xl font-bold text-slate-900">
              {formatScore(
                topMatch.ranking_score
              )}
            </p>

          </div>

          <button
            type="button"
            onClick={onView}
            className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            View Result
          </button>

        </div>

      </div>

    </div>
  );
}


// ============================================================
// LOADING SEARCHES
// ============================================================

function LoadingSearches() {
  return (
    <div className="p-8 text-center">

      <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-600" />

      <p className="text-sm text-slate-500">
        Loading recent searches...
      </p>

    </div>
  );
}


// ============================================================
// EMPTY SEARCHES
// ============================================================

function EmptySearches({
  onNewSearch,
}: {
  onNewSearch: () => void;
}) {
  return (
    <div className="p-10 text-center">

      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500">
        <Search size={22} />
      </div>

      <p className="font-semibold text-slate-900">
        No searches yet
      </p>

      <p className="mt-1 text-sm text-slate-500">
        Start an object search to see your activity here.
      </p>

      <button
        type="button"
        onClick={onNewSearch}
        className="mt-5 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
      >
        Start New Search
      </button>

    </div>
  );
}


// ============================================================
// NAVIGATION ITEM
// ============================================================

function NavItem({
  icon,
  label,
  active = false,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition ${
        active
          ? "bg-indigo-600 text-white"
          : "text-slate-400 hover:bg-slate-900 hover:text-white"
      }`}
    >
      {icon}
      {label}
    </button>
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