// Add rows to a Notion data source. Usage: node notion_rows.mjs <data_source_id> rows.json  (rows = [{prop: value}] in a short form)
import fs from "node:fs"; import os from "node:os";
import { H as h, DS, CFG, CRED } from "./kit.mjs";
const [ds, file] = process.argv.slice(2);
const ds_schema = await (await fetch(`https://api.notion.com/v1/data_sources/${ds}`, { headers: h })).json();
const conv = (type, v) => ({
  title: { title: [{ text: { content: String(v) } }] }, rich_text: { rich_text: [{ text: { content: String(v).slice(0, 1990) } }] },
  select: { select: { name: v } }, multi_select: { multi_select: [].concat(v).map((name) => ({ name })) },
  number: { number: v }, url: { url: v }, date: { date: { start: v } }, checkbox: { checkbox: !!v },
}[type]);
for (const row of JSON.parse(fs.readFileSync(file, "utf8"))) {
  const properties = {};
  for (const [k, v] of Object.entries(row)) { const t = ds_schema.properties[k]?.type; if (!t) throw new Error("no property " + k); properties[k] = conv(t, v); }
  const r = await fetch("https://api.notion.com/v1/pages", { method: "POST", headers: h, body: JSON.stringify({ parent: { type: "data_source_id", data_source_id: ds }, properties }) });
  const j = await r.json(); console.log(r.status, Object.values(row)[0], r.ok ? j.id : JSON.stringify(j).slice(0, 300));
}
