// node mark_submitted.mjs <page_id> "<site name>" "<step line>"  Status Submitted, Applied today, account logged (CLAUDE.md, Accounts), step appended.
import fs from "node:fs"; import os from "node:os";
import { H as h, DS, CFG, CRED } from "./kit.mjs";
const cred = CRED;
const [id, site, step] = process.argv.slice(2);
const d = new Date(); const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const props = { Status: { select: { name: "Submitted" } }, Applied: { date: { start: today } }, Blocker: { rich_text: [] } };
const pw = process.env.PW_ALNUM ? cred.SITE_PASSWORD.replace(/[^A-Za-z0-9]/g, "") : cred.SITE_PASSWORD;
if (site) props["Account used"] = { rich_text: [{ text: { content: `${site}: ${cred.JOB_EMAIL} / ${pw} (made by TOOLS/acct_apply.py, profile chrome_acct)` } }] };
let r = await fetch(`https://api.notion.com/v1/pages/${id}`, { method: "PATCH", headers: h, body: JSON.stringify({ properties: props }) });
console.log("row", r.status);
if (step) {
  r = await fetch(`https://api.notion.com/v1/blocks/${id}/children`, { method: "PATCH", headers: h, body: JSON.stringify({ children: [{ bulleted_list_item: { rich_text: [{ text: { content: `${today}: ${step}` } }] } }] }) });
  console.log("step", r.status);
}
