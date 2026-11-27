import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import "./enhance.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { site } from "@/config/site";

// Same Inter files as the desktop app (desktop/assets/fonts), self-hosted: no network at build or runtime.
const inter = localFont({
  src: [
    { path: "../fonts/Inter-Regular.ttf", weight: "400", style: "normal" },
    { path: "../fonts/Inter-Medium.ttf", weight: "500", style: "normal" },
    { path: "../fonts/Inter-SemiBold.ttf", weight: "600", style: "normal" },
    { path: "../fonts/Inter-SemiBold.ttf", weight: "700", style: "normal" },
  ],
  variable: "--font-inter",
  display: "swap",
});
// Headings: Sora (geometric, OFL), self-hosted variable font
const sora = localFont({
  src: [{ path: "../fonts/Sora-Variable.woff2", weight: "100 800", style: "normal" }],
  variable: "--font-sora",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://ishara-mu-three.vercel.app"),
  title: { default: `${site.name}: ${site.tagline}`, template: `%s Â· ${site.name}` },
  description: site.description,
  openGraph: { title: `${site.name}: ${site.tagline}`, description: site.description, type: "website" },
};

export const viewport: Viewport = {
  themeColor: "#f5f5f7",
  colorScheme: "light",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${sora.variable}`} suppressHydrationWarning>
      <head>
        {/* marks that JavaScript runs, so reveal animations may start hidden */}
        <script dangerouslySetInnerHTML={{ __html: "document.documentElement.classList.add('js')" }} />
      </head>
      <body>
        <a href="#main" className="sr-skip">Skip to content</a>
        <Header />
        <main id="main"><div className="bg-deco" aria-hidden />{children}</main>
        <Footer />
      </body>
    </html>
  );
}
