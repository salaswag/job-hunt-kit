// One-time Notion setup. Builds the job hunt page inside a page you shared with your Notion integration:
// a "Needs you" box at the top, then the Applications table and the Judgment calls table. Writes their IDs into
// config/kit.json, so every other script finds them.
//   node TOOLS/setup_notion.mjs <link or id of the page you shared with the integration>
// Run it once. Running it again makes a second set (the old one stays; delete it in Notion if you want).
import fs from "node:fs"; import path from "node:path";
import { H as h, CFG, ROOT } from "./kit.mjs";

const arg = process.argv[2] || "";
const parent = arg.split("?")[0].match(/[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$/i)?.[0].replace(/-/g, "");
if (!parent) { console.log("usage: node TOOLS/setup_notion.mjs <Notion page link>"); process.exit(1); }

async function call(method, url, body) {
  const r = await fetch("https://api.notion.com" + url, { method, headers: h, body: body && JSON.stringify(body) });
  const j = await r.json();
  if (!r.ok) {
    if (r.status === 404) throw new Error("Notion cannot see that page. Open it in Notion, click ... > Connections, and add your integration. Then run this again.");
    throw new Error(`${r.status} ${JSON.stringify(j).slice(0, 400)}`);
  }
  return j;
}
const opts = (...names) => ({ options: names.map((name) => ({ name })) });
const text = (content) => [{ type: "text", text: { content } }];

// 1. The job hunt page
const page = await call("POST", "/v1/pages", {
  parent: { page_id: parent }, icon: { type: "emoji", emoji: "💼" },
  properties: { title: { title: text("Job Hunt") } },
  children: [
    { type: "heading_2", heading_2: { rich_text: text("Needs you") } },
    { type: "callout", callout: { icon: { type: "emoji", emoji: "🔔" }, color: "orange_background",
      rich_text: text("Things only you can do: interviews to book, CAPTCHA ticks, assessments, calls. Claude adds them here and removes them when done."),
      children: [] } },
    { type: "paragraph", paragraph: { rich_text: text("Every application is a row below. \"Your feedback\" and \"Your take\" are where you talk back: the next run reads them and changes its rules.") } },
  ],
});
const kids = await call("GET", `/v1/blocks/${page.id}/children`);
const box = kids.results.find((b) => b.type === "callout");

// 2. Applications
const tracks = CFG.tracks?.length ? CFG.tracks : ["main"];
const apps = await call("POST", "/v1/databases", {
  parent: { type: "page_id", page_id: page.id }, is_inline: true, title: text("Applications"),
  initial_data_source: { properties: {
    "Job": { title: {} }, "Company": { rich_text: {} },
    "Status": { select: opts("Found", "Applying", "Submitted", "Blocked", "Needs you", "Skipped", "Rejected", "Interview", "Offer") },
    "Track": { select: opts(...tracks) },
    "Site": { select: opts("Greenhouse", "Lever", "Ashby", "Workday", "iCIMS", "BambooHR", "LinkedIn", "Indeed", "Job Bank", "Company site", "Email") },
    "URL": { url: {} }, "Posted": { date: {} }, "Applied": { date: {} }, "Applicants": { number: {} }, "Years asked": { number: {} },
    "Match score": { number: {} }, "Tailored score": { number: {} },
    "Legit check": { select: opts("Looks real", "Unsure", "Scam (skipped)") },
    "Resume": { files: {} }, "Cover letter": { files: {} }, "Blocker": { rich_text: {} }, "Account used": { rich_text: {} },
    "Latest email": { rich_text: {} }, "Recruiter": { rich_text: {} },
    "Recruiter outreach": { multi_select: opts("LinkedIn connect sent", "LinkedIn message sent", "Email sent", "Thank-you sent", "No recruiter found", "Not yet") },
    "Follow-up": { select: opts("Waiting", "Email sent", "LinkedIn sent", "Call", "Called", "Replied", "No reply", "Skipped") },
    "Follow up on": { date: {} }, "Call script": { rich_text: {} }, "Your feedback": { rich_text: {} },
  } },
});

// 3. Judgment calls (calls Claude made under doubt; you answer in "Your take")
const calls = await call("POST", "/v1/databases", {
  parent: { type: "page_id", page_id: page.id }, is_inline: true, title: text("Judgment calls (give me your take)"),
  initial_data_source: { properties: {
    "Call": { title: {} }, "Job": { rich_text: {} }, "What I did": { rich_text: {} }, "Why": { rich_text: {} },
    "Confidence %": { number: {} }, "Date": { date: {} }, "Your take": { rich_text: {} },
    "Status": { select: opts("Waiting on you", "Agreed", "Changed the rule") },
  } },
});

// 4. You (for @mentions that reach the Notion app on your phone)
let owner = "";
try { owner = (await call("GET", "/v1/users")).results.find((u) => u.type === "person")?.id || ""; }
catch { console.log("note: could not read users (turn on \"Read user information\" for the integration to get phone pings)"); }

CFG.notion = { page_id: page.id, page_url: page.url, needs_you_block: box.id, applications_ds: apps.data_sources[0].id,
  judgment_ds: calls.data_sources[0].id, owner_user_id: owner };
fs.writeFileSync(path.join(ROOT, "config", "kit.json"), JSON.stringify(CFG, null, 2) + "\n");
console.log("Notion is ready:", page.url);
console.log(JSON.stringify(CFG.notion, null, 1));
