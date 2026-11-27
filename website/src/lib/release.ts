import fallback from "@/data/release.json";

/** Shape of release/latest.json (single source of truth for website + desktop updater). */
export type Release = {
  product: string;
  version: string;
  status: "released" | "unreleased";
  releaseDate: string | null;
  installer: { file: string; url: string | null; sha256: string | null; sizeBytes: number | null; includesModels: boolean };
  requirements: { os: string; minWindowsBuild: number; bluetooth: string; microphone: boolean; diskSpaceMB: number };
  models: {
    version: string;
    bundled: boolean;
    items: { name: string; purpose: string }[];
    optional?: { name: string; purpose: string; offeredIn: string; url: string; sha256: string; sizeBytes: number }[];
  };
  firmware: { version: string; board: string };
  notes: string[];
};

const MANIFEST_URL =
  process.env.RELEASE_MANIFEST_URL ??
  "https://raw.githubusercontent.com/muradahmed23/ishara/main/release/latest.json";

/** Live manifest from GitHub (refreshed every 5 minutes), bundled copy if unreachable. */
export async function getRelease(): Promise<Release> {
  try {
    const r = await fetch(MANIFEST_URL, { next: { revalidate: 300 } });
    if (r.ok) return (await r.json()) as Release;
  } catch {
    /* offline build or GitHub unreachable: use the bundled copy */
  }
  return fallback as Release;
}

/** A download is only offered when it is real: released, with URL and checksum. */
export function isDownloadable(r: Release): boolean {
  return r.status === "released" && !!r.installer.url && !!r.installer.sha256;
}

export const formatSize = (b: number | null) => (b ? `${Math.round(b / 1048576)} MB` : "");
