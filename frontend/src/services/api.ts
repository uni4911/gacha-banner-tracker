import type { Banner, ServerRegion } from '../types/banner';

const FALLBACK_DIRECT_URL = 'http://127.0.0.1:8000';

const SERVER_MAP: Record<ServerRegion, string | null> = {
  ALL: null,
  ASIA: 'ASIA',
  EUROPE: 'EUROPE',
  AMERICA: 'AMERICA',
};

async function tryFetch(url: string, timeoutMs = 4000): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    return res;
  } finally {
    clearTimeout(id);
  }
}

export async function fetchActiveBanners(
  gameName: string,
  serverRegion: ServerRegion = 'ALL'
): Promise<Banner[]> {
  const params = new URLSearchParams();
  const serverValue = SERVER_MAP[serverRegion];
  if (serverValue) {
    params.append('server', serverValue);
  }

  const queryString = params.toString() ? `?${params.toString()}` : '';
  const path = `/games/${encodeURIComponent(gameName)}/banners/active${queryString}`;

  let response: Response | null = null;
  let lastStatus = 0;

  // 1. Try relative path (Vite proxy)
  try {
    const res = await tryFetch(path);
    if (res.ok) {
      return (await res.json()) as Banner[];
    }
    lastStatus = res.status;
    response = res;
  } catch {
    // Relative fetch failed, try direct port 8000
  }

  // 2. Try direct FastAPI backend (http://127.0.0.1:8000)
  try {
    const directUrl = `${FALLBACK_DIRECT_URL}${path}`;
    const directRes = await tryFetch(directUrl);
    if (directRes.ok) {
      return (await directRes.json()) as Banner[];
    }
    lastStatus = directRes.status;
    response = directRes;
  } catch {
    // Both failed
  }

  if (response && !response.ok) {
    let errDetail = '';
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(
      `Server responded with status ${response.status}: ${response.statusText}${
        errDetail ? ` (${errDetail})` : ''
      }`
    );
  }

  if (lastStatus === 502 || lastStatus === 503) {
    throw new Error(
      `FastAPI backend is not running on port 8000 (502 Bad Gateway). Please run: uvicorn src.api.app:app --reload --port 8000`
    );
  }

  throw new Error(
    `Cannot connect to FastAPI backend. Please make sure the backend is running with: uvicorn src.api.app:app --reload --port 8000`
  );
}

export async function checkApiHealth(): Promise<boolean> {
  // Try proxy first
  try {
    const res = await tryFetch('/health', 2000);
    if (res.ok) {
      const data = await res.json();
      return data.status === 'ok';
    }
  } catch {
    // Ignore and fallback
  }

  // Try direct backend
  try {
    const res = await tryFetch(`${FALLBACK_DIRECT_URL}/health`, 2000);
    if (res.ok) {
      const data = await res.json();
      return data.status === 'ok';
    }
  } catch {
    // Offline
  }

  return false;
}

export async function fetchGames(): Promise<{ id?: number | null; name: string }[]> {
  const path = '/games';
  // 1. Try relative proxy
  try {
    const res = await tryFetch(path);
    if (res.ok) {
      return (await res.json()) as { id?: number | null; name: string }[];
    }
  } catch {
    // try fallback
  }

  // 2. Try direct FastAPI backend
  try {
    const directRes = await tryFetch(`${FALLBACK_DIRECT_URL}${path}`);
    if (directRes.ok) {
      return (await directRes.json()) as { id?: number | null; name: string }[];
    }
  } catch {
    // offline
  }

  return [];
}

