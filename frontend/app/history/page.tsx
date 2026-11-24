"use client";

import { ChevronRight, FolderSearch, Layers, Plus, RefreshCw, Search, SearchX } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { HistoryRow, SearchModeBadge } from "@/components/search";
import {
  Badge,
  Button,
  ButtonLink,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  LoadingState,
  Page,
  PageHeader,
  cn,
} from "@/components/ui";
import { useResource } from "@/lib/useResource";
import { formatRelative } from "@/lib/format";
import {
  getMultiSourceHistory,
  getSearchHistory,
  MultiSourceSummary,
  SearchHistoryItem,
  SearchInputMode,
} from "@/services/api";

type ModeFilter = "all" | SearchInputMode;
type Sort = "newest" | "oldest" | "candidates";

const MODE_FILTERS: { value: ModeFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "image", label: "Image" },
  { value: "text", label: "Text" },
  { value: "image_text", label: "Image + text" },
];

export default function HistoryPage() {
  const history = useResource(getSearchHistory);
  const multi = useResource(getMultiSourceHistory);
  const items = useMemo(() => history.data ?? [], [history.data]);
  const multiItems = multi.data ?? [];
  const loading = history.loading && !history.data;
  const refreshing = (history.loading && !!history.data) || (multi.loading && !!multi.data);
  const error = history.error;
  const reloadAll = () => {
    history.reload();
    multi.reload();
  };

  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<ModeFilter>("all");
  const [sort, setSort] = useState<Sort>("newest");

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();

    const filtered = items.filter((item) => {
      if (mode !== "all" && (item.search.search_mode ?? "image") !== mode) return false;
      if (!q) return true;
      return [item.search_id, item.search.text_prompt, item.top_match?.class_name, item.status, item.source?.name]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(q));
    });

    const time = (s: SearchHistoryItem) => new Date(s.created_at).getTime() || 0;

    return [...filtered].sort((a, b) =>
      sort === "oldest"
        ? time(a) - time(b)
        : sort === "candidates"
          ? (b.search.candidates || 0) - (a.search.candidates || 0)
          : time(b) - time(a)
    );
  }, [items, query, mode, sort]);

  const filtersActive = query.trim() !== "" || mode !== "all";

  return (
    <Page>
      <PageHeader
        title="Case history"
        description="Every search you have run, with its footage and the evidence found."
        actions={
          <>
            <Button
              variant="secondary"
              icon={RefreshCw}
              loading={refreshing}
              onClick={reloadAll}
            >
              Refresh
            </Button>
            <ButtonLink href="/searches/new" icon={Plus}>
              New search
            </ButtonLink>
          </>
        }
      />

      {loading ? (
        <Card>
          <LoadingState label="Loading search history…" />
        </Card>
      ) : error && items.length === 0 ? (
        <ErrorState
          title="Unable to load history"
          message={error}
          onRetry={reloadAll}
        />
      ) : items.length === 0 && multiItems.length === 0 ? (
        <Card>
          <EmptyState
            icon={FolderSearch}
            title="No searches yet"
            description="Searches you run will be listed here so you can return to their results and evidence."
            action={
              <ButtonLink href="/searches/new" icon={Plus}>
                Start a search
              </ButtonLink>
            }
          />
        </Card>
      ) : (
        <>
        {multiItems.length > 0 && <MultiSourceList items={multiItems} />}
        <Card>
          {/* Toolbar */}
          <div className="flex flex-col gap-3 border-b border-line p-4 lg:flex-row lg:items-center">
            <div className="relative flex-1">
              <Search
                size={16}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
                aria-hidden
              />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter by description, object class or search ID"
                aria-label="Filter searches"
                className="vt-input pl-9"
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div
                role="radiogroup"
                aria-label="Search type"
                className="flex rounded-lg border border-line-strong bg-surface-2 p-0.5"
              >
                {MODE_FILTERS.map((f) => (
                  <button
                    key={f.value}
                    type="button"
                    role="radio"
                    aria-checked={mode === f.value}
                    onClick={() => setMode(f.value)}
                    className={cn(
                      "rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
                      mode === f.value ? "bg-surface-3 text-fg shadow-sm" : "text-muted hover:text-fg"
                    )}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as Sort)}
                aria-label="Sort searches"
                className="vt-input w-auto py-2"
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="candidates">Most candidates</option>
              </select>
            </div>
          </div>

          {error && (
            <p className="border-b border-line bg-danger/10 px-5 py-2.5 text-sm text-danger">
              Refresh failed: {error}
            </p>
          )}

          {visible.length === 0 ? (
            <EmptyState
              icon={SearchX}
              title={items.length === 0 ? "No single-source searches yet" : "No searches match your filters"}
              action={
                filtersActive && (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setQuery("");
                      setMode("all");
                    }}
                  >
                    Clear filters
                  </Button>
                )
              }
            />
          ) : (
            <div className="divide-y divide-line">
              {visible.map((item) => (
                <HistoryRow key={item.search_id} item={item} />
              ))}
            </div>
          )}

          <p className="border-t border-line px-5 py-3 text-xs text-muted">
            Showing {visible.length} of {items.length} search{items.length === 1 ? "" : "es"}
          </p>
        </Card>
        </>
      )}
    </Page>
  );
}

function MultiSourceList({ items }: { items: MultiSourceSummary[] }) {
  return (
    <Card className="mb-6">
      <CardHeader
        title="Multi-source searches"
        description="Combined rankings across several cameras or files."
      />
      <div className="divide-y divide-line">
        {items.map((m) => (
          <Link
            key={m.multi_search_id}
            href={`/searches/multi-results/${encodeURIComponent(m.multi_search_id)}`}
            className="group flex items-center gap-4 px-5 py-4 transition-colors hover:bg-surface-2"
          >
            <span className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-line-strong bg-surface-2 text-muted sm:flex">
              <Layers size={18} aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="truncate text-sm font-semibold text-fg">
                  {m.text_prompt ? `“${m.text_prompt}”` : "Reference image search"}
                </p>
                <SearchModeBadge mode={m.search_mode} />
                {m.status !== "completed" && (
                  <Badge tone={m.status === "failed" ? "danger" : "warn"}>
                    {m.status === "failed" ? "Failed" : `${m.failed_sources} source(s) failed`}
                  </Badge>
                )}
              </div>
              <p className="mt-1 truncate text-xs text-muted">
                {formatRelative(m.created_at)} · {m.source_count} source{m.source_count === 1 ? "" : "s"}
                {m.source_names.length > 0 ? ` (${m.source_names.join(", ")})` : ""} · {m.match_count} match
                {m.match_count === 1 ? "" : "es"}
              </p>
            </div>
            <ChevronRight
              size={18}
              className="shrink-0 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-fg-2"
              aria-hidden
            />
          </Link>
        ))}
      </div>
    </Card>
  );
}
