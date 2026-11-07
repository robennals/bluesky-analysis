// Replay Jetstream slots and keep the targets of likes, reposts and follows (what is read/endorsed, and who is followed).
// Usage: node jetstream-engagement.mjs <hoursBack> <everyHours> <slotMinutes> <outdir>
import fs from "node:fs";
const [hoursBack, everyH, slotMin] = process.argv.slice(2, 5).map(Number);
const out = process.argv[5] ?? "../data/engagement";
fs.mkdirSync(out, { recursive: true });
const now = Date.now();
const starts = [];
for (let h = hoursBack; h > 0; h -= everyH) starts.push(now - h * 3600e3);
const want = ["app.bsky.feed.like", "app.bsky.feed.repost", "app.bsky.graph.follow"].map(c => `wantedCollections=${c}`).join("&");

function runSlot(startMs) {
  return new Promise((resolve) => {
    const endUs = (startMs + slotMin * 60e3) * 1000;
    const tag = new Date(startMs).toISOString().slice(0, 16);
    const f = fs.createWriteStream(`${out}/eng-${tag}.tsv`);
    let n = 0, done = false;
    const ws = new WebSocket(`wss://jetstream2.us-east.bsky.network/subscribe?${want}&cursor=${startMs * 1000}`);
    const finish = () => { if (done) return; done = true; ws.close(); f.end(() => { console.log(`${tag}: ${n}`); resolve(); }); };
    ws.onmessage = (m) => {
      const e = JSON.parse(m.data);
      if (e.time_us > endUs) return finish();
      if (e.kind !== "commit" || e.commit.operation !== "create") return;
      const c = e.commit, s = c.record?.subject;
      const kind = c.collection.split(".").pop();
      const target = typeof s === "string" ? s : s?.uri;
      if (!target) return;
      n++;
      f.write(`${kind}\t${e.did}\t${target}\n`);
    };
    ws.onerror = () => { console.error(`${tag}: ws error`); finish(); };
  });
}
for (const s of starts) await runSlot(s);
console.log("all slots done");
