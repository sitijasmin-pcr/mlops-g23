// Prompt sistem hanya dibaca backend. Data visual diambil melalui FastAPI.
export async function loadWorkers(){ const r=await fetch('/api/workers'); if(!r.ok)throw Error('Backend belum berjalan. Jalankan FastAPI terlebih dahulu.');return r.json(); }
