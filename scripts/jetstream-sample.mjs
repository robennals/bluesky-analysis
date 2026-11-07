// Sample the Bluesky Jetstream firehose: count every record type, save every new post.
// Usage: node jetstream-sample.mjs <minutes> <outdir>
import fs from "node:fs";
const minutes = Number(process.argv[2] ?? 10), out = process.argv[3] ?? "../data/jetstream";
fs.mkdirSync(out, { recursive: true });
const posts = fs.createWriteStream(`${out}/posts.jsonl`);
const counts = {}, perDid = {}, ops = {};
let n = 0;
const ws = new WebSocket("wss://jetstream2.us-east.bsky.network/subscribe");
ws.onmessage = (m) => {
  const e = JSON.parse(m.data);
  n++;
  if (e.kind !== "commit") { counts[`_${e.kind}`] = (counts[`_${e.kind}`] ?? 0) + 1; return; }
  const c = e.commit, key = `${c.collection} ${c.operation}`;
  counts[key] = (counts[key] ?? 0) + 1;
  if (c.operation !== "create") return;
  perDid[e.did] ??= {};
  perDid[e.did][c.collection] = (perDid[e.did][c.collection] ?? 0) + 1;
  if (c.collection === "app.bsky.feed.post") {
    const r = c.record;
    posts.write(JSON.stringify({ did: e.did, rkey: c.rkey, t: r.createdAt, text: r.text, langs: r.langs,
      reply: !!r.reply, embed: r.embed?.$type, ext: r.embed?.external?.uri ?? r.embed?.media?.external?.uri,
      quote: r.embed?.record?.uri ?? r.embed?.record?.record?.uri,
      tags: (r.facets ?? []).flatMap(f => f.features).filter(f => f.tag).map(f => f.tag),
      links: (r.facets ?? []).flatMap(f => f.features).filter(f => f.uri).map(f => f.uri) }) + "\n");
  }
};
ws.onerror = (err) => console.error("ws error", err.message ?? err);
setTimeout(() => {
  ws.close();
  fs.writeFileSync(`${out}/counts.json`, JSON.stringify({ minutes, events: n, counts, perDid }, null, 0));
  posts.end(() => { console.log(`done: ${n} events in ${minutes} min`); process.exit(0); });
}, minutes * 60_000);
setInterval(() => console.log(new Date().toISOString(), n, "events"), 60_000);
