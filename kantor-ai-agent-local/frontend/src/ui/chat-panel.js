import {chat} from '../api.js';
import './chat-panel.css';

const MAX_IMAGE_BYTES=5*1024*1024;
const MAX_IMAGES=4;
const IMAGE_TYPES=new Set(['image/png','image/jpeg','image/webp']);

function readImage(file){
 return new Promise((resolve,reject)=>{
  const reader=new FileReader();
  reader.onload=()=>resolve({name:file.name,dataUrl:reader.result});
  reader.onerror=()=>reject(Error(`Gambar "${file.name}" tidak dapat dibaca.`));
  reader.readAsDataURL(file);
 });
}

export function createChat(workers,onState){
 let active=null;
 const histories=new Map(workers.map(worker=>[worker.id,[]]));
 const pending=new Map();
 let attachments=[];
 let readingImages=false;
 const panel=document.querySelector('#chat');
 const feed=document.querySelector('#messages');
 const input=document.querySelector('#message');
 const picker=document.querySelector('#image-upload');
 const preview=document.querySelector('#attachment-preview');

 function paintAttachments(){
  preview.replaceChildren();
  for(const [index,image] of attachments.entries()){
   const item=document.createElement('div');
   item.className='attachment-item';
   const thumbnail=document.createElement('img');
   thumbnail.src=image.dataUrl;
   thumbnail.alt=image.name;
   const name=document.createElement('span');
   name.textContent=image.name;
   const remove=document.createElement('button');
   remove.type='button';
   remove.textContent='×';
   remove.setAttribute('aria-label',`Hapus ${image.name}`);
   remove.onclick=()=>{attachments.splice(index,1);paintAttachments()};
   item.append(thumbnail,name,remove);
   preview.append(item);
  }
 }

 function paint(){
  if(!active)return;
  const worker=workers.find(item=>item.id===active);
  document.querySelector('#chat-name').textContent=worker.name;
  document.querySelector('#chat-role').textContent=worker.role;
  document.querySelector('#chat-avatar').textContent=worker.name[0];
  document.querySelector('#chat-avatar').style.background=worker.color;
  feed.replaceChildren();
  const rows=histories.get(active);
  if(!rows.length){
   const welcome=document.createElement('p');
   welcome.className='welcome';
   welcome.textContent='Halo, saya '+worker.name+'. '+worker.description+' Apa yang ingin kita kerjakan hari ini?';
   feed.append(welcome);
  }
  for(const row of rows){
   const bubble=document.createElement('div');
   bubble.className='bubble '+row.role;
   if(row.content)bubble.append(document.createTextNode(row.content));
   for(const image of row.images||[]){
    const thumbnail=document.createElement('img');
    thumbnail.className='message-image';
    thumbnail.src=image.dataUrl;
    thumbnail.alt=image.name;
    bubble.append(thumbnail);
   }
   if(!row.content&&row.role==='assistant')bubble.textContent='Sedang berpikir…';
   feed.append(bubble);
  }
  document.querySelector('#send').disabled=pending.has(active)||readingImages;
  document.querySelector('#attach').disabled=pending.has(active)||readingImages;
  document.querySelector('#clear').disabled=pending.has(active);
  document.querySelector('#chat-state').textContent=readingImages?'Menyiapkan gambar…':pending.has(active)?'Sedang menyusun jawaban…':'Percakapan pribadi • sesi ini';
  feed.scrollTop=feed.scrollHeight;
 }

 async function selectImages(){
  const selected=Array.from(picker.files||[]);
  picker.value='';
  if(!selected.length)return;
  if(readingImages)return;
  if(attachments.length+selected.length>MAX_IMAGES){
   showError(`Maksimal ${MAX_IMAGES} gambar dalam satu pesan.`);
   return;
  }
  const invalid=selected.find(file=>!IMAGE_TYPES.has(file.type));
  if(invalid){
   showError(`Format "${invalid.name}" tidak didukung. Pilih PNG, JPEG, atau WEBP.`);
   return;
  }
  const oversized=selected.find(file=>file.size>MAX_IMAGE_BYTES);
  if(oversized){
   showError(`Ukuran "${oversized.name}" melebihi batas 5 MB.`);
   return;
  }
  const selectedFor=active;
  readingImages=true;
  paint();
  try{
   const loaded=await Promise.all(selected.map(readImage));
   if(active===selectedFor){
    attachments.push(...loaded);
    showError('');
    paintAttachments();
   }
  }catch(error){
   if(active===selectedFor)showError(error.message);
  }finally{
   readingImages=false;
   paint();
  }
 }

 async function send(event){
  event?.preventDefault();
  const text=input.value.trim();
  if(!active||(!text&&!attachments.length)||pending.has(active)||readingImages)return;
  const id=active;
  const history=histories.get(id);
  if(history.length>=30){
   showError('Riwayat mencapai batas 30 pesan. Hapus percakapan untuk memulai lagi.');
   return;
  }
  const images=attachments;
  history.push({role:'user',content:text,images});
  const request=history.filter(message=>message.content||message.images?.length).map(message=>{
   if(!message.images?.length)return {role:message.role,content:message.content};
   const content=[];
   if(message.content)content.push({type:'text',text:message.content});
   for(const image of message.images)content.push({type:'image_url',image_url:{url:image.dataUrl}});
   return {role:message.role,content};
  });
  const answer={role:'assistant',content:''};
  history.push(answer);
  const controller=new AbortController();
  pending.set(id,controller);
  input.value='';
  attachments=[];
  paintAttachments();
  showError('');
  onState(id,'thinking');
  paint();
  try{
   await chat(id,request,data=>{
    if(data.type==='token'){
     answer.content+=data.content;
     if(active===id)paint();
    }
   },controller.signal);
   onState(id,'done');
  }catch(error){
   onState(id,'idle');
   if(!answer.content)history.splice(history.indexOf(answer),1);
   if(active===id)showError(error.message);
  }finally{
   pending.delete(id);
   if(active===id)paint();
  }
 }

 function showError(text){
  document.querySelector('#chat-error').textContent=text;
 }

 document.querySelector('#chat-form').addEventListener('submit',send);
 input.addEventListener('keydown',event=>{
  if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send()}
 });
 document.querySelector('#attach').onclick=()=>picker.click();
 picker.addEventListener('change',selectImages);
 document.querySelector('#clear').onclick=()=>{
  if(active&&!pending.has(active)){histories.set(active,[]);showError('');paint()}
 };
 document.querySelector('#close-chat').onclick=()=>panel.classList.add('closed');
 return {
  open(id){
   active=id;
   attachments=[];
   paintAttachments();
   panel.classList.remove('closed');
   showError('');
   paint();
   input.focus();
  }
 };
}
