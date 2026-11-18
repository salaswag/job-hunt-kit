// Shared settings for the Node helpers: config/kit.json plus the Notion token from
// %USERPROFILE%\.job_hunt\credentials.env (outside this folder, so it never lands in git).
import fs from "node:fs"; import os from "node:os"; import path from "node:path"; import { fileURLToPath } from "node:url";

export const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const cfgPath = path.join(ROOT, "config", "kit.json");
const credPath = path.join(os.homedir(), ".job_hunt", "credentials.env");
if (!fs.existsSync(cfgPath)) throw new Error("config/kit.json is missing: open this folder in Claude Code and say \"set me up\" (START_HERE.md)");
if (!fs.existsSync(credPath)) throw new Error("%USERPROFILE%\\.job_hunt\\credentials.env is missing (START_HERE.md, step 5)");

export const CFG = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
export const CRED = Object.fromEntries(fs.readFileSync(credPath, "utf8").split(/\r?\n/)
  .filter((l) => l.includes("=") && !l.startsWith("#")).map((l) => [l.slice(0, l.indexOf("=")).trim(), l.slice(l.indexOf("=") + 1).trim()]));
if (!CRED.NOTION_TOKEN) throw new Error("NOTION_TOKEN is missing in %USERPROFILE%\\.job_hunt\\credentials.env (START_HERE.md, step 5)");

export const HBASE = { Authorization: `Bearer ${CRED.NOTION_TOKEN}`, "Notion-Version": "2025-09-03" };
export const H = { ...HBASE, "content-type": "application/json" };
export const DS = CFG.notion?.applications_ds;      // the Applications table
export const JUDGMENT_DS = CFG.notion?.judgment_ds; // the Judgment calls table
