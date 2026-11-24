const CONFIGURED_API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

/**
 * "localhost" and "127.0.0.1" are different sites to the browser, so the
 * session cookie would not be sent if the page and the API use different
 * names. When both are on this machine, follow the name the page was opened
 * with. Real deployments (non-loopback hosts) are left untouched.
 */
function resolveApiBaseUrl(): string {
  if (typeof window === "undefined") return CONFIGURED_API_URL;

  try {
    const api = new URL(CONFIGURED_API_URL);
    const pageHost = window.location.hostname;

    if (
      LOOPBACK_HOSTS.has(api.hostname) &&
      LOOPBACK_HOSTS.has(pageHost) &&
      api.hostname !== pageHost
    ) {
      api.hostname = pageHost;
      return api.toString().replace(/\/+$/, "");
    }
  } catch {
    /* invalid URL: use as configured */
  }

  return CONFIGURED_API_URL;
}

const API_BASE_URL = resolveApiBaseUrl();

export type VideoSourceType = "rtsp" | "http" | "local" | "network";

export interface VideoSource {
  id: string;
  name: string;
  source_type: VideoSourceType;
  location?: string;
  display_url?: string;
  url?: string;
  description?: string;
  is_active?: boolean;
  has_credentials?: boolean;
  last_connection_status?: "connected" | "failed" | "not_tested" | string;
  last_tested_at?: string | null;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export interface VideoSourceInput {
  name: string;
  source_type: VideoSourceType;
  url: string;
  location?: string;
  description?: string;
}

export interface VideoSourceUpdate {
  name?: string;
  source_type?: VideoSourceType;
  url?: string;
  location?: string;
  description?: string;
  is_active?: boolean;
}

export interface VideoSourceTestResult {
  connected?: boolean;
  width?: number | null;
  height?: number | null;
  tested_at?: string;
  success?: boolean;
  status?: string;
  message?: string;
  detail?: string;
  [key: string]: unknown;
}

export interface SearchResponse {
  status: string;
  message: string;
  request_id?: string;
  result?: VisionTraceResult;
  error?: string;
}

export type SearchInputMode = "image" | "text" | "image_text";

export interface DetectorStatus {
  requested: string;
  active: string;
  checkpoint?: string | null;
  device?: string;
  fallback: boolean;
  fallback_reason?: string | null;
}

export interface VisionTraceMatch {
  rank: number;
  track_id: number;
  class_id: number;
  class_name: string;
  match_status: string;
  /** null for text-only searches (no reference image to compare with). */
  similarity_score: number | null;
  ranking_score: number;
  top3_average: number;
  average_similarity: number | null;
  ranking_basis?: "dinov2_similarity" | "detection_confidence";
  search_prompt?: string | null;
  timestamp: number;
  frame_number: number;
  bbox: [number, number, number, number];
  detection_confidence: number;
  frames_observed: number;
  evidence_image: string;
}

export interface VisionTraceResult {
  status: string;
  search_id: string;
  created_at: string;
  reference: {
    image: string | null;
    text_prompt?: string | null;
  };
  video: {
    path: string;
    duration: number;
    fps: number;
    frame_count: number;
    width: number;
    height: number;
  };
  search: {
    search_mode?: SearchInputMode;
    text_prompt?: string | null;
    prompts?: string[] | null;
    ranking_basis?: "dinov2_similarity" | "detection_confidence";
    detector?: DetectorStatus;
    frame_interval: number;
    minimum_detection_confidence: number;
    /** Detector input size used (larger = "small objects" search). */
    detection_size?: number | null;
    processing_seconds?: number;
    frames_analyzed: number;
    candidate_observations: number;
    unique_tracks: number;
    candidates: number;
  };
  matches: VisionTraceMatch[];
  source?: {
    id?: string;
    name?: string;
    source_type?: VideoSourceType;
    location?: string;
    [key: string]: unknown;
  };
}

export interface SearchHistoryTopMatch {
  rank: number;
  track_id: number;
  class_name: string;
  match_status: string;
  similarity_score: number | null;
  ranking_score: number;
  ranking_basis?: "dinov2_similarity" | "detection_confidence";
  timestamp: number;
}

export interface SearchHistoryItem {
  search_id: string;
  status: string;
  created_at: string;
  video: {
    duration: number;
    fps: number;
    frame_count: number;
    width: number;
    height: number;
  };
  search: {
    frames_analyzed: number;
    candidate_observations: number;
    unique_tracks: number;
    candidates: number;
    search_mode?: SearchInputMode;
    text_prompt?: string | null;
  };
  top_match: SearchHistoryTopMatch | null;
  source?: SearchSourceInfo | null;
}

export interface SearchSourceInfo {
  id: string;
  name: string;
  source_type: VideoSourceType;
  location?: string | null;
}

export interface MultiSourceSummary {
  multi_search_id: string;
  status: "completed" | "partial" | "failed";
  created_at: string;
  source_count: number;
  successful_sources: number;
  failed_sources: number;
  match_count: number;
  search_mode?: SearchInputMode;
  text_prompt?: string | null;
  source_names: string[];
  top_match: {
    class_name?: string;
    source_name?: string;
    similarity_score?: number | null;
    ranking_score?: number;
    timestamp?: number;
  } | null;
}

export interface MultiSourceMatch extends VisionTraceMatch {
  /** Rank inside the source's own search (rank = global rank across sources). */
  source_rank?: number | null;
  source_id: string;
  source_name: string;
  source_type: VideoSourceType;
  search_id: string;
}

export interface MultiSourceStatus {
  source_id: string;
  source_name: string;
  source_type: string;
  status: "completed" | "failed";
  search_id: string | null;
  match_count: number;
  message: string;
}

export interface MultiSourceResult {
  multi_search_id: string;
  status: "completed" | "partial" | "failed";
  created_at: string;
  source_count: number;
  successful_sources: number;
  failed_sources: number;
  settings: {
    search_mode?: SearchInputMode;
    text_prompt?: string | null;
    frame_interval: number;
    min_detection_confidence: number;
    max_results_per_source: number;
    recording_duration_seconds: number;
  };
  sources: MultiSourceStatus[];
  matches: MultiSourceMatch[];
}

export interface AuthUser {
  id: number;
  full_name: string;
  email: string;
  is_active?: boolean;
}

export interface AuthResponse {
  message: string;
  user: AuthUser;
}

export interface RegisterInput {
  full_name: string;
  email: string;
  password: string;
}

/** Error carrying the HTTP status so callers can react (e.g. 401 → login). */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

/** fetch() wrapper that turns network failures into a readable message. */
async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch {
    throw new ApiError(
      "Cannot reach the ML Footage Tracking server. Check that the backend is running and try again.",
      0
    );
  }
}

/** Extracts a human-readable message from FastAPI error payloads. */
function errorMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;

  const body = data as Record<string, unknown>;
  const detail = body.detail ?? body.error ?? body.message;

  if (typeof detail === "string" && detail.trim()) return detail;

  // Pydantic validation errors: [{ loc, msg, ... }]
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    if (first?.msg) {
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : "";
      return field ? `${String(field)}: ${first.msg}` : first.msg;
    }
  }

  return fallback;
}

async function readResponse<T>(
  response: Response,
  fallback: string
): Promise<T> {
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message =
      response.status === 401
        ? "Your session has expired. Please sign in again."
        : errorMessage(data, fallback);

    throw new ApiError(message, response.status);
  }

  return data as T;
}

/**
 * Adds the reference image (image / image + text searches) and the text
 * prompt (text / image + text searches) to a search request.
 */
function appendSearchInputs(
  formData: FormData,
  referenceImage: File | null,
  textPrompt?: string,
  highDetail = false
) {
  const prompt = (textPrompt ?? "").trim();

  // Larger detector input: finds small objects (shoes, phones), ~3x slower.
  if (highDetail) {
    formData.append("high_detail", "true");
  }

  if (referenceImage) {
    formData.append("reference_image", referenceImage);
  }

  if (prompt) {
    formData.append("text_prompt", prompt);
  }
}

/**
 * UPLOADED VIDEO SEARCH
 */
export async function startSearch(
  referenceImage: File | null,
  video: File,
  frameInterval = 5,
  minDetectionConfidence = 0.25,
  maxResults = 20,
  textPrompt?: string,
  highDetail = false
): Promise<SearchResponse> {
  const formData = new FormData();

  appendSearchInputs(formData, referenceImage, textPrompt, highDetail);
  formData.append("video", video);
  formData.append("frame_interval", String(frameInterval));
  formData.append(
    "min_detection_confidence",
    String(minDetectionConfidence)
  );
  formData.append("max_results", String(maxResults));

  const response = await apiFetch(`${API_BASE_URL}/api/search`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });

  return readResponse<SearchResponse>(
    response,
    "Upload search failed."
  );
}

/**
 * REGISTERED SOURCE SEARCH
 */
export async function startSourceSearch(
  referenceImage: File | null,
  sourceId: string,
  frameInterval = 5,
  minDetectionConfidence = 0.25,
  maxResults = 20,
  recordingDurationSeconds = 30,
  textPrompt?: string,
  highDetail = false
): Promise<SearchResponse> {
  const formData = new FormData();

  formData.append("source_id", sourceId);
  appendSearchInputs(formData, referenceImage, textPrompt, highDetail);
  formData.append("frame_interval", String(frameInterval));
  formData.append(
    "min_detection_confidence",
    String(minDetectionConfidence)
  );
  formData.append("max_results", String(maxResults));
  formData.append(
    "recording_duration_seconds",
    String(recordingDurationSeconds)
  );

  const response = await apiFetch(`${API_BASE_URL}/api/search/source`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });

  return readResponse<SearchResponse>(
    response,
    "Registered-source search failed."
  );
}

/**
 * INDIVIDUAL SEARCH RESULT
 */
export async function getSearchResult(
  searchId: string
): Promise<VisionTraceResult> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/search/${encodeURIComponent(searchId)}`,
    {
      method: "GET",
      cache: "no-store",
      credentials: "include",
    }
  );

  return readResponse<VisionTraceResult>(
    response,
    "Unable to retrieve search result."
  );
}

/**
 * SEARCH HISTORY
 */
export async function getSearchHistory(): Promise<SearchHistoryItem[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/search`, {
    method: "GET",
    cache: "no-store",
    credentials: "include",
  });

  const data = await readResponse<SearchHistoryItem[]>(
    response,
    "Unable to retrieve search history."
  );

  if (!Array.isArray(data)) {
    throw new Error(
      "Invalid search history response from ML Footage Tracking backend."
    );
  }

  return data;
}

/**
 * VIDEO SOURCES
 */
export async function getVideoSources(): Promise<VideoSource[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/sources`, {
    method: "GET",
    cache: "no-store",
    credentials: "include",
  });

  const data = await readResponse<
    VideoSource[] | { sources: VideoSource[] }
  >(
    response,
    "Unable to retrieve registered video sources."
  );

  if (Array.isArray(data)) {
    return data;
  }

  if (data && Array.isArray(data.sources)) {
    return data.sources;
  }

  throw new Error(
    "Invalid video sources response from ML Footage Tracking backend."
  );
}

export async function createVideoSource(
  source: VideoSourceInput
): Promise<VideoSource> {
  const response = await apiFetch(`${API_BASE_URL}/api/sources`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(source),
    credentials: "include",
  });

  return readResponse<VideoSource>(
    response,
    "Unable to register video source."
  );
}

export async function updateVideoSource(
  sourceId: string,
  updates: VideoSourceUpdate
): Promise<VideoSource> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/sources/${encodeURIComponent(sourceId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
      credentials: "include",
    }
  );

  return readResponse<VideoSource>(
    response,
    "Unable to update video source."
  );
}

export async function deleteVideoSource(
  sourceId: string
): Promise<void> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/sources/${encodeURIComponent(sourceId)}`,
    {
      method: "DELETE",
      credentials: "include",
    }
  );

  if (!response.ok) {
    await readResponse(response, "Unable to delete video source.");
  }
}

export async function testVideoSource(
  sourceId: string
): Promise<VideoSourceTestResult> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/sources/${encodeURIComponent(sourceId)}/test`,
    {
      method: "POST",
      credentials: "include",
    }
  );

  return readResponse<VideoSourceTestResult>(
    response,
    "Unable to test video source."
  );
}

/**
 * EVIDENCE URL
 */
export function getEvidenceUrl(
  searchId: string,
  evidencePath: string
): string {
  if (!evidencePath) return "";

  const filename = evidencePath.split(/[\\/]/).pop();
  if (!filename) return "";

  return `${API_BASE_URL}/api/search/${encodeURIComponent(
    searchId
  )}/evidence/${encodeURIComponent(filename)}`;
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

/** Original footage for a completed search (streamed by the backend). */
export function getSearchVideoUrl(searchId: string): string {
  return `${API_BASE_URL}/api/search/${encodeURIComponent(searchId)}/video`;
}

/**
 * MULTI-SOURCE SEARCH
 */
export async function startMultiSourceSearch(
  referenceImage: File | null,
  sourceIds: string[],
  frameInterval = 5,
  minDetectionConfidence = 0.25,
  maxResults = 20,
  recordingDurationSeconds = 30,
  textPrompt?: string,
  highDetail = false
): Promise<{
  status: string;
  message: string;
  multi_search_id: string;
  result: MultiSourceResult;
}> {
  const formData = new FormData();

  formData.append("source_ids", JSON.stringify(sourceIds));
  appendSearchInputs(formData, referenceImage, textPrompt, highDetail);
  formData.append("frame_interval", String(frameInterval));
  formData.append(
    "min_detection_confidence",
    String(minDetectionConfidence)
  );
  formData.append("max_results", String(maxResults));
  formData.append(
    "recording_duration_seconds",
    String(recordingDurationSeconds)
  );

  const response = await apiFetch(
    `${API_BASE_URL}/api/search/multi-source`,
    {
      method: "POST",
      body: formData,
      credentials: "include",
    }
  );

  return readResponse(
    response,
    "Multi-source search failed."
  );
}

export async function getMultiSourceResult(
  multiSearchId: string
): Promise<MultiSourceResult> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/search/multi/${encodeURIComponent(multiSearchId)}`,
    {
      method: "GET",
      cache: "no-store",
      credentials: "include",
    }
  );

  return readResponse<MultiSourceResult>(
    response,
    "Unable to retrieve multi-source search results."
  );
}

/**
 * Lists multi-source searches so they can be reopened from Case history.
 */
export async function getMultiSourceHistory(): Promise<MultiSourceSummary[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/search/multi`, {
    method: "GET",
    cache: "no-store",
    credentials: "include",
  });

  return readResponse<MultiSourceSummary[]>(
    response,
    "Unable to retrieve multi-source searches."
  );
}

/**
 * Permanently deletes a search with its evidence images and stored footage.
 */
export async function deleteSearch(searchId: string): Promise<void> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/search/${encodeURIComponent(searchId)}`,
    { method: "DELETE", credentials: "include" }
  );

  await readResponse(response, "Unable to delete this search.");
}

/**
 * AUTHENTICATION
 */

export async function registerUser(
  data: RegisterInput
): Promise<AuthResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
    credentials: "include",
  });

  return readResponse<AuthResponse>(
    response,
    "Registration failed."
  );
}

export async function loginUser(
  email: string,
  password: string
): Promise<AuthResponse> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
    credentials: "include",
  });

  return readResponse<AuthResponse>(
    response,
    "Login failed."
  );
}

export async function getCurrentUser(): Promise<AuthUser> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/me`, {
    method: "GET",
    cache: "no-store",
    credentials: "include",
  });

  return readResponse<AuthUser>(
    response,
    "Unable to retrieve current user."
  );
}

export async function logoutUser(): Promise<{ message: string }> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  return readResponse<{ message: string }>(
    response,
    "Logout failed."
  );
}
