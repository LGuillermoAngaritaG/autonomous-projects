#!/usr/bin/env node
// usage.mjs — current 5-hour-window usage % for Claude Code, Codex, OpenCode.
// Reads each tool's own local data. No ccusage, no network.
//
//   claudecode: ~/.claude/rate-limit-cache.json   -> native 5h used_percentage
//   codex:      ~/.codex/sessions/**/*.jsonl       -> native 5h primary.used_percent
//   opencode:   ~/.local/share/opencode/opencode.db -> assistant messages (= provider
//               requests) in the rolling 5h, vs OPENCODE_REQ_LIMIT (880 req / 5h).
//
// Output:
//   claudecode: 9%
//   codex: 23%
//   opencode: 80%

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const home = homedir();
const now = Date.now();
const FIVE_H_MS = 5 * 3600 * 1000;

// ── claudecode ───────────────────────────────────────────────────────────────
// Claude Code writes its own rate-limit snapshot here, including the real 5h %.
function claudePct() {
  try {
    const c = JSON.parse(
      readFileSync(join(home, ".claude", "rate-limit-cache.json"), "utf8"),
    );
    const fh = c.five_hour;
    if (!fh || typeof fh.used_percentage !== "number") return null;
    if (fh.resets_at && fh.resets_at * 1000 <= now) return 0; // window has reset
    return Math.round(fh.used_percentage);
  } catch {
    return null;
  }
}

// ── codex ────────────────────────────────────────────────────────────────────
// Codex logs a rate_limits snapshot in its session jsonl. primary = the 5h window
// (window_minutes 300). Take the most recent snapshot from the newest session.
const PRIMARY_RE =
  /"primary":\{"used_percent":([\d.]+),"window_minutes":300,"resets_at":(\d+)/g;

// Newest day dir is sessions/YYYY/MM/DD — names sort lexicographically, so walking
// the max name at each level lands on the latest day without scanning every year.
function newestDayDir(root) {
  let dir = root;
  for (let depth = 0; depth < 3; depth++) {
    let subs;
    try {
      subs = readdirSync(dir, { withFileTypes: true })
        .filter((e) => e.isDirectory())
        .map((e) => e.name)
        .sort();
    } catch {
      return null;
    }
    if (subs.length === 0) return null;
    dir = join(dir, subs[subs.length - 1]);
  }
  return dir;
}

function codexPct() {
  const dayDir = newestDayDir(join(home, ".codex", "sessions"));
  if (!dayDir) return null;
  let files;
  try {
    files = readdirSync(dayDir)
      .filter((n) => n.endsWith(".jsonl"))
      .map((n) => join(dayDir, n))
      .sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs); // newest first
  } catch {
    return null;
  }
  for (const file of files) {
    let last = null;
    for (const m of readFileSync(file, "utf8").matchAll(PRIMARY_RE)) {
      last = m; // keep the last snapshot in the file
    }
    if (!last) continue;
    const used = parseFloat(last[1]);
    const resetsAt = parseInt(last[2], 10);
    if (resetsAt * 1000 <= now) return 0; // window has reset since this snapshot
    return Math.round(used);
  }
  return null;
}

// ── opencode ─────────────────────────────────────────────────────────────────
// opencode stores no rate-limit %, only messages + timestamps. Each assistant
// message is one provider request, and the plan caps requests per rolling 5h.
const OPENCODE_REQ_LIMIT = 880; // requests per 5h
async function opencodePct() {
  const { XDG_DATA_HOME, LOCALAPPDATA, APPDATA } = process.env;
  const dbPath = [
    XDG_DATA_HOME && join(XDG_DATA_HOME, "opencode", "opencode.db"),
    join(home, ".local", "share", "opencode", "opencode.db"), // Linux + Windows default
    join(home, "Library", "Application Support", "opencode", "opencode.db"), // macOS
    LOCALAPPDATA && join(LOCALAPPDATA, "opencode", "opencode.db"), // Windows fallbacks
    APPDATA && join(APPDATA, "opencode", "opencode.db"),
  ].find((p) => p && existsSync(p));
  if (!dbPath) return null;

  let DatabaseSync;
  const origEmit = process.emitWarning;
  process.emitWarning = () => {}; // hush the node:sqlite ExperimentalWarning
  try {
    ({ DatabaseSync } = await import("node:sqlite"));
  } catch {
    return null;
  } finally {
    process.emitWarning = origEmit;
  }

  let requests;
  try {
    const db = new DatabaseSync(dbPath, { readOnly: true });
    requests = db
      .prepare(
        "SELECT count(*) AS n FROM message WHERE json_extract(data,'$.role')='assistant' AND time_created >= ?",
      )
      .get(now - FIVE_H_MS).n;
    db.close();
  } catch {
    return null;
  }
  return Math.min(100, Math.round((requests / OPENCODE_REQ_LIMIT) * 100));
}

// ── report ───────────────────────────────────────────────────────────────────
const fmt = (p) => (p === null ? "n/a" : `${p}%`);
console.log(`claudecode: ${fmt(claudePct())}`);
console.log(`codex: ${fmt(codexPct())}`);
console.log(`opencode: ${fmt(await opencodePct())}`);
