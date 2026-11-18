import fs from "node:fs"; import os from "node:os";
import { H as h, DS, CFG, CRED } from "./kit.mjs";
const day = process.argv[2];
const body = { filter: { property: "Applied", date: { equals: day } }, page_size: 100 };
// node TOOLS/count_today.mjs YYYY-MM-DD   prints Status | Track | Job for every row applied that day
for (const ds of [DS]) {
const r = await (await fetch(`https://api.notion.com/v1/data_sources/${ds}/query`, { method: "POST", headers: h, body: JSON.stringify(body) })).json();
if (!r.results) { console.log(JSON.stringify(r).slice(0, 400)); process.exit(1); }
for (const p of r.results) { const pr = p.properties; const g = (k) => { const v = pr[k]; if (!v) return ""; const x = v[v.type]; return v.type === "title" || v.type === "rich_text" ? x.map(y => y.plain_text).join("") : v.type === "select" || v.type === "status" ? x?.name : ""; };
  console.log([g("Status"), g("Track"), Object.values(pr).find(v => v.type === "title").title.map(y => y.plain_text).join("")].join(" | ")); }
}
