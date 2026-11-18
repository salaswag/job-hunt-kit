// The "Needs you" box at the top of the Notion job hunt page: things only you can do.
//   node TOOLS/needs_you.mjs list
//   node TOOLS/needs_you.mjs add "<company: what to do, link>" [--ping]   --ping also @mentions you in a page comment,
//                                                                        which the Notion phone app shows as a notification
//   node TOOLS/needs_you.mjs done "<words from the line>"                removes every line that contains those words
import { H as h, CFG } from "./kit.mjs";

const box = CFG.notion?.needs_you_block;
if (!box) { console.log("No Needs you box yet: run node TOOLS/setup_notion.mjs first"); process.exit(1); }
const api = async (method, url, body) => {
  const r = await fetch("https://api.notion.com" + url, { method, headers: h, body: body && JSON.stringify(body) });
  if (!r.ok) throw new Error(`${r.status} ${(await r.text()).slice(0, 300)}`);
  return r.json();
};
const lines = async () => (await api("GET", `/v1/blocks/${box}/children?page_size=100`)).results
  .filter((b) => b.type === "bulleted_list_item").map((b) => ({ id: b.id, text: b.bulleted_list_item.rich_text.map((t) => t.plain_text).join("") }));

const [cmd, arg, flag] = process.argv.slice(2);
if (cmd === "list") {
  for (const l of await lines()) console.log("-", l.text);
} else if (cmd === "add" && arg) {
  const line = `${new Date().toLocaleDateString("en-CA")}: ${arg}`;
  if ((await lines()).some((l) => l.text.endsWith(arg))) { console.log("already there"); process.exit(0); }
  await api("PATCH", `/v1/blocks/${box}/children`, { children: [{ type: "bulleted_list_item", bulleted_list_item: { rich_text: [{ type: "text", text: { content: line.slice(0, 1990) } }] } }] });
  console.log("added:", line);
  if (flag === "--ping" && CFG.notion.owner_user_id) {
    await api("POST", "/v1/comments", { parent: { page_id: CFG.notion.page_id }, rich_text: [
      { type: "mention", mention: { type: "user", user: { id: CFG.notion.owner_user_id } } },
      { type: "text", text: { content: " " + arg.slice(0, 1900) } }] });
    console.log("pinged you in a page comment");
  }
} else if (cmd === "done" && arg) {
  let n = 0;
  for (const l of await lines()) if (l.text.toLowerCase().includes(arg.toLowerCase())) { await api("DELETE", `/v1/blocks/${l.id}`); n++; }
  console.log(`removed ${n}`);
} else {
  console.log('usage: list | add "<line>" [--ping] | done "<words>"'); process.exit(1);
}
