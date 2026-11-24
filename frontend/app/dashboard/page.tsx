"use client";

import {
  ArrowRight,
  Boxes,
  FolderSearch,
  History,
  Plus,
  Search,
  Target,
  Video,
} from "lucide-react";
import Link from "next/link";
import { useCallback } from "react";

import { useAuth } from "@/components/AppChrome";
import { HistoryRow } from "@/components/search";
import {
  Alert,
  ButtonLink,
  Card,
  CardHeader,
  EmptyState,
  LoadingState,
  Page,
  PageHeader,
  Stat,
} from "@/components/ui";
import { formatNumber } from "@/lib/format";
import { useResource } from "@/lib/useResource";
import {
  getSearchHistory,
  getVideoSources,
  SearchHistoryItem,
  VideoSource,
} from "@/services/api";

export default function DashboardPage() {
  const { user } = useAuth();

  // Load both lists; one failing should not blank the other.
  const fetchDashboard = useCallback(async () => {
    const [history, srcs] = await Promise.allSettled([getSearchHistory(), getVideoSources()]);
    const failure = [history, srcs].find((r) => r.status === "rejected") as
      | PromiseRejectedResult
      | undefined;

    return {
      searches: history.status === "fulfilled" ? history.value : ([] as SearchHistoryItem[]),
      sources: srcs.status === "fulfilled" ? srcs.value : ([] as VideoSource[]),
      error: failure
        ? failure.reason instanceof Error
          ? failure.reason.message
          : "Some dashboard data could not be loaded."
        : "",
    };
  }, []);

  const { data, loading } = useResource(fetchDashboard);
  const searches = data?.searches ?? [];
  const sources = data?.sources ?? [];
  const error = data?.error ?? "";

  const totals = searches.reduce(
    (acc, s) => {
      acc.tracks += s.search.unique_tracks || 0;
      acc.candidates += s.search.candidates || 0;
      return acc;
    },
    { tracks: 0, candidates: 0 }
  );

  // Sources whose last connection test succeeded.
  const connectedSources = sources.filter((s) => s.last_connection_status === "connected").length;
  const firstName = user?.full_name?.split(/\s+/)[0];
  const dash = loading ? "…" : undefined;

  return (
    <Page>
      <PageHeader
        title={firstName ? `Welcome back, ${firstName}` : "Overview"}
        description="Search recorded footage for objects and review the evidence found."
        actions={
          <ButtonLink href="/searches/new" icon={Plus}>
            New search
          </ButtonLink>
        }
      />

      {error && (
        <Alert tone="error" className="mb-6" title="Some data could not be loaded">
          {error}
        </Alert>
      )}

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <Stat label="Searches run" value={dash ?? formatNumber(searches.length)} icon={FolderSearch} />
        <Stat
          label="Video sources"
          value={dash ?? formatNumber(sources.length)}
          icon={Video}
          hint={loading ? undefined : `${connectedSources} connected`}
        />
        <Stat label="Objects tracked" value={dash ?? formatNumber(totals.tracks)} icon={Boxes} />
        <Stat label="Candidates found" value={dash ?? formatNumber(totals.candidates)} icon={Target} />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card>
          <CardHeader
            title="Recent searches"
            description="Your latest investigations"
            action={
              searches.length > 0 && (
                <Link
                  href="/history"
                  className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
                >
                  View all <ArrowRight size={14} aria-hidden />
                </Link>
              )
            }
          />
          {loading ? (
            <LoadingState label="Loading recent searches…" />
          ) : searches.length === 0 ? (
            <EmptyState
              icon={Search}
              title="No searches yet"
              description="Run your first search with a reference image, a text description or both."
              action={
                <ButtonLink href="/searches/new" icon={Plus}>
                  Start a search
                </ButtonLink>
              }
            />
          ) : (
            <div className="divide-y divide-line">
              {searches.slice(0, 6).map((item) => (
                <HistoryRow key={item.search_id} item={item} />
              ))}
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <QuickAction
            href="/searches/new"
            icon={Search}
            title="Search footage"
            text="Upload a video or pick registered sources and find an object."
          />
          <QuickAction
            href="/sources"
            icon={Video}
            title="Manage video sources"
            text={
              sources.length === 0 && !loading
                ? "Register a CCTV stream or video file to search it later."
                : "Add, test or update cameras and video files."
            }
          />
          <QuickAction
            href="/history"
            icon={History}
            title="Case history"
            text="Revisit past searches, their footage and the evidence found."
          />
        </div>
      </div>
    </Page>
  );
}

function QuickAction({
  href,
  icon: Icon,
  title,
  text,
}: {
  href: string;
  icon: typeof Search;
  title: string;
  text: string;
}) {
  return (
    <Link
      href={href}
      className="group flex gap-4 rounded-xl border border-line bg-surface p-4 transition-colors hover:border-line-strong hover:bg-surface-2"
    >
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
        <Icon size={18} aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="flex items-center gap-1 text-sm font-semibold text-fg">
          {title}
          <ArrowRight
            size={14}
            className="text-faint transition-transform group-hover:translate-x-0.5"
            aria-hidden
          />
        </p>
        <p className="mt-0.5 text-sm leading-relaxed text-muted">{text}</p>
      </div>
    </Link>
  );
}
