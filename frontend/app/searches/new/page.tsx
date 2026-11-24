"use client";

import {
  Camera,
  Film,
  Image as ImageIcon,
  Layers,
  Search,
  SlidersHorizontal,
  Type,
  Upload,
  X,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ChangeEvent,
  DragEvent,
  FormEvent,
  ReactNode,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  Field,
  Page,
  PageHeader,
  Spinner,
  cn,
} from "@/components/ui";
import { formatClock } from "@/lib/format";
import {
  getVideoSources,
  startMultiSourceSearch,
  startSearch,
  startSourceSearch,
  VideoSource,
} from "@/services/api";

type Target = "upload" | "source" | "multi";
type InputMode = "image" | "text" | "image_text";

const QUICK_CATEGORIES = [
  "backpack",
  "handbag",
  "suitcase",
  "mobile phone",
  "laptop",
  "car",
  "motorcycle",
  "person",
  "shoe",
  "watch",
];

const TARGETS: { value: Target; title: string; text: string; icon: LucideIcon }[] = [
  { value: "upload", title: "Upload a video", text: "A file from this computer", icon: Upload },
  { value: "source", title: "One source", text: "A registered camera or file", icon: Camera },
  { value: "multi", title: "Several sources", text: "Rank matches across sources", icon: Layers },
];

const INPUT_MODES: { value: InputMode; title: string; text: string; icon: LucideIcon }[] = [
  { value: "image", title: "Reference image", text: "Find visually similar objects", icon: ImageIcon },
  { value: "text", title: "Description", text: "Detect objects by name", icon: Type },
  { value: "image_text", title: "Image + text", text: "Text picks, image ranks", icon: Layers },
];

const MAX_IMAGE_MB = 20;

export default function NewSearchPage() {
  const router = useRouter();

  const [target, setTarget] = useState<Target>("upload");
  const [inputMode, setInputMode] = useState<InputMode>("image");
  const [textPrompt, setTextPrompt] = useState("");
  const [referenceImage, setReferenceImage] = useState<File | null>(null);
  const [video, setVideo] = useState<File | null>(null);

  const [sources, setSources] = useState<VideoSource[]>([]);
  const [loadingSources, setLoadingSources] = useState(true);
  const [sourcesError, setSourcesError] = useState("");
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);

  const [frameInterval, setFrameInterval] = useState("5");
  const [confidence, setConfidence] = useState("0.25");
  const [maxResults, setMaxResults] = useState("20");
  const [recordingDuration, setRecordingDuration] = useState("30");
  const [highDetail, setHighDetail] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");

  /* ---------------- data ---------------- */

  useEffect(() => {
    let cancelled = false;

    getVideoSources()
      .then((data) => {
        if (cancelled) return;
        const active = data.filter((s) => s.is_active !== false);
        setSources(data);
        setSelectedSourceId(active[0]?.id ?? data[0]?.id ?? "");
        setSelectedSourceIds(active.map((s) => s.id));
      })
      .catch((err) => {
        if (!cancelled)
          setSourcesError(err instanceof Error ? err.message : "Unable to load sources.");
      })
      .finally(() => {
        if (!cancelled) setLoadingSources(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Elapsed timer + leave-page warning while a search is running.
  useEffect(() => {
    if (!submitting) return;

    const tick = setInterval(() => setElapsed((Date.now() - startedAt) / 1000), 1000);
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);

    return () => {
      clearInterval(tick);
      window.removeEventListener("beforeunload", warn);
    };
  }, [submitting, startedAt]);

  const imagePreview = useMemo(
    () => (referenceImage ? URL.createObjectURL(referenceImage) : ""),
    [referenceImage]
  );
  useEffect(() => () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview);
  }, [imagePreview]);

  /* ---------------- derived ---------------- */

  const needsImage = inputMode !== "text";
  const needsText = inputMode !== "image";
  const selectedSource = sources.find((s) => s.id === selectedSourceId);
  const selectedSources = sources.filter((s) => selectedSourceIds.includes(s.id));
  const usesRtsp =
    (target === "source" && selectedSource?.source_type === "rtsp") ||
    (target === "multi" && selectedSources.some((s) => s.source_type === "rtsp"));

  const ready =
    (!needsImage || !!referenceImage) &&
    (!needsText || textPrompt.trim().length > 0) &&
    (target === "upload"
      ? !!video
      : target === "source"
        ? !!selectedSourceId
        : selectedSourceIds.length > 0);

  /* ---------------- actions ---------------- */

  function pickImage(file: File | null) {
    setError("");
    if (file && !file.type.startsWith("image/")) {
      setError("The reference must be an image file (PNG, JPG or WebP).");
      return;
    }
    if (file && file.size > MAX_IMAGE_MB * 1024 * 1024) {
      setError(`The reference image must be smaller than ${MAX_IMAGE_MB} MB.`);
      return;
    }
    setReferenceImage(file);
  }

  function pickVideo(file: File | null) {
    setError("");
    if (file && !file.type.startsWith("video/") && !/\.(mp4|avi|mov|mkv|webm|m4v)$/i.test(file.name)) {
      setError("Please choose a video file (MP4, AVI, MOV, MKV or WebM).");
      return;
    }
    setVideo(file);
  }

  function toggleSource(id: string) {
    setError("");
    setSelectedSourceIds((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const prompt = textPrompt.trim();
    const interval = Number(frameInterval);
    const conf = Number(confidence);
    const limit = Number(maxResults);
    const duration = Number(recordingDuration);

    if (needsImage && !referenceImage) return setError("Add a reference image of the object.");
    if (needsText && !prompt)
      return setError('Describe the object to search for, for example "black backpack".');
    if (target === "upload" && !video) return setError("Choose a video file to search.");
    if (target === "source" && !selectedSourceId) return setError("Choose a registered source.");
    if (target === "multi" && selectedSourceIds.length === 0)
      return setError("Select at least one registered source.");
    if (!Number.isInteger(interval) || interval < 1)
      return setError("Frame interval must be a whole number of at least 1.");
    if (!Number.isFinite(conf) || conf < 0 || conf > 1)
      return setError("Minimum confidence must be between 0 and 1.");
    if (!Number.isInteger(limit) || limit < 1 || limit > 100)
      return setError("Maximum results must be between 1 and 100.");
    if (usesRtsp && (!Number.isInteger(duration) || duration < 5 || duration > 300))
      return setError("Recording duration must be between 5 and 300 seconds.");

    const image = needsImage ? referenceImage : null;
    const text = needsText ? prompt : undefined;

    setStartedAt(Date.now());
    setElapsed(0);
    setSubmitting(true);

    try {
      if (target === "upload") {
        const res = await startSearch(image, video!, interval, conf, limit, text, highDetail);
        const id = res.result?.search_id;
        if (!id) throw new Error(res.message || "The server did not return a search ID.");
        router.push(`/searches/results/${encodeURIComponent(id)}`);
      } else if (target === "source") {
        const res = await startSourceSearch(image, selectedSourceId, interval, conf, limit, duration, text, highDetail);
        const id = res.result?.search_id;
        if (!id) throw new Error(res.message || "The server did not return a search ID.");
        router.push(`/searches/results/${encodeURIComponent(id)}`);
      } else {
        const res = await startMultiSourceSearch(image, selectedSourceIds, interval, conf, limit, duration, text, highDetail);
        const id = res.multi_search_id || res.result?.multi_search_id;
        if (!id) throw new Error(res.message || "The server did not return a search ID.");
        router.push(`/searches/multi-results/${encodeURIComponent(id)}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "The search could not be completed.");
      setSubmitting(false);
    }
  }

  /* ---------------- render ---------------- */

  if (submitting) {
    return (
      <Page width="narrow">
        <ProcessingPanel
          elapsed={elapsed}
          target={target}
          sourceCount={target === "multi" ? selectedSourceIds.length : 1}
          usesRtsp={usesRtsp}
          recordingSeconds={Number(recordingDuration)}
        />
      </Page>
    );
  }

  const noSources = !loadingSources && sources.length === 0;

  return (
    <Page width="narrow">
      <PageHeader
        title="New search"
        description="Tell the system what to look for and which footage to search."
      />

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        {/* 1. What */}
        <Step n={1} title="What are you looking for?">
          <Segmented options={INPUT_MODES} value={inputMode} onChange={(v) => { setInputMode(v); setError(""); }} />

          {needsImage && (
            <div className="mt-5">
              <p className="mb-1.5 text-sm font-medium text-fg-2">Reference image</p>
              {referenceImage ? (
                <div className="flex items-center gap-4 rounded-lg border border-line-strong bg-surface-2 p-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imagePreview}
                    alt="Reference preview"
                    className="h-20 w-20 shrink-0 rounded-md bg-black object-contain"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-fg">{referenceImage.name}</p>
                    <p className="mt-0.5 text-xs text-muted">{(referenceImage.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                  <Button variant="ghost" size="sm" icon={X} onClick={() => pickImage(null)}>
                    Remove
                  </Button>
                </div>
              ) : (
                <FileDrop
                  accept="image/*"
                  icon={ImageIcon}
                  title="Drop an image here or click to browse"
                  hint={`A clear photo of the object · PNG, JPG or WebP up to ${MAX_IMAGE_MB} MB`}
                  onFile={pickImage}
                />
              )}
            </div>
          )}

          {needsText && (
            <div className="mt-5">
              <Field
                label="Object description"
                htmlFor="text-prompt"
                hint={
                  inputMode === "text"
                    ? "Separate several objects with commas. Without a reference image, results are ranked by detection confidence."
                    : "Separate several objects with commas. The image ranks the detected objects by visual similarity."
                }
              >
                <input
                  id="text-prompt"
                  value={textPrompt}
                  onChange={(e) => { setTextPrompt(e.target.value); setError(""); }}
                  maxLength={200}
                  placeholder="e.g. black backpack, silver laptop"
                  className="vt-input"
                />
              </Field>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {QUICK_CATEGORIES.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => { setTextPrompt(c); setError(""); }}
                    className={cn(
                      "rounded-full border px-3 py-1 text-xs transition-colors",
                      textPrompt.trim().toLowerCase() === c
                        ? "border-accent/50 bg-accent/10 text-accent"
                        : "border-line-strong text-muted hover:border-fg-2/40 hover:text-fg"
                    )}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>
          )}
        </Step>

        {/* 2. Where */}
        <Step n={2} title="Which footage should be searched?">
          <Segmented options={TARGETS} value={target} onChange={(v) => { setTarget(v); setError(""); }} />

          <div className="mt-5">
            {target === "upload" ? (
              video ? (
                <div className="flex items-center gap-4 rounded-lg border border-line-strong bg-surface-2 p-3">
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-surface-3 text-accent">
                    <Film size={22} aria-hidden />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-fg">{video.name}</p>
                    <p className="mt-0.5 text-xs text-muted">{(video.size / 1024 / 1024).toFixed(1)} MB</p>
                  </div>
                  <Button variant="ghost" size="sm" icon={X} onClick={() => pickVideo(null)}>
                    Remove
                  </Button>
                </div>
              ) : (
                <FileDrop
                  accept="video/*,.mp4,.avi,.mov,.mkv,.webm"
                  icon={Film}
                  title="Drop a video here or click to browse"
                  hint="MP4, AVI, MOV, MKV or WebM"
                  onFile={pickVideo}
                />
              )
            ) : loadingSources ? (
              <div className="flex items-center gap-3 py-4 text-sm text-muted">
                <Spinner size={16} /> Loading registered sources…
              </div>
            ) : sourcesError ? (
              <Alert tone="error" title="Sources could not be loaded">{sourcesError}</Alert>
            ) : noSources ? (
              <Alert
                tone="warn"
                title="No registered sources yet"
                action={
                  <Link href="/sources" className="text-sm font-semibold text-accent hover:underline">
                    Register a source →
                  </Link>
                }
              >
                Add a CCTV stream or video file on the Video sources page first.
              </Alert>
            ) : target === "source" ? (
              <Field label="Registered source" htmlFor="source">
                <select
                  id="source"
                  value={selectedSourceId}
                  onChange={(e) => setSelectedSourceId(e.target.value)}
                  className="vt-input"
                >
                  {sources.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} · {s.source_type.toUpperCase()}
                      {s.location ? ` · ${s.location}` : ""}
                      {s.is_active === false ? " (inactive)" : ""}
                    </option>
                  ))}
                </select>
              </Field>
            ) : (
              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="text-sm text-muted">
                    <span className="font-semibold text-fg">{selectedSourceIds.length}</span> of {sources.length} selected
                  </p>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedSourceIds(sources.filter((s) => s.is_active !== false).map((s) => s.id))}
                    >
                      Select all
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setSelectedSourceIds([])}>
                      Clear
                    </Button>
                  </div>
                </div>
                <ul className="max-h-72 divide-y divide-line overflow-y-auto rounded-lg border border-line-strong bg-surface-2">
                  {sources.map((s) => (
                    <li key={s.id}>
                      <label className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-surface-3">
                        <input
                          type="checkbox"
                          checked={selectedSourceIds.includes(s.id)}
                          onChange={() => toggleSource(s.id)}
                          className="h-4 w-4"
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium text-fg">{s.name}</span>
                          <span className="block truncate text-xs text-muted">
                            {s.source_type.toUpperCase()}
                            {s.location ? ` · ${s.location}` : ""}
                          </span>
                        </span>
                        {s.is_active === false && <Badge>Inactive</Badge>}
                      </label>
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-xs text-muted">Sources are searched one after another.</p>
              </div>
            )}

            {usesRtsp && (
              <div className="mt-4 max-w-xs">
                <Field
                  label="Live stream recording length"
                  htmlFor="recording"
                  hint="Seconds of live RTSP video to capture and search (5–300)."
                >
                  <input
                    id="recording"
                    type="number"
                    min={5}
                    max={300}
                    value={recordingDuration}
                    onChange={(e) => setRecordingDuration(e.target.value)}
                    className="vt-input"
                  />
                </Field>
              </div>
            )}
          </div>
        </Step>

        {/* 3. Advanced */}
        <Card>
          <details className="group">
            <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-4 text-sm font-medium text-fg-2 hover:text-fg [&::-webkit-details-marker]:hidden">
              <SlidersHorizontal size={16} className="text-muted" aria-hidden />
              Advanced settings
              <span className="ml-auto text-xs font-normal text-faint group-open:hidden">
                Every {frameInterval} frames · ≥ {confidence} confidence · up to {maxResults} results
                {highDetail ? " · small objects" : ""}
              </span>
            </summary>
            <div className="grid gap-4 border-t border-line px-5 py-5 sm:grid-cols-3">
              <Field label="Frame interval" htmlFor="interval" hint="Analyse every Nth frame. Lower is slower but more thorough.">
                <input id="interval" type="number" min={1} value={frameInterval} onChange={(e) => setFrameInterval(e.target.value)} className="vt-input" />
              </Field>
              <Field label="Minimum confidence" htmlFor="confidence" hint="Ignore detections below this score (0–1).">
                <input id="confidence" type="number" min={0} max={1} step={0.05} value={confidence} onChange={(e) => setConfidence(e.target.value)} className="vt-input" />
              </Field>
              <Field label="Max results per source" htmlFor="max" hint="Between 1 and 100.">
                <input id="max" type="number" min={1} max={100} value={maxResults} onChange={(e) => setMaxResults(e.target.value)} className="vt-input" />
              </Field>
              <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-line-strong bg-surface-2 p-3 sm:col-span-3">
                <input
                  type="checkbox"
                  checked={highDetail}
                  onChange={(e) => setHighDetail(e.target.checked)}
                  className="mt-0.5 h-4 w-4"
                />
                <span>
                  <span className="block text-sm font-medium text-fg">Detect small objects</span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-muted">
                    Analyses frames at a higher resolution so small items such as shoes, phones or
                    watches are found in wide CCTV shots. Searches take about three times longer.
                  </span>
                </span>
              </label>
            </div>
          </details>
        </Card>

        {error && <Alert tone="error">{error}</Alert>}

        <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted">
            Processing time depends on video length and the number of sources.
          </p>
          <Button type="submit" size="lg" icon={Search} disabled={!ready}>
            {target === "multi"
              ? `Search ${selectedSourceIds.length || ""} source${selectedSourceIds.length === 1 ? "" : "s"}`
              : "Start search"}
          </Button>
        </div>
      </form>
    </Page>
  );
}

/* ------------------------------------------------------------------ */

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <Card className="p-5 sm:p-6">
      <h2 className="mb-4 flex items-center gap-3 text-[15px] font-semibold text-fg">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/15 text-xs font-semibold text-accent">
          {n}
        </span>
        {title}
      </h2>
      {children}
    </Card>
  );
}

function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; title: string; text: string; icon: LucideIcon }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div role="radiogroup" className="grid gap-2 sm:grid-cols-3">
      {options.map(({ value: v, title, text, icon: Icon }) => {
        const active = v === value;
        return (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(v)}
            className={cn(
              "flex items-start gap-3 rounded-lg border p-3 text-left transition-colors",
              active
                ? "border-accent/60 bg-accent/8 ring-1 ring-accent/30"
                : "border-line-strong bg-surface-2 hover:border-fg-2/30"
            )}
          >
            <Icon size={18} className={cn("mt-0.5 shrink-0", active ? "text-accent" : "text-muted")} aria-hidden />
            <span>
              <span className="block text-sm font-semibold text-fg">{title}</span>
              <span className="mt-0.5 block text-xs text-muted">{text}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function FileDrop({
  accept,
  icon: Icon,
  title,
  hint,
  onFile,
}: {
  accept: string;
  icon: LucideIcon;
  title: string;
  hint: string;
  onFile: (file: File | null) => void;
}) {
  const [over, setOver] = useState(false);

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setOver(false);
    onFile(e.dataTransfer.files?.[0] ?? null);
  };

  return (
    <label
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      className={cn(
        "flex min-h-36 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors",
        over ? "border-accent bg-accent/5" : "border-line-strong bg-surface-2 hover:border-fg-2/40"
      )}
    >
      <Icon size={24} className="text-muted" aria-hidden />
      <span className="mt-3 text-sm font-medium text-fg">{title}</span>
      <span className="mt-1 text-xs text-muted">{hint}</span>
      <input
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(e: ChangeEvent<HTMLInputElement>) => {
          onFile(e.target.files?.[0] ?? null);
          e.target.value = "";
        }}
      />
    </label>
  );
}

function ProcessingPanel({
  elapsed,
  target,
  sourceCount,
  usesRtsp,
  recordingSeconds,
}: {
  elapsed: number;
  target: Target;
  sourceCount: number;
  usesRtsp: boolean;
  recordingSeconds: number;
}) {
  const steps = [
    usesRtsp
      ? `Recording ${recordingSeconds}s of live footage`
      : target === "upload"
        ? "Uploading footage"
        : "Opening registered footage",
    "Detecting and tracking objects",
    "Comparing candidates with your reference",
    "Saving ranked evidence",
  ];
  // Rough visual progress through the steps; the backend does not stream progress.
  const active = Math.min(steps.length - 1, Math.floor(elapsed / 12));

  return (
    <Card className="mx-auto mt-6 max-w-xl p-8 text-center" as="div">
      <div role="status" aria-live="polite">
        <Spinner size={36} className="mx-auto" />
        <h1 className="mt-5 text-xl font-semibold text-fg">Searching footage…</h1>
        <p className="mt-2 text-sm text-muted">
          {target === "multi"
            ? `Processing ${sourceCount} source${sourceCount === 1 ? "" : "s"} one at a time.`
            : "This can take a few minutes for long videos."}{" "}
          Keep this tab open.
        </p>
        <p className="mt-4 font-mono text-2xl tabular-nums text-fg">{formatClock(elapsed)}</p>
      </div>

      <ol className="mt-8 space-y-2 text-left">
        {steps.map((s, i) => (
          <li
            key={s}
            className={cn(
              "flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm",
              i < active && "border-line text-muted",
              i === active && "border-accent/40 bg-accent/8 text-fg",
              i > active && "border-line text-faint"
            )}
          >
            <span
              className={cn(
                "h-2 w-2 shrink-0 rounded-full",
                i < active ? "bg-ok" : i === active ? "animate-pulse bg-accent" : "bg-line-strong"
              )}
            />
            {s}
          </li>
        ))}
      </ol>
    </Card>
  );
}
