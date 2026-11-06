const $=s=>document.querySelector(s),esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const link=t=>esc(t).replace(/(https?:\/\/[^\s<]+)/g,'<a href="$1" target="_blank" rel="noopener">$1</a>');
let busy=false;
const num=()=>$("#wa-num").value.replace(/\D/g,"")||"919800000000";
function bubble(html,who){const d=document.createElement("div");d.className="wm "+who;d.innerHTML=html;$("#wa-chat").appendChild(d);d.scrollIntoView({block:"end"});return d}
function lock(){document.querySelectorAll(".wbtn").forEach(b=>b.disabled=true)}
function draw(o){
 if(o.type==="text")bubble(link(o.text.body),"in");
 else if(o.type==="interactive"){const i=o.interactive;bubble(link(i.body.text),"in");
  if(i.type==="button"){const w=document.createElement("div");w.className="wbtns";i.action.buttons.forEach(b=>{const x=document.createElement("button");x.className="wbtn";x.textContent=b.reply.title;x.onclick=()=>{lock();post({type:"interactive",interactive:{type:"button_reply",button_reply:{id:b.reply.id,title:b.reply.title}}},b.reply.title)};w.appendChild(x)});$("#wa-chat").appendChild(w)}
  else{const w=document.createElement("div");w.className="wbtns";const x=document.createElement("button");x.className="wbtn";x.textContent="☰ "+i.action.button;x.onclick=()=>openSheet(i.action.sections[0].rows);w.appendChild(x);$("#wa-chat").appendChild(w)}}
 $("#wa-chat").lastElementChild.scrollIntoView({block:"end"})}
function openSheet(rows){$("#wa-rows").innerHTML="";rows.forEach(r=>{const d=document.createElement("div");d.className="row-i";d.textContent=r.title;d.onclick=()=>{$("#wa-sheet").classList.add("hide");lock();post({type:"interactive",interactive:{type:"list_reply",list_reply:{id:r.id,title:r.title}}},r.title)};$("#wa-rows").appendChild(d)});$("#wa-sheet").classList.remove("hide")}
$("#wa-sheet-x").onclick=()=>$("#wa-sheet").classList.add("hide");
async function post(msg,label){if(busy)return;busy=true;if(label)bubble(esc(label),"out");
 const payload={object:"whatsapp_business_account",entry:[{id:"WABA",changes:[{field:"messages",value:{messaging_product:"whatsapp",messages:[{from:num(),id:"wamid."+Date.now(),timestamp:String(Math.floor(Date.now()/1000)),...msg}]}}]}]};
 const r=await fetch("/api/whatsapp/webhook",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});const d=await r.json();
 $("#wa-json").textContent="→ "+JSON.stringify(msg,null,1)+"\n\n← "+JSON.stringify(d.outbound,null,1).slice(0,2500);
 for(const o of d.outbound||[]){await new Promise(x=>setTimeout(x,350));draw(o)}busy=false}
$("#wa-form").onsubmit=e=>{e.preventDefault();const v=$("#wa-input").value.trim();if(!v)return;$("#wa-input").value="";document.querySelectorAll(".wbtn").forEach(b=>b.disabled=true);post({type:"text",text:{body:v}},v)};
$("#wa-reset").onclick=()=>{$("#wa-chat").innerHTML="";post({type:"text",text:{body:"restart"}})};
post({type:"text",text:{body:"Hi"}});
