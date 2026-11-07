// Collect sample records written by non-Bluesky atproto apps, replaying Jetstream history.
// Usage: node jetstream-apps.mjs <hoursBack> <minutesToRun> <perApp> <out.json>
import fs from "node:fs";
const [hoursBack, minutes, perApp] = process.argv.slice(2, 5).map(Number);
const out = process.argv[5];
const apps = JSON.parse(fs.readFileSync("../data/app-share.json")).map(([k]) => k).filter((k) => k !== "Bluesky").slice(0, 16);
const q = apps.map((a) => `wantedCollections=${a}.*`).join("&");
const got = Object.fromEntries(apps.map((a) => [a, []]));
const seenDid = Object.fromEntries(apps.map((a) => [a, {}]));
const ws = new WebSocket(`wss://jetstream2.us-east.bsky.network/subscribe?${q}&cursor=${(Date.now() - hoursBack * 3600e3) * 1000}`);
const finish = () => { fs.writeFileSync(out, JSON.stringify(got)); console.log(Object.entries(got).map(([k, v]) => `${k}:${v.length}`).join(" ")); process.exit(0); };
ws.onmessage = (m) => {
  const e = JSON.parse(m.data);
  if (e.kind !== "commit" || e.commit.operation !== "create") return;
  const c = e.commit, a = apps.find((x) => c.collection.startsWith(x + "."));
  if (!a) return;
  seenDid[a][e.did] = (seenDid[a][e.did] ?? 0) + 1;
  if (seenDid[a][e.did] > 3 || got[a].length >= perApp * 4) return;   // keep variety: at most 3 records per account
  got[a].push({ did: e.did, collection: c.collection, rkey: c.rkey, record: JSON.stringify(c.record).slice(0, 1500) });
};
ws.onerror = () => { console.error("ws error"); finish(); };
setTimeout(finish, minutes * 60e3);
