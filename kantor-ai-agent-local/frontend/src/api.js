export async function health(){try{const r=await fetch('/api/health',{signal:AbortSignal.timeout(7000)});if(!r.ok)throw Error();return await r.json()}catch{return null}}
export async function chat(worker_id,messages,onEvent,signal){
 let response; try{response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({worker_id,messages}),signal})}catch(e){if(e.name==='AbortError')throw e;throw Error('Backend belum berjalan. Jalankan FastAPI terlebih dahulu.')}
 if(!response.ok){const body=await response.json().catch(()=>({}));throw Error(body.detail||'Pesan tidak dapat dikirim.')}
 const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',done=false;
 function consume(){let i;while((i=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,i);buffer=buffer.slice(i+2);for(const line of block.split('\n')){if(!line.startsWith('data:'))continue;const data=JSON.parse(line.slice(5));if(data.type==='error')throw Error(data.message);if(data.type==='done')done=true;onEvent(data)}}}
 try{while(true){const part=await reader.read();if(part.done)break;buffer+=decoder.decode(part.value,{stream:true}).replace(/\r/g,'');consume()}buffer+=decoder.decode();consume();if(!done)throw Error('Koneksi terputus. Silakan coba kembali.')}finally{await reader.cancel();reader.releaseLock()}
}
