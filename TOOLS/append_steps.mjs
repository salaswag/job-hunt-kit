// node append_steps.mjs steps.json  ({page_id: ["step", ...]})  Appends bullet steps to each page body.
import fs from "node:fs"; import os from "node:os";
import { H as h, DS, CFG, CRED } from "./kit.mjs";
for (const [id, steps] of Object.entries(JSON.parse(fs.readFileSync(process.argv[2], "utf8")))) {
  const children = steps.map((s) => ({ type: "bulleted_list_item", bulleted_list_item: { rich_text: [{ type: "text", text: { content: s } }] } }));
  const r = await fetch(`https://api.notion.com/v1/blocks/${id}/children`, { method: "PATCH", headers: h, body: JSON.stringify({ children }) });
  console.log(r.status, id);
}
