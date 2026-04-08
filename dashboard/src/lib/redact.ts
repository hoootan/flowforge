/**
 * Redact sensitive values from objects before displaying in the UI.
 *
 * Walks the object tree and replaces values whose keys match known
 * sensitive patterns with a masked placeholder.
 */

const SENSITIVE_KEY_PATTERNS = [
  /token/i,
  /secret/i,
  /password/i,
  /api[_-]?key/i,
  /\bauth(?:orization|_token|_key|_secret)?\b/i,
  /\boauth/i,
  /credential/i,
  /private[_-]?key/i,
  /access[_-]?key/i,
  /session[_-]?id/i,
  /cookie/i,
  /\bjwt\b/i,
  /bearer/i,
  /refresh[_-]?token/i,
  /client[_-]?secret/i,
  /signing[_-]?key/i,
  /encryption[_-]?key/i,
  /\bssn\b/i,
  /credit[_-]?card/i,
];

const REDACTED = "••••••••";

function isSensitiveKey(key: string): boolean {
  return SENSITIVE_KEY_PATTERNS.some((pattern) => pattern.test(key));
}

function redactValue(value: string): string {
  if (value.length <= 8) return REDACTED;
  // Show first 4 and last 4 chars for identifiability
  return `${value.slice(0, 4)}${REDACTED}${value.slice(-4)}`;
}

function isPlainObject(obj: unknown): obj is Record<string, unknown> {
  if (typeof obj !== "object" || obj === null) return false;
  const proto = Object.getPrototypeOf(obj);
  return proto === Object.prototype || proto === null;
}

export function redactSensitiveFields(obj: unknown): unknown {
  if (obj === null || obj === undefined) return obj;

  if (Array.isArray(obj)) {
    return obj.map((item) => redactSensitiveFields(item));
  }

  if (!isPlainObject(obj)) return obj;

  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (isSensitiveKey(key) && typeof value === "string" && value.length > 0) {
      result[key] = redactValue(value);
    } else {
      result[key] = redactSensitiveFields(value);
    }
  }
  return result;
}
