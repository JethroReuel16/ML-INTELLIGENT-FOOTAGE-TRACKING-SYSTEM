const API_BASE_URL = "http://127.0.0.1:8000";

// ============================================================
// SEARCH RESPONSE TYPES
// ============================================================

export interface SearchResponse {
  status: string;
  message: string;
  request_id?: string;
  result?: VisionTraceResult;
  error?: string;
}

// ============================================================
// MATCH TYPES
// ============================================================

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

// ============================================================
// COMPLETE SEARCH RESULT
// ============================================================

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

// ============================================================
// SEARCH HISTORY TYPES
// ============================================================

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

// ============================================================
// START SEARCH
// ============================================================

export async function startSearch(
  referenceImage: File,
  video: File,
  frameInterval = 5,
  minDetectionConfidence = 0.25,
  maxResults = 20
): Promise<SearchResponse> {
  const formData = new FormData();

  formData.append(
    "reference_image",
    referenceImage
  );

  formData.append(
    "video",
    video
  );

  formData.append(
    "frame_interval",
    String(frameInterval)
  );

  formData.append(
    "min_detection_confidence",
    String(minDetectionConfidence)
  );

  formData.append(
    "max_results",
    String(maxResults)
  );

  const response = await fetch(
    `${API_BASE_URL}/api/search`,
    {
      method: "POST",
      body: formData,
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        data?.error ||
        "VisionTrace search failed."
    );
  }

  return data;
}

// ============================================================
// GET COMPLETE SEARCH RESULT
// ============================================================

export async function getSearchResult(
  searchId: string
): Promise<VisionTraceResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/search/${searchId}`,
    {
      method: "GET",
      cache: "no-store",
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        data?.error ||
        "Unable to retrieve search result."
    );
  }

  return data;
}

// ============================================================
// GET SEARCH HISTORY
// ============================================================

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

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        data?.error ||
        "Unable to retrieve search history."
    );
  }

  if (!Array.isArray(data)) {
    throw new Error(
      "Invalid search history response from VisionTrace backend."
    );
  }

  return data;
}

// ============================================================
// GET EVIDENCE IMAGE URL
// ============================================================

export function getEvidenceUrl(
  searchId: string,
  evidencePath: string
): string {
  if (!evidencePath) {
    return "";
  }

  const filename = evidencePath
    .split(/[\\/]/)
    .pop();

  if (!filename) {
    return "";
  }

  return `${API_BASE_URL}/api/search/${searchId}/evidence/${encodeURIComponent(
    filename
  )}`;
}

// ============================================================
// API BASE URL
// ============================================================

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}