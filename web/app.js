// Minimal plan B poller. Reads #d= fragment once into localStorage.
const params = new URLSearchParams(location.hash.slice(1));
const d = params.get('d');
if (d) localStorage.setItem('d', d);
const path = localStorage.getItem('d');

async function poll() {
  if (!path) return;
  try {
    const r = await fetch(`/d/${path}/state.json?t=${Date.now()}`);
    if (!r.ok) return;
    const s = await r.json();
    const el = document.getElementById('bal');
    if (el) el.textContent = `$${s.balance.toFixed(2)}`;
  } catch (e) {}
}
setInterval(poll, 15000);
poll();
