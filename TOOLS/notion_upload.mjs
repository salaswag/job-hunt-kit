// Attach local files to a Notion page's files property. Usage: node notion_upload.mjs <page_id> "<Property>" <file> [file...]
import fs from "node:fs"; import os from "node:os"; import path from "node:path";
import { HBASE as h } from "./kit.mjs";
const [page, prop, ...files] = process.argv.slice(2);
const items = [];
for (const f of files) {
  const name = path.basename(f);
  const up = await (await fetch("https://api.notion.com/v1/file_uploads", { method: "POST", headers: { ...h, "content-type": "application/json" }, body: JSON.stringify({ filename: name, content_type: "application/pdf" }) })).json();
  if (!up.id) throw new Error(JSON.stringify(up).slice(0, 300));
  const form = new FormData(); form.append("file", new Blob([fs.readFileSync(f)], { type: "application/pdf" }), name);
  const sent = await (await fetch(`https://api.notion.com/v1/file_uploads/${up.id}/send`, { method: "POST", headers: h, body: form })).json();
  if (sent.status !== "uploaded") throw new Error(JSON.stringify(sent).slice(0, 300));
  items.push({ type: "file_upload", file_upload: { id: up.id }, name });
}
const r = await fetch(`https://api.notion.com/v1/pages/${page}`, { method: "PATCH", headers: { ...h, "content-type": "application/json" }, body: JSON.stringify({ properties: { [prop]: { files: items } } }) });
console.log(r.status, prop, files.map((f) => path.basename(f)).join(", "), r.ok ? "attached" : (await r.text()).slice(0, 300));
