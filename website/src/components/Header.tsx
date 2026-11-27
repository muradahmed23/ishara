"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { site } from "@/config/site";

export function Header() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header className="header">
      <div className="wrap header-in">
        <Link href="/" className="brand" aria-label="iShara home" onClick={() => setOpen(false)}>
          <span className="mark" aria-hidden /> {site.name}
        </Link>
        <nav className={`nav${open ? " open" : ""}`} aria-label="Main">
          {site.nav.filter((n) => n.href !== "/download").map((n) => (
            <Link key={n.href} href={n.href} aria-current={path === n.href ? "page" : undefined} onClick={() => setOpen(false)}>
              {n.label}
            </Link>
          ))}
          <Link href="/download" className="btn btn-primary btn-sm" onClick={() => setOpen(false)}>Download</Link>
          <button className="menu-btn" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
          </button>
        </nav>
      </div>
    </header>
  );
}
