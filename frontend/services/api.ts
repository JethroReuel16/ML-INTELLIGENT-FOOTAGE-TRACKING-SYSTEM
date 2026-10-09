
const API_BASE_URL = "http://127.0.0.1:8000";

export interface SearchResponse {
  status: string;
  message: string;
  request_id?: string;
  result?: VisionTraceResult;
  error?: string;
}

export interface VisionTraceMatch {
  rank: number;
  track_id: number;
  class_id: number;
  class_name: string;
  match_status: string;
  similarity_score: number;
  ranking_score: number;
  top3_average: number;
  average_similarity: number;
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
    image: string;
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
    frame_interval: number;
    minimum_detection_confidence: number;
    frames_analyzed: number;
    candidate_observations: number;
    unique_tracks: number;
    candidates: number;
  };

  matches: VisionTraceMatch[];
}

export interface SearchHistoryTopMatch {
  rank: number;
  track_id: number;
  class_name: string;
  match_status: string;
  similarity_score: number;
  ranking_score: number;
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
  };

  top_match: SearchHistoryTopMatch | null;
}

export type VideoSourceType =
  | "rtsp"
  | "http"
  | "local"
  | "network";

export interface VideoSource {
  id: string;
  name: string;
  source_type: VideoSourceType;
  display_url: string;
  location: string;
  description: string;
  created_at: string;
  updated_at: string;
  last_tested_at: string | null;
  last_connection_status: string;
  has_credentials: boolean;
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
}

export interface VideoSourceTestResult {
  source_id: string;
  connected: boolean;
  status: "connected" | "failed";
  tested_at: string;
  width: number | null;
  height: number | null;
  message: string;
}

async function readApiResponse<T>(
  response: Response,
  fallbackMessage: string
): Promise<T> {
  let data: any = {};

  try {
    data = await response.json();
  } catch {
    // Keep the fallback message if the response is not JSON.
  }

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        data?.message ||
        data?.error ||
        fallbackMessage
    );
  }

  return data as T;
}

export async function startSearch(
  referenceImage: File,
  video: File,
  frameInterval = 5,
  minDetectionConfidence = 0.25,
  maxResults = 20
): Promise<SearchResponse> {
  const formData = new FormData();

  formData.append("reference_image", referenceImage);
  formData.append("video", video);
  formData.append("frame_interval", String(frameInterval));
  formData.append(
    "min_detection_confidence",
    String(minDetectionConfidence)
  );
  formData.append("max_results", String(maxResults));

  const response = await fetch(
    `${API_BASE_URL}/api/search`,
    {
      method: "POST",
      body: formData,
    }
  );

  return readApiResponse<SearchResponse>(
    response,
    "VisionTrace search failed."
  );
}

export async function getSearchResult(
  searchId: string
): Promise<VisionTraceResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/search/${encodeURIComponent(searchId)}`,
    {
      method: "GET",
      cache: "no-store",
    }
  );

  return readApiResponse<VisionTraceResult>(
    response,
    "Unable to retrieve search result."
  );
}

export async function getSearchHistory(): Promise<
  SearchHistoryItem[]
> {
  const response = await fetch(
    `${API_BASE_URL}/api/search`,
    {
      method: "GET",
      cache: "no-store",
    }
  );

  const data = await readApiResponse<unknown>(
    response,
    "Unable to retrieve search history."
  );

  if (!Array.isArray(data)) {
    throw new Error(
      "Invalid search history response from VisionTrace backend."
    );
  }

  return data as SearchHistoryItem[];
}

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

/* ---------------- VIDEO SOURCE MANAGEMENT ---------------- */

export async function getVideoSources(): Promise<VideoSource[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/sources`,
    {
      method: "GET",
      cache: "no-store",
    }
  );

  const data = await readApiResponse<unknown>(
    response,
    "Unable to retrieve video sources."
  );

  if (!Array.isArray(data)) {
    throw new Error(
      "Invalid video source response from VisionTrace backend."
    );
  }

  return data as VideoSource[];
}

export async function createVideoSource(
  source: VideoSourceInput
): Promise<VideoSource> {
  const response = await fetch(
    `${API_BASE_URL}/api/sources`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(source),
    }
  );

  return readApiResponse<VideoSource>(
    response,
    "Unable to create video source."
  );
}

export async function updateVideoSource(
  sourceId: string,
  changes: VideoSourceUpdate
): Promise<VideoSource> {
  const response = await fetch(
    `${API_BASE_URL}/api/sources/${encodeURIComponent(sourceId)}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(changes),
    }
  );

  return readApiResponse<VideoSource>(
    response,
    "Unable to update video source."
  );
}

export async function deleteVideoSource(
  sourceId: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/sources/${encodeURIComponent(sourceId)}`,
    {
      method: "DELETE",
    }
  );

  await readApiResponse<{
    success: boolean;
    message: string;
  }>(
    response,
    "Unable to delete video source."
  );
}

export async function testVideoSource(
  sourceId: string
): Promise<VideoSourceTestResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/sources/${encodeURIComponent(
      sourceId
    )}/test`,
    {
      method: "POST",
    }
  );

  return readApiResponse<VideoSourceTestResult>(
    response,
    "Unable to test video source."
  );
}