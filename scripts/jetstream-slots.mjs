// Replay Jetstream history in time slots (e.g. 2 minutes every 2 hours over the last ~34h).
// For each slot: count every record type (and which accounts wrote them) and save every new post.
// Usage: node jetstream-slots.mjs <hoursBack> <everyHours> <slotMinutes> <outdir>
import fs from "node:fs";
const [hoursBack, everyH, slotMin] = process.argv.slice(2, 5).map(Number);
const out = process.argv[5] ?? "../data/slots";
fs.mkdirSync(out, { recursive: true });
const now = Date.now();
const starts = [];
for (let h = hoursBack; h > 0; h -= everyH) starts.push(now - h * 3600e3);

function runSlot(startMs) {
  return new Promise((resolve) => {
    const endUs = (startMs + slotMin * 60e3) * 1000;
    const tag = new Date(startMs).toISOString().slice(0, 16);
    const posts = fs.createWriteStream(`${out}/posts-${tag}.jsonl`);
    const counts = {}, writers = {};
    let n = 0;
    const ws = new WebSocket(`wss://jetstream2.us-east.bsky.network/subscribe?cursor=${startMs * 1000}`);
    const finish = () => {
      ws.close();
      const writerCounts = Object.fromEntries(Object.entries(writers).map(([k, s]) => [k, s.size]));
      fs.writeFileSync(`${out}/counts-${tag}.json`, JSON.stringify({ start: tag, slotMin, events: n, counts, writers: writerCounts }));
      posts.end(() => { console.log(`${tag}: ${n} events`); resolve(); });
    };
    ws.onmessage = (m) => {
      const e = JSON.parse(m.data);
      if (e.time_us > endUs) return finish();
      n++;
      if (e.kind !== "commit") return;
      const c = e.commit, key = `${c.collection} ${c.operation}`;
      counts[key] = (counts[key] ?? 0) + 1;
      if (c.operation !== "create") return;
      (writers[c.collection] ??= new Set()).add(e.did);
      if (c.collection === "app.bsky.feed.post") {
        const r = c.record;
        posts.write(JSON.stringify({ did: e.did, rkey: c.rkey, t: r.createdAt, text: r.text, langs: r.langs,
          reply: !!r.reply, embed: r.embed?.$type, ext: r.embed?.external?.uri ?? r.embed?.media?.external?.uri,
          extTitle: r.embed?.external?.title ?? r.embed?.media?.external?.title,
          tags: (r.facets ?? []).flatMap(f => f.features).filter(f => f.tag).map(f => f.tag) }) + "\n");
      }
    };
    ws.onerror = () => { console.error(`${tag}: ws error`); finish(); };
  });
}
for (const s of starts) await runSlot(s);
console.log("all slots done");
