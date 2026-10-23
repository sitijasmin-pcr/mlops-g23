import {test} from 'node:test';
import assert from 'node:assert/strict';
import {chat} from './api.js';

test('SSE menangani token UTF-8 yang terpotong antar chunk', async()=>{
 const original=globalThis.fetch;
 const bytes=new TextEncoder().encode('data: {"type":"token","content":"Halo 👋"}\n\ndata: {"type":"done"}\n\n');
 globalThis.fetch=async()=>new Response(new ReadableStream({start(controller){for(const byte of bytes)controller.enqueue(new Uint8Array([byte]));controller.close()}}));
 try{const events=[];await chat('rina',[],event=>events.push(event));assert.deepEqual(events,[{type:'token',content:'Halo 👋'},{type:'done'}])}finally{globalThis.fetch=original}
});
test('SSE tanpa penanda selesai dilaporkan sebagai error',async()=>{
 const original=globalThis.fetch;globalThis.fetch=async()=>new Response('data: {"type":"token","content":"Sebagian"}\n\n');
 try{await assert.rejects(()=>chat('rina',[],()=>{}),/Koneksi terputus/)}finally{globalThis.fetch=original}
});
