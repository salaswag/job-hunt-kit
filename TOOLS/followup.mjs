// Follow-up clock on the Notion Applications rows (TOOLS/FOLLOWUP_PROMPT.md).
// node TOOLS/followup.mjs backfill            fills "Follow up on" (Applied + the track's days in config/kit.json followup_days)
// node TOOLS/followup.mjs due [YYYY-MM-DD]    JSON list of rows due that day, in track order (config/kit.json tracks)
// node TOOLS/followup.mjs set <page_id> "<Follow-up>" [YYYY-MM-DD|-] ["call script"]
// node TOOLS/followup.mjs stats               does a follow-up get an answer? counts per track
import { H as h, DS, CFG } from "./kit.mjs";

const days = (track) => CFG.followup_days?.[track] ?? CFG.followup_days?.default ?? 10;
const order = (track) => { const i = (CFG.tracks || []).indexOf(track); return i < 0 ? 99 : i; };
const SENT = ["Email sent", "LinkedIn sent", "Called"];
const today = new Date().toLocaleDateString("en-CA");
const addDays = (d, n) => { const t = new Date(d + "T12:00:00Z"); t.setUTCDate(t.getUTCDate() + n); return t.toISOString().slice(0, 10); };

async function query(filter) {
  const out = []; let cursor;
  do {
    const r = await (await fetch(`https://api.notion.com/v1/data_sources/${DS}/query`, { method: "POST", headers: h, body: JSON.stringify({ filter, page_size: 100, start_cursor: cursor }) })).json();
    if (!r.results) throw new Error(JSON.stringify(r).slice(0, 300));
    out.push(...r.results); cursor = r.has_more ? r.next_cursor : undefined;
  } while (cursor);
  return out;
}
const val = (p, k) => { const v = p.properties[k]; if (!v) return ""; const x = v[v.type];
  return v.type === "title" || v.type === "rich_text" ? x.map((y) => y.plain_text).join("") : v.type === "select" ? x?.name || "" : v.type === "date" ? x?.start || "" : v.type === "number" ? x : v.type === "url" ? x || "" : ""; };
async function patch(id, props) {
  const r = await fetch(`https://api.notion.com/v1/pages/${id}`, { method: "PATCH", headers: h, body: JSON.stringify({ properties: props }) });
  if (!r.ok) throw new Error(`${r.status} ${(await r.text()).slice(0, 300)}`);
}
const sel = (name) => ({ select: { name } });
const date = (d) => ({ date: d ? { start: d } : null });
const text = (s) => ({ rich_text: [{ text: { content: String(s).slice(0, 1990) } }] });

const [cmd, ...args] = process.argv.slice(2);

if (cmd === "backfill") {
  for (const p of await query({ property: "Applied", date: { is_not_empty: true } })) {
    const st = val(p, "Status"), fu = val(p, "Follow-up"), due = val(p, "Follow up on"), track = val(p, "Track");
    let props = null;
    if (st === "Submitted" && !fu) props = { "Follow-up": sel("Waiting"), "Follow up on": date(due || addDays(val(p, "Applied"), days(track))) };
    else if (["Rejected", "Interview", "Offer"].includes(st) && SENT.includes(fu)) props = { "Follow-up": sel("Replied") };
    else if (st !== "Submitted" && (!fu || fu === "Waiting")) props = { "Follow-up": sel("Skipped") };
    else if (fu === "Call" && due && due < addDays(today, -4)) props = { "Follow-up": sel("No reply") }; // call window passed
    if (props) { await patch(p.id, props); console.log(track, st, "->", props["Follow-up"].select.name, props["Follow up on"]?.date?.start || "", "|", val(p, "Job")); }
  }
} else if (cmd === "due") {
  const day = args[0] || today;
  const filter = { and: [{ property: "Follow up on", date: { on_or_before: day } }, { property: "Status", select: { equals: "Submitted" } },
    { or: ["Waiting", "Email sent", "LinkedIn sent"].map((v) => ({ property: "Follow-up", select: { equals: v } })) }] };
  const rows = (await query(filter)).map((p) => ({ id: p.id, track: val(p, "Track"), company: val(p, "Company"), job: val(p, "Job"),
    applied: val(p, "Applied"), due: val(p, "Follow up on"), followup: val(p, "Follow-up"), recruiter: val(p, "Recruiter"), url: val(p, "URL"),
    match: val(p, "Match score") || 0 }));
  rows.sort((a, b) => (order(a.track) - order(b.track)) || (b.match - a.match) || a.due.localeCompare(b.due));
  console.log(JSON.stringify(rows, null, 1));
} else if (cmd === "set") {
  const [id, fu, next, script] = args;
  const props = { "Follow-up": sel(fu) };
  if (next && next !== "-") props["Follow up on"] = date(next);
  if (script) props["Call script"] = text(script);
  await patch(id, props); console.log("ok", fu, next || "", script ? "(call script)" : "");
} else if (cmd === "stats") {
  const all = await query({ property: "Applied", date: { is_not_empty: true } });
  for (const track of [...new Set(all.map((p) => val(p, "Track")))]) {
    const rows = all.filter((p) => val(p, "Track") === track);
    const followed = rows.filter((p) => [...SENT, "Replied", "No reply"].includes(val(p, "Follow-up")));
    const answered = followed.filter((p) => val(p, "Follow-up") === "Replied");
    const interviews = (xs) => xs.filter((p) => ["Interview", "Offer"].includes(val(p, "Status"))).length;
    const rest = rows.filter((p) => !followed.includes(p));
    console.log(`${track || "(no track)"}: followed up ${followed.length}, answered ${answered.length}, interviews ${interviews(followed)} | not followed up ${rest.length}, interviews ${interviews(rest)} | waiting ${rows.filter((p) => val(p, "Follow-up") === "Waiting").length}`);
  }
} else {
  console.log("usage: backfill | due [YYYY-MM-DD] | set <page_id> <Follow-up> [date|-] [call script] | stats"); process.exit(1);
}
