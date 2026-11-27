import { formatSize, isDownloadable, type Release } from "@/lib/release";

/** Download panel driven entirely by release/latest.json. Never shows a fake link. */
export function DownloadCard({ release: r }: { release: Release }) {
  const ready = isDownloadable(r);
  return (
    <div className="dl">
      <div className="dl-top">
        <span className="mark" aria-hidden />
        <div>
          <h3 style={{ fontSize: 26 }}>iShara for Windows</h3>
          <div className="row" style={{ gap: 8, marginTop: 6 }}>
            <span className="muted">Version {r.version}</span>
            {ready ? <span className="badge ok">Available</span> : <span className="badge soon">Coming soon</span>}
          </div>
        </div>
      </div>

      {ready ? (
        <a className="btn btn-primary" href={r.installer.url!} download>
          Download iShara {r.version} · {formatSize(r.installer.sizeBytes)}
        </a>
      ) : (
        <span className="btn btn-primary" aria-disabled="true" role="link">Download coming soon</span>
      )}

      <div className="facts">
        <div className="fact"><b>{ready ? formatSize(r.installer.sizeBytes) : "≈ 700 MB"}</b><span>one complete installer</span></div>
        <div className="fact"><b>Windows 10 / 11</b><span>64-bit</span></div>
        <div className="fact"><b>Offline</b><span>speech models included</span></div>
        <div className="fact"><b>{r.releaseDate ?? "—"}</b><span>release date</span></div>
      </div>

      <p className="muted">
        The installer contains everything: the app, its runtime and the {r.models.items.length} offline speech models
        (voice commands and dictation). No Python, no extra downloads, no account. Your profiles and calibration are kept
        when you update.
      </p>
      {ready && r.installer.sha256 && (
        <p className="small muted" style={{ marginTop: 14 }}>
          SHA-256: <span className="mono">{r.installer.sha256}</span>
        </p>
      )}
    </div>
  );
}
