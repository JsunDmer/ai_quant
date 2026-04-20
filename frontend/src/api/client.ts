export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    method: 'GET',
    headers: {
      Accept: 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  const text = await res.text();
  const body = text ? (safeJsonParse(text) as unknown) : null;

  if (!res.ok) {
    throw new ApiError(`GET ${path} failed`, res.status, body);
  }

  return body as T;
}

export async function apiPost<T>(path: string, json: unknown, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    body: JSON.stringify(json),
  });

  const text = await res.text();
  const body = text ? (safeJsonParse(text) as unknown) : null;

  if (!res.ok) {
    throw new ApiError(`POST ${path} failed`, res.status, body);
  }

  return body as T;
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

