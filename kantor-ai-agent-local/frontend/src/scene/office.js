import * as THREE from 'three';
import {makeWorker} from './worker.js';
export function createOffice(scene,workers){
 const exterior=new THREE.Group(),interior=new THREE.Group();scene.add(exterior,interior);interior.visible=false;
 const mats={};function material(c){return mats[c]??=new THREE.MeshStandardMaterial({color:c,roughness:.82})}
 function box(parent,x,y,z,w,h,d,c){const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material(c));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m}
 function cyl(parent,x,y,z,r,h,c,segments=40){const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,segments),material(c));m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;parent.add(m);return m}
 function tree(p,x,z){cyl(p,x,.9,z,.16,1.8,'#967552',8);const crown=new THREE.Mesh(new THREE.IcosahedronGeometry(1.15,1),material('#58977d'));crown.position.set(x,2.35,z);crown.castShadow=true;p.add(crown)}
 box(exterior,0,-.55,0,52,1,42,'#9fb9a4');box(exterior,0,.01,9,37,.1,16,'#d6d8cf');
 // Plaza bundar dan sayap bangunan mengikuti komposisi foto referensi.
 cyl(exterior,0,.15,13,7,.25,'#b7bdb6');cyl(exterior,0,.3,13,5.9,.15,'#e5e3d7');cyl(exterior,0,.41,13,4.7,.15,'#a7bcaa');cyl(exterior,0,.52,13,3.7,.18,'#d6d6c9');cyl(exterior,0,.64,13,1.8,.16,'#79a9b0');
 for(const side of [-1,1]){box(exterior,side*11,4,-2,14,8,7,'#e8e7df');box(exterior,side*17,4,-9,3,8,10,'#e0e1d9');for(let floor=0;floor<3;floor++){box(exterior,side*11,1.6+floor*2.3,1.56,14,.8,.12,'#536e75');box(exterior,side*11,2.25+floor*2.3,1.7,14,.17,.45,'#f5f2e6');for(let i=0;i<10;i++)box(exterior,side*4.4+side*i*1.45,4,1.8,.16,8,.3,'#f6f3e8')}box(exterior,side*11,8.2,-2,14.6,.4,7.6,'#c3c4b9')}
 box(exterior,0,4.5,-1,8,9,9,'#e8dfce');box(exterior,0,2,3.55,3.3,4,.16,'#44636c');for(const x of [-3,3])box(exterior,x,4.2,3.8,.45,8.4,.5,'#fff1dc');
 const roof=new THREE.Mesh(new THREE.ConeGeometry(6.9,3.7,4),material('#a45e51'));roof.rotation.y=Math.PI/4;roof.position.set(0,10.8,-1);roof.castShadow=true;exterior.add(roof);box(exterior,0,12.1,-1,1.7,2,1.7,'#eee7d8');const top=new THREE.Mesh(new THREE.ConeGeometry(1.6,1.5,4),material('#974c43'));top.rotation.y=Math.PI/4;top.position.set(0,13.8,-1);exterior.add(top);
 for(let i=0;i<5;i++)box(exterior,0,.15+i*.15,5.7-i*.28,6-i*.25,.3,1.1,'#d3cebd');for(const x of [-22,22])for(const z of [-14,-6,3,12])tree(exterior,x,z);for(const x of [-12,12])for(const z of [10,17])tree(exterior,x,z);
 box(interior,0,-.24,0,31,.5,17,'#e7dfce');box(interior,0,1.6,-8.3,31,3.2,.3,'#d7e2dc');box(interior,-15.4,1.1,0,.3,2.2,17,'#d7e2dc');box(interior,15.4,1.1,0,.3,2.2,17,'#d7e2dc');
 for(let x=-13;x<15;x+=3.5){box(interior,x,2,-8.08,2.6,1.8,.1,'#99bdc5');box(interior,x,2,-7.99,.07,1.8,.12,'#f4f4eb')}
 const avatars=new Map();for(const w of workers){const [x,,z]=w.position;box(interior,x,.85,z-1.8,3.5,.18,1.5,'#c89e77');for(const dx of [-1.4,1.4])box(interior,x+dx,.4,z-1.8,.12,.8,1.1,'#51636a');box(interior,x,1.4,z-2,1.4,.86,.1,'#344c57');box(interior,x,1.4,z-1.93,1.22,.66,.04,w.color);box(interior,x,1,z-1.65,.12,.3,.12,'#344c57');box(interior,x,.97,z-1.2,1,.05,.3,'#e6ebdf');box(interior,x,.4,z+.8,.9,.15,.9,'#4a6470');box(interior,x,.9,z+1.2,.9,1,.15,'#4a6470');const a=makeWorker(w);avatars.set(w.id,a);interior.add(a.group)}
 box(interior,-8,.5,4,7,1,2,'#759a8c');box(interior,-8,1,4.9,7,1,.35,'#759a8c');box(interior,-8,.45,6.4,4,.16,1.3,'#c89e77');box(interior,6,.85,4.8,6,.2,2.4,'#c89e77');for(const x of [4,6,8])for(const z of [3,6.6])box(interior,x,.5,z,.9,1,.8,'#a7b5ab');for(const x of [-14,14]){cyl(interior,x,.25,-6,.55,.5,'#d1a283');tree(interior,x,-6)}
 for(const x of [-10,0,10]){box(interior,x,4,-6,3,.1,.5,'#f7e6a6')}
 return {avatars,exterior,interior,setInterior(value){exterior.visible=!value;interior.visible=value}}
}
