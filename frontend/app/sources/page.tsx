
"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

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
} from "../../services/api";

const SOURCE_TYPES: {
  value: VideoSourceType;
  label: string;
  description: string;
}[] = [
  {
    value: "rtsp",
    label: "RTSP / CCTV / NVR",
    description: "Camera or recorder stream using rtsp:// or rtsps://",
  },
  {
    value: "http",
    label: "HTTP / HTTPS video",
    description: "Direct network video URL",
  },
  {
    value: "network",
    label: "Network file path",
    description: "Shared path, for example \\\\server\\share\\camera.mp4",
  },
  {
    value: "local",
    label: "Local file path",
    description: "A video file accessible from the backend computer",
  },
];

const EMPTY_FORM: VideoSourceInput = {
  name: "",
  source_type: "rtsp",
  url: "",
  location: "",
  description: "",
};

export default function SourcesPage() {
  const [sources, setSources] = useState<VideoSource[]>([]);
  const [form, setForm] = useState<VideoSourceInput>({
    ...EMPTY_FORM,
  });

  const [editingSource, setEditingSource] =
    useState<VideoSource | null>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [testingSourceId, setTestingSourceId] =
    useState<string | null>(null);

  const [testResults, setTestResults] = useState<
    Record<string, VideoSourceTestResult>
  >({});

  const loadSources = useCallback(async () => {
    try {
      setPageError("");

      const data = await getVideoSources();
      setSources(data);
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : "Unable to load video sources."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSources();
  }, [loadSources]);

  const updateFormField = <
    K extends keyof VideoSourceInput
  >(
    field: K,
    value: VideoSourceInput[K]
  ) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const resetForm = () => {
    setForm({ ...EMPTY_FORM });
    setEditingSource(null);
    setPageError("");
  };

  const beginEditing = (source: VideoSource) => {
    setEditingSource(source);

    setForm({
      name: source.name,
      source_type: source.source_type,
      // Do not populate a masked URL into the actual connection field.
      // A blank URL means the existing connection address is retained.
      url: "",
      location: source.location || "",
      description: source.description || "",
    });

    setPageError("");
    setSuccessMessage("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  const handleSave = async (
    event: FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();

    setPageError("");
    setSuccessMessage("");

    if (!form.name.trim()) {
      setPageError("Enter a name for this source.");
      return;
    }

    if (!editingSource && !form.url.trim()) {
      setPageError("Enter the source URL or file path.");
      return;
    }

    try {
      setSaving(true);

      if (editingSource) {
        const changes: {
          name: string;
          source_type: VideoSourceType;
          location: string;
          description: string;
          url?: string;
        } = {
          name: form.name.trim(),
          source_type: form.source_type,
          location: form.location?.trim() || "",
          description: form.description?.trim() || "",
        };

        // Only replace the connection address if a new one was entered.
        if (form.url.trim()) {
          changes.url = form.url.trim();
        }

        await updateVideoSource(
          editingSource.id,
          changes
        );

        setSuccessMessage(
          "Video source updated successfully."
        );
      } else {
        await createVideoSource({
          ...form,
          name: form.name.trim(),
          url: form.url.trim(),
          location: form.location?.trim() || "",
          description: form.description?.trim() || "",
        });

        setSuccessMessage(
          "Video source registered successfully. Test the connection before using it."
        );
      }

      resetForm();
      await loadSources();
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : "Unable to save video source."
      );
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (source: VideoSource) => {
    setPageError("");
    setSuccessMessage("");
    setTestingSourceId(source.id);

    try {
      const result = await testVideoSource(source.id);

      setTestResults((current) => ({
        ...current,
        [source.id]: result,
      }));

      if (result.connected) {
        setSuccessMessage(
          `${source.name}: connection successful (${result.width} × ${result.height}).`
        );
      } else {
        setPageError(
          `${source.name}: ${result.message}`
        );
      }

      await loadSources();
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : "Connection test failed."
      );
    } finally {
      setTestingSourceId(null);
    }
  };

  const handleDelete = async (source: VideoSource) => {
    const confirmed = window.confirm(
      `Delete "${source.name}" from registered video sources?`
    );

    if (!confirmed) return;

    setPageError("");
    setSuccessMessage("");

    try {
      await deleteVideoSource(source.id);

      setSources((current) =>
        current.filter((item) => item.id !== source.id)
      );

      setTestResults((current) => {
        const updated = { ...current };
        delete updated[source.id];
        return updated;
      });

      if (editingSource?.id === source.id) {
        resetForm();
      }

      setSuccessMessage(
        `"${source.name}" has been removed.`
      );
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : "Unable to delete source."
      );
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-gray-500">
              VisionTrace AI
            </p>

            <h1 className="mt-2 text-3xl font-bold text-gray-900">
              Video Sources
            </h1>

            <p className="mt-2 max-w-2xl text-gray-600">
              Register CCTV cameras, NVR streams, HTTP video URLs,
              and accessible local or network video files.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="rounded-xl border bg-white px-4 py-3 text-sm font-medium text-gray-700">
              {sources.length} registered
            </span>

            <button
              onClick={() => void loadSources()}
              disabled={loading}
              className="rounded-xl border bg-white px-4 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-100 disabled:opacity-50"
            >
              Refresh
            </button>
          </div>
        </header>

        {pageError && (
          <div
            role="alert"
            className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
          >
            {pageError}
          </div>
        )}

        {successMessage && (
          <div
            role="status"
            className="mb-6 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800"
          >
            {successMessage}
          </div>
        )}

        <div className="grid items-start gap-6 lg:grid-cols-[minmax(320px,0.85fr)_minmax(0,1.5fr)]">
          <section className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="mb-6">
              <h2 className="text-xl font-bold text-gray-900">
                {editingSource
                  ? "Edit Video Source"
                  : "Register a Source"}
              </h2>

              <p className="mt-2 text-sm leading-6 text-gray-500">
                The source must be accessible from the computer
                running the VisionTrace backend.
              </p>
            </div>

            <form
              onSubmit={handleSave}
              className="space-y-5"
            >
              <div>
                <label
                  htmlFor="source-name"
                  className="mb-2 block text-sm font-semibold text-gray-700"
                >
                  Source name
                </label>

                <input
                  id="source-name"
                  value={form.name}
                  onChange={(event) =>
                    updateFormField(
                      "name",
                      event.target.value
                    )
                  }
                  placeholder="e.g. Main Entrance Camera"
                  maxLength={100}
                  required
                  className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm outline-none focus:border-black"
                />
              </div>

              <div>
                <label
                  htmlFor="source-type"
                  className="mb-2 block text-sm font-semibold text-gray-700"
                >
                  Source type
                </label>

                <select
                  id="source-type"
                  value={form.source_type}
                  onChange={(event) =>
                    updateFormField(
                      "source_type",
                      event.target.value as VideoSourceType
                    )
                  }
                  className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm outline-none focus:border-black"
                >
                  {SOURCE_TYPES.map((type) => (
                    <option
                      key={type.value}
                      value={type.value}
                    >
                      {type.label}
                    </option>
                  ))}
                </select>

                <p className="mt-2 text-xs leading-5 text-gray-500">
                  {
                    SOURCE_TYPES.find(
                      (type) =>
                        type.value === form.source_type
                    )?.description
                  }
                </p>
              </div>

              <div>
                <label
                  htmlFor="source-url"
                  className="mb-2 block text-sm font-semibold text-gray-700"
                >
                  {editingSource
                    ? "Replace URL or path (optional)"
                    : "Source URL or path"}
                </label>

                <input
                  id="source-url"
                  type="text"
                  value={form.url}
                  onChange={(event) =>
                    updateFormField(
                      "url",
                      event.target.value
                    )
                  }
                  placeholder={
                    editingSource
                      ? "Leave blank to retain the current address"
                      : form.source_type === "rtsp"
                        ? "rtsp://camera-address:554/stream"
                        : form.source_type === "http"
                          ? "https://server/video.mp4"
                          : form.source_type === "network"
                            ? "\\\\server\\share\\camera.mp4"
                            : "D:\\Videos\\camera.mp4"
                  }
                  required={!editingSource}
                  maxLength={2048}
                  autoComplete="off"
                  className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm outline-none focus:border-black"
                />

                {editingSource && editingSource.has_credentials && (
                  <p className="mt-2 text-xs leading-5 text-amber-700">
                    The saved address contains credentials. Leave this field
                    blank to keep the current connection details.
                  </p>
                )}

                <p className="mt-2 text-xs leading-5 text-gray-500">
                  Use the full address or path available to the backend
                  machine, not just the address accessible from your browser.
                </p>
              </div>

              <div>
                <label
                  htmlFor="source-location"
                  className="mb-2 block text-sm font-semibold text-gray-700"
                >
                  Location / camera label
                </label>

                <input
                  id="source-location"
                  value={form.location || ""}
                  onChange={(event) =>
                    updateFormField(
                      "location",
                      event.target.value
                    )
                  }
                  placeholder="e.g. Lusaka office, north entrance"
                  maxLength={200}
                  className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm outline-none focus:border-black"
                />
              </div>

              <div>
                <label
                  htmlFor="source-description"
                  className="mb-2 block text-sm font-semibold text-gray-700"
                >
                  Description
                </label>

                <textarea
                  id="source-description"
                  value={form.description || ""}
                  onChange={(event) =>
                    updateFormField(
                      "description",
                      event.target.value
                    )
                  }
                  placeholder="Optional notes about this source"
                  maxLength={500}
                  rows={3}
                  className="w-full resize-y rounded-xl border border-gray-300 px-4 py-3 text-sm outline-none focus:border-black"
                />
              </div>

              <div className="flex flex-wrap gap-3 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 rounded-xl bg-black px-5 py-3 text-sm font-semibold text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {saving
                    ? "Saving..."
                    : editingSource
                      ? "Save Changes"
                      : "Register Source"}
                </button>

                {editingSource && (
                  <button
                    type="button"
                    onClick={resetForm}
                    disabled={saving}
                    className="rounded-xl border px-5 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </section>

          <section className="space-y-4">
            <div className="flex items-end justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Registered Sources
                </h2>

                <p className="mt-1 text-sm text-gray-500">
                  Test a source before selecting it for a search.
                </p>
              </div>
            </div>

            {loading ? (
              <div className="rounded-2xl border bg-white p-10 text-center shadow-sm">
                <div className="mx-auto mb-4 h-9 w-9 animate-spin rounded-full border-4 border-gray-200 border-t-black" />

                <p className="text-sm text-gray-500">
                  Loading video sources...
                </p>
              </div>
            ) : sources.length === 0 ? (
              <div className="rounded-2xl border border-dashed bg-white p-10 text-center">
                <div className="mb-3 text-4xl">▣</div>

                <h3 className="font-semibold text-gray-900">
                  No video sources registered
                </h3>

                <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-gray-500">
                  Register a CCTV stream, network path, or video URL
                  using the form to get started.
                </p>
              </div>
            ) : (
              sources.map((source) => {
                const testResult = testResults[source.id];
                const isTesting =
                  testingSourceId === source.id;

                const status = testResult
                  ? testResult.status
                  : source.last_connection_status;

                return (
                  <article
                    key={source.id}
                    className="rounded-2xl border bg-white p-5 shadow-sm"
                  >
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="wrap-break-word text-lg font-bold text-gray-900">
                            {source.name}
                          </h3>

                          <ConnectionBadge status={status} />
                        </div>

                        <p className="mt-2 text-sm font-medium text-gray-600">
                          {getSourceTypeLabel(source.source_type)}
                        </p>

                        <p className="mt-2 break-all font-mono text-xs leading-5 text-gray-500">
                          {source.display_url}
                        </p>

                        {source.location && (
                          <p className="mt-3 text-sm text-gray-600">
                            <span className="font-semibold">
                              Location:
                            </span>{" "}
                            {source.location}
                          </p>
                        )}

                        {source.description && (
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-500">
                            {source.description}
                          </p>
                        )}

                        {source.has_credentials && (
                          <p className="mt-2 text-xs text-amber-700">
                            This source uses saved connection credentials.
                          </p>
                        )}

                        {testResult && (
                          <div
                            className={`mt-4 rounded-xl p-3 text-sm ${
                              testResult.connected
                                ? "bg-green-50 text-green-800"
                                : "bg-red-50 text-red-700"
                            }`}
                          >
                            <p className="font-semibold">
                              {testResult.connected
                                ? "Connection successful"
                                : "Connection failed"}
                            </p>

                            <p className="mt-1 leading-5">
                              {testResult.message}
                            </p>

                            {testResult.connected && (
                              <p className="mt-1 text-xs">
                                Received frame: {testResult.width} ×{" "}
                                {testResult.height}
                              </p>
                            )}
                          </div>
                        )}

                        {source.last_tested_at && !testResult && (
                          <p className="mt-3 text-xs text-gray-400">
                            Last tested:{" "}
                            {formatDate(source.last_tested_at)}
                          </p>
                        )}
                      </div>

                      <div className="flex shrink-0 flex-wrap gap-2 sm:flex-col">
                        <button
                          onClick={() => void handleTest(source)}
                          disabled={isTesting}
                          className="rounded-xl bg-black px-4 py-2.5 text-sm font-semibold text-white hover:bg-gray-800 disabled:opacity-50"
                        >
                          {isTesting
                            ? "Testing..."
                            : "Test Connection"}
                        </button>

                        <button
                          onClick={() => beginEditing(source)}
                          className="rounded-xl border px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                        >
                          Edit
                        </button>

                        <button
                          onClick={() => void handleDelete(source)}
                          className="rounded-xl border border-red-200 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })
            )}
          </section>
        </div>

        <section className="mt-8 rounded-2xl border bg-white p-5 shadow-sm">
          <h2 className="font-bold text-gray-900">
            Connection notes
          </h2>

          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-gray-600">
            <li>
              The backend computer must have network access to the
              camera or recorder.
            </li>
            <li>
              RTSP credentials, stream paths, firewall rules, and
              camera permissions must be correct.
            </li>
            <li>
              A successful connection test confirms that a frame
              could be read; it does not guarantee that every stream
              can be played directly in a browser.
            </li>
            <li>
              Registered sources are saved on this backend machine.
              This page is intended for a trusted development
              environment; authentication and access control should
              be added before deployment.
            </li>
          </ul>
        </section>
      </div>
    </main>
  );
}

function getSourceTypeLabel(
  sourceType: VideoSourceType
): string {
  const item = SOURCE_TYPES.find(
    (type) => type.value === sourceType
  );

  return item?.label || sourceType.toUpperCase();
}

function ConnectionBadge({
  status,
}: {
  status: string;
}) {
  if (status === "connected") {
    return (
      <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-800">
        Connected
      </span>
    );
  }

  if (status === "failed") {
    return (
      <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-800">
        Connection failed
      </span>
    );
  }

  return (
    <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">
      Not tested
    </span>
  );
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}