'use strict';

// Tiny in-memory TTL cache with in-flight de-duplication.
//
// Usage: cached(key, ttlMs, fn)
//   - Returns a cached result if one exists and hasn't expired.
//   - Coalesces concurrent calls for the same key into a single in-flight
//     promise so we never fire the same fetch twice in parallel.
//   - Caches the resolved value with an expiry timestamp.
//   - On error: does NOT cache, so the next caller retries immediately.

// cache entry shape: { value, expiresAt }
const _cache = new Map();
// in-flight shape: Promise
const _inflight = new Map();

/**
 * Fetch (or return cached) the result of fn().
 * @param {string}   key    Unique cache key
 * @param {number}   ttlMs  Time-to-live in milliseconds
 * @param {Function} fn     Async function that produces the value
 * @returns {Promise<any>}
 */
async function cached(key, ttlMs, fn) {
  // Return a still-fresh cached entry immediately.
  const entry = _cache.get(key);
  if (entry && Date.now() < entry.expiresAt) return entry.value;

  // Coalesce concurrent callers: if a fetch is already in-flight, share it.
  if (_inflight.has(key)) return _inflight.get(key);

  // Start a new fetch, register it as in-flight.
  const promise = Promise.resolve()
    .then(() => fn())
    .then((value) => {
      // Store on success; expire after ttlMs from now.
      _cache.set(key, { value, expiresAt: Date.now() + ttlMs });
      return value;
    })
    .finally(() => {
      // Always remove from in-flight so errors don't permanently block.
      _inflight.delete(key);
    });

  _inflight.set(key, promise);
  return promise;
}

/** Remove a single entry so the next call re-fetches. */
function invalidate(key) {
  _cache.delete(key);
  // Leave any in-flight promise alone — it will naturally expire.
}

/** Wipe the entire cache (useful in tests or after a provider switch). */
function clear() {
  _cache.clear();
  // In-flight promises can't be cancelled but will settle harmlessly.
}

module.exports = { cached, invalidate, clear };
