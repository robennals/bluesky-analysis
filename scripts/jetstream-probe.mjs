// Check how far back Jetstream can replay: connect with a cursor N hours ago and report the first event's time.
const hours = Number(process.argv[2]);
const cursor = (Date.now() - hours * 3600e3) * 1000;
const ws = new WebSocket(`wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post&cursor=${cursor}`);
ws.onmessage = (m) => { const e = JSON.parse(m.data); console.log(`asked ${hours}h back -> first event ${new Date(e.time_us / 1000).toISOString()}`); process.exit(0); };
ws.onerror = () => { console.log(`asked ${hours}h back -> error`); process.exit(0); };
setTimeout(() => { console.log(`asked ${hours}h back -> timeout`); process.exit(0); }, 15000);
