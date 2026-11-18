// Tiny Notion API caller using the kit's Notion token (never printed). Usage: node notion_api.mjs METHOD /v1/path body.json
import fs from "node:fs"; import os from "node:os";
import { HBASE as h } from "./kit.mjs";
const [method, path, bodyFile] = process.argv.slice(2);
const r = await fetch("https://api.notion.com" + path, { method, headers: { ...h, "Notion-Version": "2025-09-03", "content-type": "application/json" }, body: bodyFile ? fs.readFileSync(bodyFile, "utf8") : undefined });
const j = await r.json(); console.log(r.status, JSON.stringify(j).slice(0, 1500));
