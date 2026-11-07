// fetch wrapper for the Khidmah Roster API.

export class ApiError extends Error {
  /** Error thrown for any non-2xx API response. */
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const PIN_KEY = "kr_pin";

/** The stored admin PIN, or null. */
export function storedPin() {
  return sessionStorage.getItem(PIN_KEY);
}

/** Remember a PIN that just passed /api/auth. */
export function storePin(pin) {
  sessionStorage.setItem(PIN_KEY, pin);
}

/** Forget the stored PIN (locked state). */
export function clearPin() {
  sessionStorage.removeItem(PIN_KEY);
}

const TODAY_RE = /[?&]today=(\d{4}-\d{2}-\d{2})(?:&|$)/;

/** The preview day from the URL (?today=YYYY-MM-DD), or null. */
function urlToday() {
  const match = location.search.match(TODAY_RE);
  return match ? match[1] : null;
}

/** Append the URL's today= preview to a GET path.
 *  The server ignores it unless ALLOW_TODAY_OVERRIDE is enabled. */
function withToday(path) {
  const today = urlToday();
  if (today === null) return path;
  return `${path}${path.includes("?") ? "&" : "?"}today=${today}`;
}

/** Perform a JSON request, adding X-Admin-Pin when a PIN is stored. */
async function request(method, path, body) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const pin = storedPin();
  if (pin) headers["X-Admin-Pin"] = pin;

  const res = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // non-JSON body; handled below via the status
  }

  if (!res.ok) {
    if (res.status === 401) {
      clearPin();
      window.dispatchEvent(new CustomEvent("kr:locked"));
    }
    throw new ApiError((data && data.error) || `Request failed (${res.status})`, res.status);
  }
  return data;
}

/** The app's API client. */
export const api = {
  /** GET path and parse JSON (adds the URL's today= preview). */
  get: (path) => request("GET", withToday(path)),
  /** Send method + optional JSON body, parse JSON. */
  send: (method, path, body) => request(method, path, body),
};
