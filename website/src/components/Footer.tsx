import Link from "next/link";
import { site } from "@/config/site";

export function Footer() {
  return (
    <footer className="footer">
      <div className="wrap footer-in">
        <div>
          <div className="brand" style={{ color: "var(--text)", marginBottom: 8 }}>
            <span className="mark" aria-hidden /> {site.name}
          </div>
          <p>{site.tagline}. Open source, works offline.</p>
        </div>
        <div className="row" style={{ gap: 20 }}>
          {site.nav.map((n) => <Link key={n.href} href={n.href}>{n.label}</Link>)}
          <a href={site.github} target="_blank" rel="noreferrer">GitHub</a>
        </div>
      </div>
    </footer>
  );
}
