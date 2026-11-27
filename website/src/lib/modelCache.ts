/**
 * Keeps the demo's face-tracking model (~3.7 MB) in IndexedDB, so a returning visitor's demo
 * starts without downloading it again. Any storage failure (private mode, quota, blocked site
 * data) simply falls back to a normal download: the cache can never break the demo.
 */
const DB = "ishara-cache";
const STORE = "models";

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function get(key: string): Promise<ArrayBuffer | undefined> {
  const db = await open();
  try {
    return await new Promise((resolve, reject) => {
      const r = db.transaction(STORE, "readonly").objectStore(STORE).get(key);
      r.onsuccess = () => resolve(r.result as ArrayBuffer | undefined);
      r.onerror = () => reject(r.error);
    });
  } finally { db.close(); }
}

async function put(key: string, value: ArrayBuffer): Promise<void> {
  const db = await open();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(value, key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally { db.close(); }
}

/** The model file as bytes: from IndexedDB when cached, otherwise downloaded (and cached). */
export async function cachedModel(url: string): Promise<Uint8Array> {
  try {
    const hit = await get(url);
    if (hit && hit.byteLength > 1000) return new Uint8Array(hit);
  } catch { /* storage unavailable: download instead */ }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`model download failed (${res.status})`);
  const buf = await res.arrayBuffer();
  try { await put(url, buf); } catch { /* not cached this time; still works */ }
  return new Uint8Array(buf);
}
