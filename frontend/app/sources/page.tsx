"use client";

import {
  Camera,
  Globe,
  HardDrive,
  KeyRound,
  MapPin,
  Pencil,
  Plug,
  Plus,
  RefreshCw,
  Server,
  Trash2,
  Video,
  type LucideIcon,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  LoadingState,
  Modal,
  Page,
  PageHeader,
  type Tone,
} from "@/components/ui";
import { formatRelative } from "@/lib/format";
import {
  createVideoSource,
  deleteVideoSource,
  getVideoSources,
  testVideoSource,
  updateVideoSource,
  VideoSource,
  VideoSourceInput,
  VideoSourceTestResult,
  VideoSourceType,
  VideoSourceUpdate,
} from "@/services/api";

const SOURCE_TYPES: {
  value: VideoSourceType;
  label: string;
  help: string;
  placeholder: string;
  icon: LucideIcon;
}[] = [
  {
    value: "rtsp",
    label: "RTSP stream (CCTV / NVR)",
    help: "A live camera or recorder stream using rtsp:// or rtsps://.",
    placeholder: "rtsp://user:password@192.168.1.20:554/stream1",
    icon: Camera,
  },
  {
    value: "http",
    label: "HTTP(S) video URL",
    help: "A direct link to a video file served over the network.",
    placeholder: "https://server.example/footage/entrance.mp4",
    icon: Globe,
  },
  {
    value: "network",
    label: "Network file share",
    help: "A video on a shared drive the server can reach.",
    placeholder: "\\\\fileserver\\cctv\\camera-01.mp4",
    icon: Server,
  },
  {
    value: "local",
    label: "File on the server",
    help: "A video stored on the machine running the backend.",
    placeholder: "D:\\Footage\\camera-01.mp4",
    icon: HardDrive,
  },
];

const typeInfo = (t: VideoSourceType) => SOURCE_TYPES.find((s) => s.value === t) ?? SOURCE_TYPES[0];

const EMPTY: VideoSourceInput = { name: "", source_type: "rtsp", url: "", location: "", description: "" };

function connectionBadge(status?: string): { tone: Tone; label: string } {
  if (status === "connected") return { tone: "ok", label: "Connected" };
  if (status === "failed") return { tone: "danger", label: "Connection failed" };
  return { tone: "neutral", label: "Not tested" };
}

export default function SourcesPage() {
  const [sources, setSources] = useState<VideoSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<VideoSource | null>(null);
  const [form, setForm] = useState<VideoSourceInput>(EMPTY);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [deleting, setDeleting] = useState<VideoSource | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const [testingId, setTestingId] = useState<string | null>(null);
  const [tests, setTests] = useState<Record<string, VideoSourceTestResult>>({});

  const load = useCallback(async () => {
    try {
      setSources(await getVideoSources());
      setLoadError("");
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Unable to load video sources.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  /* ---------------- form ---------------- */

  function openCreate() {
    setEditing(null);
    setForm(EMPTY);
    setFormError("");
    setFormOpen(true);
  }

  function openEdit(source: VideoSource) {
    setEditing(source);
    setForm({
      name: source.name,
      source_type: source.source_type,
      url: "", // blank keeps the stored address (it may contain credentials)
      location: source.location || "",
      description: source.description || "",
    });
    setFormError("");
    setFormOpen(true);
  }

  const closeForm = useCallback(() => {
    if (!saving) setFormOpen(false);
  }, [saving]);

  const set = <K extends keyof VideoSourceInput>(key: K, value: VideoSourceInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");

    if (!form.name.trim()) return setFormError("Give this source a name.");
    if (!editing && !form.url.trim()) return setFormError("Enter the stream URL or file path.");
    if (editing && form.source_type !== editing.source_type && !form.url.trim())
      return setFormError("Changing the source type needs a new URL or path that matches the new type.");

    setSaving(true);
    try {
      if (editing) {
        const changes: VideoSourceUpdate = {
          name: form.name.trim(),
          source_type: form.source_type,
          location: form.location?.trim() ?? "",
          description: form.description?.trim() ?? "",
        };
        if (form.url.trim()) changes.url = form.url.trim();
        await updateVideoSource(editing.id, changes);
        setNotice({ tone: "success", text: `“${form.name.trim()}” was updated.` });
      } else {
        await createVideoSource({
          name: form.name.trim(),
          source_type: form.source_type,
          url: form.url.trim(),
          location: form.location?.trim() ?? "",
          description: form.description?.trim() ?? "",
        });
        setNotice({
          tone: "success",
          text: `“${form.name.trim()}” was registered. Test its connection before searching it.`,
        });
      }
      setFormOpen(false);
      await load();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Unable to save this source.");
    } finally {
      setSaving(false);
    }
  }

  /* ---------------- actions ---------------- */

  async function handleTest(source: VideoSource) {
    setTestingId(source.id);
    setNotice(null);
    try {
      const res = await testVideoSource(source.id);
      setTests((t) => ({ ...t, [source.id]: res }));
      await load();
    } catch (err) {
      setTests((t) => ({
        ...t,
        [source.id]: {
          connected: false,
          status: "failed",
          message: err instanceof Error ? err.message : "Connection test failed.",
        },
      }));
    } finally {
      setTestingId(null);
    }
  }

  async function handleDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await deleteVideoSource(deleting.id);
      setSources((s) => s.filter((x) => x.id !== deleting.id));
      setTests((t) => {
        const next = { ...t };
        delete next[deleting.id];
        return next;
      });
      setNotice({ tone: "success", text: `“${deleting.name}” was removed.` });
      setDeleting(null);
    } catch (err) {
      setNotice({ tone: "error", text: err instanceof Error ? err.message : "Unable to delete this source." });
      setDeleting(null);
    } finally {
      setDeleteBusy(false);
    }
  }

  /* ---------------- render ---------------- */

  const current = typeInfo(form.source_type);

  return (
    <Page>
      <PageHeader
        title="Video sources"
        description="Cameras, recorders and video files the server can search. Sources must be reachable from the machine running the backend."
        actions={
          <>
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={() => {
                setLoading(true);
                void load();
              }}
              disabled={loading}
            >
              Refresh
            </Button>
            <Button icon={Plus} onClick={openCreate}>
              Add source
            </Button>
          </>
        }
      />

      {notice && (
        <Alert tone={notice.tone} className="mb-6" onDismiss={() => setNotice(null)}>
          {notice.text}
        </Alert>
      )}

      {loading && sources.length === 0 ? (
        <Card>
          <LoadingState label="Loading video sources…" />
        </Card>
      ) : loadError && sources.length === 0 ? (
        <ErrorState title="Unable to load sources" message={loadError} onRetry={() => { setLoading(true); void load(); }} />
      ) : sources.length === 0 ? (
        <Card>
          <EmptyState
            icon={Video}
            title="No video sources yet"
            description="Register a CCTV stream, network share or video file so you can search it from New search."
            action={
              <Button icon={Plus} onClick={openCreate}>
                Add your first source
              </Button>
            }
          />
        </Card>
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {sources.map((source) => {
            const info = typeInfo(source.source_type);
            const test = tests[source.id];
            const status = test?.status || source.last_connection_status;
            const badge = connectionBadge(status);
            const testing = testingId === source.id;

            return (
              <li key={source.id}>
                <Card as="article" className="flex h-full flex-col">
                  <div className="flex items-start gap-4 p-5">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
                      <info.icon size={19} aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="truncate text-[15px] font-semibold text-fg">{source.name}</h2>
                        <Badge tone={badge.tone}>{badge.label}</Badge>
                        {source.is_active === false && <Badge>Inactive</Badge>}
                      </div>
                      <p className="mt-0.5 text-xs text-muted">{info.label}</p>
                      <p className="mt-2 truncate font-mono text-xs text-faint" title={source.display_url}>
                        {source.display_url || "Address hidden"}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                        {source.location && (
                          <span className="inline-flex items-center gap-1">
                            <MapPin size={12} aria-hidden /> {source.location}
                          </span>
                        )}
                        {source.has_credentials && (
                          <span className="inline-flex items-center gap-1">
                            <KeyRound size={12} aria-hidden /> Credentials saved
                          </span>
                        )}
                        {source.last_tested_at && (
                          <span>Tested {formatRelative(source.last_tested_at)}</span>
                        )}
                      </div>
                      {source.description && (
                        <p className="mt-3 line-clamp-2 text-sm text-fg-2">{source.description}</p>
                      )}
                    </div>
                  </div>

                  {test && (
                    <div className="mx-5 mb-4">
                      {test.connected ?? test.status === "connected" ? (
                        <Alert tone="success" title="Connection successful">
                          {test.width && test.height
                            ? `Received a ${test.width} × ${test.height} frame.`
                            : "A video frame was read successfully."}
                        </Alert>
                      ) : (
                        <Alert tone="error" title="Connection failed">
                          {test.message || test.detail || "The server could not read a frame from this source."}
                        </Alert>
                      )}
                    </div>
                  )}

                  <div className="mt-auto flex flex-wrap gap-2 border-t border-line px-5 py-3">
                    <Button size="sm" variant="secondary" icon={Plug} loading={testing} onClick={() => void handleTest(source)}>
                      {testing ? "Testing…" : "Test connection"}
                    </Button>
                    <Button size="sm" variant="ghost" icon={Pencil} onClick={() => openEdit(source)}>
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      icon={Trash2}
                      className="ml-auto text-danger hover:bg-danger/10 hover:text-danger"
                      onClick={() => setDeleting(source)}
                    >
                      Delete
                    </Button>
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>
      )}

      {/* Add / edit */}
      <Modal
        open={formOpen}
        onClose={closeForm}
        title={editing ? "Edit video source" : "Add video source"}
        description="The address must be reachable from the server, not just from your browser."
      >
        <form id="source-form" onSubmit={handleSave} className="space-y-4" noValidate>
          {formError && <Alert tone="error">{formError}</Alert>}

          <Field label="Name" htmlFor="src-name">
            <input
              id="src-name"
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              maxLength={100}
              placeholder="Main entrance camera"
              className="vt-input"
              autoFocus
            />
          </Field>

          <Field label="Type" htmlFor="src-type" hint={current.help}>
            <select
              id="src-type"
              value={form.source_type}
              onChange={(e) => set("source_type", e.target.value as VideoSourceType)}
              className="vt-input"
            >
              {SOURCE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>

          <Field
            label={editing ? "New URL or path" : "URL or path"}
            optional={!!editing}
            htmlFor="src-url"
            hint={
              editing
                ? editing.has_credentials
                  ? "Leave blank to keep the current address and its saved credentials."
                  : "Leave blank to keep the current address."
                : undefined
            }
          >
            <input
              id="src-url"
              value={form.url}
              onChange={(e) => set("url", e.target.value)}
              maxLength={2048}
              autoComplete="off"
              spellCheck={false}
              placeholder={editing ? editing.display_url || current.placeholder : current.placeholder}
              className="vt-input font-mono text-[13px]"
            />
          </Field>

          <Field label="Location" optional htmlFor="src-location">
            <input
              id="src-location"
              value={form.location ?? ""}
              onChange={(e) => set("location", e.target.value)}
              maxLength={200}
              placeholder="Head office · north entrance"
              className="vt-input"
            />
          </Field>

          <Field label="Notes" optional htmlFor="src-desc">
            <textarea
              id="src-desc"
              value={form.description ?? ""}
              onChange={(e) => set("description", e.target.value)}
              maxLength={500}
              rows={3}
              className="vt-input resize-y"
            />
          </Field>
        </form>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="ghost" onClick={closeForm} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" form="source-form" loading={saving}>
            {editing ? "Save changes" : "Add source"}
          </Button>
        </div>
      </Modal>

      {/* Delete confirmation */}
      <Modal
        open={!!deleting}
        onClose={() => !deleteBusy && setDeleting(null)}
        title="Delete this source?"
        size="sm"
        description={
          <>
            <span className="font-semibold text-fg">{deleting?.name}</span> will be removed from your
            registered sources. Past search results are kept.
          </>
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleting(null)} disabled={deleteBusy}>
              Cancel
            </Button>
            <Button variant="danger" icon={Trash2} loading={deleteBusy} onClick={() => void handleDelete()}>
              Delete source
            </Button>
          </>
        }
      />
    </Page>
  );
}
