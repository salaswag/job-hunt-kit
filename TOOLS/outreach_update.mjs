// node outreach_update.mjs updates.json  ([{company, job?, recruiter, outreach}])  Patches Submitted rows matching Company (and Job title substring).
import fs from "node:fs"; import os from "node:os";
import { H as h, DS, CFG, CRED } from "./kit.mjs";
for (const u of JSON.parse(fs.readFileSync(process.argv[2], "utf8"))) {
  const and = [{ property: "Company", rich_text: { contains: u.company } }, { property: "Status", select: { equals: "Submitted" } }];
  if (u.job) and.push({ property: "Job", title: { contains: u.job } });
  const r = await (await fetch(`https://api.notion.com/v1/data_sources/${DS}/query`, { method: "POST", headers: h, body: JSON.stringify({ filter: { and } }) })).json();
  for (const p of r.results || []) {
    const old = p.properties["Recruiter outreach"].multi_select.map((x) => x.name);
    const props = { "Recruiter outreach": { multi_select: [...new Set([...old, u.outreach])].map((name) => ({ name })) } };
    if (u.recruiter) props.Recruiter = { rich_text: [{ text: { content: u.recruiter } }] };
    const pr = await fetch(`https://api.notion.com/v1/pages/${p.id}`, { method: "PATCH", headers: h, body: JSON.stringify({ properties: props }) });
    console.log(pr.status, u.company, p.properties.Job.title.map((x) => x.plain_text).join(""));
  }
  if (!(r.results || []).length) console.log("NO ROW", u.company, JSON.stringify(r).slice(0, 200));
}
