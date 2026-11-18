import fs from "node:fs"; import os from "node:os";
import { H as h, DS, CFG, CRED } from "./kit.mjs";
for (const ds of process.argv.slice(2)) {
  const r = await (await fetch(`https://api.notion.com/v1/data_sources/${ds}/query`, { method: "POST", headers: h, body: "{}" })).json();
  for (const p of r.results || []) {
    const o = {};
    for (const [k, v] of Object.entries(p.properties)) {
      const t = v.type, x = v[t];
      o[k] = t === "title" || t === "rich_text" ? x.map(y => y.plain_text).join("") : t === "select" ? x?.name : t === "multi_select" ? x.map(y => y.name).join(",") : t === "number" || t === "url" || t === "checkbox" ? x : t === "date" ? x?.start : undefined;
    }
    console.log(p.id, JSON.stringify(o));
  }
  console.log("----");
}
