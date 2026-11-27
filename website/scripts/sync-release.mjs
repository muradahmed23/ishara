// Copies ../release/latest.json into the website at build time.
// It is the FALLBACK only: at runtime the site reads the live manifest from GitHub,
// so publishing a release needs no redeploy. Runs before dev and build.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../release/latest.json");
const dst = resolve(here, "../src/data/release.json");
mkdirSync(dirname(dst), { recursive: true });
if (existsSync(src)) {
  copyFileSync(src, dst);
  console.log("release manifest synced");
} else if (!existsSync(dst)) {
  throw new Error("release/latest.json not found");
}
