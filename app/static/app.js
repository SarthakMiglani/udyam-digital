/* Udyam Digital: customer app. The browser only displays what the server decides; it never computes eligibility or price. */
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const inr=n=>"₹"+Number(n||0).toLocaleString("en-IN");
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

/* ---------------- i18n (UI chrome only; product names, KYC flag text and WhatsApp updates stay in English) ---------------- */
const I={en:{
 steps:["Advisor","Quote","Verify","Order"],peek:"Behind the scenes",restart:"Start over",tag:"Udyam Digital · prototype on synthetic data",
 peekHelp:"Rules, consent and deletion events appear here as you go. The AI only talks; the rules engine decides eligibility and price.",close:"Close",
 heroH:"Get your business connected without a sales call",heroP:"Answer a few quick questions. Get one bundle, one monthly price. Verify online and track your installation.",
 f1:"One clear price",f1d:"Your bundle with a single monthly total. Add or remove items and watch it change.",f2:"Verify online",f2d:"Upload documents once. We check them in seconds and tell you exactly what to fix.",f3:"Track, don't chase",f3d:"See every step to activation. If a date slips, we tell you first.",
 startEn:"Start in English",startHi:"हिंदी में शुरू करें",trackH:"Already placed an order?",trackPh:"Order ID, e.g. ORD-1A2B3C4D",trackBtn:"Track",trackBad:"We could not find that order.",trackNotPlaced:"That order is not placed yet.",
 q:"Question",of:"of",person:"Talk to a person instead",send:"Send",typeHere:"Type your answer…",preparing:"Putting your bundle together…",
 escH:"A person will take it from here",escP:"Nothing you told us is lost. The right team already has it.",escRoute:"Passed to",escCaptured:"What we have so far",escNew:"Start a new conversation",
 yourBundle:"Your bundle",starter:"Starter",recommended:"Recommended",popular:"Most chosen",perMonth:"per month",setupFee:"one-time setup",included:"Included",
 product:"Product",qty:"Qty",total:"Monthly total",firstBill:"First bill",contract:"Minimum contract",months:"months",activation:"Expected activation",
 addons:"Add to your bundle",notOffered:"Not available to you, and why",add:"Add",remove:"Remove",
 broken:"This bundle breaks a catalogue rule.",fixIt:"Fix it to continue.",gstUnlock:"Without an active GSTIN we cannot sell",gstUnlock2:"A partner can help you register for GST, and we then unlock these.",gstAsk:"Ask a partner to call me",gstDone:"Done: a partner will call you.",
 cont:"Continue to verification",surveyNote:"Our surveyor will confirm your site before the price is final.",
 back:"Back",
 consentH:"Before we read your documents",agree:"I agree",decline:"Not now",consentVer:"Consent notice",c1:"Purpose",c2:"What we read",c3:"What we keep",c4:"The AI advisor",c5:"Your control",
 c1d:"Only to verify your business for this order (KYC). Nothing else.",c2d:"GST certificate, Udyam certificate, signatory ID and a recent address proof.",c3d:"The result of the checks and masked ID numbers. Document images are deleted the moment verification finishes.",c4d:"Never sees your document images or full ID numbers.",c5d:"Withdraw any time. Processing stops and the data we hold is deleted, unless the law requires us to keep it.",
 kycH:"Verify your business",kycP:"Your documents are read by the verification service, not by the AI advisor. The images are deleted when the check ends.",
 consentOn:"Consent given",withdraw:"Withdraw consent",withdrawQ:"Withdraw consent? Processing stops, the data we hold is deleted and your order is paused.",withdrawYes:"Withdraw",keep:"Keep consent",
 withdrawn:"Consent withdrawn",withdrawnP:"Processing has stopped and the data we held was deleted. Your order is paused. You can give consent again whenever you like.",giveAgain:"Give consent again",
 tabSpec:"Try a specimen applicant",tabUp:"Upload my documents",specHelp:"Twelve applicants from the case pack. Hints are for judges; the checker does not see them.",
 d_gst:"GST certificate",d_udyam:"Udyam certificate (optional)",d_id:"Signatory ID",d_addr:"Address proof (last 90 days)",drop:"Drop a PNG or JPG here, or click",
 typedL:"Certificate photo blurry? Type your GSTIN",typedPh:"15 characters",typedBad:"A GSTIN has 15 letters and digits.",
 check:"Check documents",checkAgain:"Check again",checking:"Checking…",needDocs:"Choose a specimen or add at least one document first.",
 s1:"Reading the documents",s2:"Checking GSTIN format and checksum",s3:"Looking up the registries",s4:"Cross-checking name, address and ID",
 VERIFIED:"Verified",LIMITED:"Verified for non-GST products",REVIEW:"Needs a quick manual review",REUPLOAD:"Please fix and upload again",
 VERIFIEDd:"Everything checks out. You can place your order.",LIMITEDd:"Your GSTIN is not active, so products that need one were taken out. Everything else can go ahead.",REVIEWd:"You can place the order. A person will confirm the flagged item while we plan the installation.",REUPLOADd:"Nothing was rejected for good. Fix the item below and check again.",
 removedGst:"Removed because GST is not active",newTotal:"New monthly total",masked:"Identifiers are masked. Images deleted after the check",yes:"yes",no:"no",toCheckout:"Continue to checkout",
 coH:"Place your order",pay:"Payment",payP:"UPI autopay mandate. Mock: no money moves in this prototype.",upiL:"UPI ID",upiPh:"name@bank",upiBad:"Enter a UPI ID like name@bank.",place:"Set up autopay and place order",placing:"Placing…",
 orderH:"Order",expected:"Expected activation",noCall:"You do not need to call to find out.",updates:"Updates sent to you",planned:"planned",done:"done",copyLink:"Copy tracking link",copied:"Link copied",trackOther:"Track another order",
 demo:"Demo controls",demoP:"Not part of the customer view. They move the simulated clock so you can see the tracker work.",plus1:"+1 day",plus3:"+3 days",slip:"Slip install by 2 days",office:"Open back office",
 netErr:"Network problem. Please try again.",restartQ:"Start over? Your current answers on this screen will be cleared.",
 trouble:"Talk to a person",sorry:"Something went wrong. Please try again."},
hi:{
 steps:["Salahkaar","Quote","Verify","Order"],peek:"Parde ke peeche",restart:"Dobara shuru",tag:"Udyam Digital · synthetic data par prototype",
 peekHelp:"Niyam, sahmati aur delete ki ghatnayein yahan dikhti hain. AI sirf baat karta hai; eligibility aur daam niyam tay karte hain.",close:"Band karein",
 heroH:"Bina sales call ke apna business connect karein",heroP:"Kuch chhote sawalon ke jawab dein. Ek bundle, ek mahine ka daam. Online verify karein aur installation track karein.",
 f1:"Ek saaf daam",f1d:"Aapka bundle, ek hi mahine ka total. Cheezein jodein ya hatayein, daam badalta dikhega.",f2:"Online verify",f2d:"Documents ek baar upload karein. Hum seconds mein jaanch kar batate hain kya theek karna hai.",f3:"Track karein, peecha nahi",f3d:"Activation tak har kadam dekhein. Tareekh badle to hum pehle batate hain.",
 startEn:"Start in English",startHi:"हिंदी में शुरू करें",trackH:"Order pehle de chuke hain?",trackPh:"Order ID, jaise ORD-1A2B3C4D",trackBtn:"Track karein",trackBad:"Ye order nahi mila.",trackNotPlaced:"Ye order abhi place nahi hua.",
 q:"Sawal",of:"/",person:"Kisi vyakti se baat karein",send:"Bhejein",typeHere:"Apna jawab likhein…",preparing:"Aapka bundle taiyaar ho raha hai…",
 escH:"Ab ek vyakti aapki madad karega",escP:"Aapne jo bataya wo kahin nahi gaya. Sahi team ke paas pehle se hai.",escRoute:"Bheja gaya",escCaptured:"Ab tak ki jaankari",escNew:"Nayi baatcheet shuru karein",
 yourBundle:"Aapka bundle",starter:"Starter",recommended:"Recommended",popular:"Sabse zyada chuna",perMonth:"har mahine",setupFee:"ek baar setup",included:"Shamil",
 product:"Product",qty:"Matra",total:"Mahine ka total",firstBill:"Pehla bill",contract:"Kam se kam contract",months:"mahine",activation:"Anumaanit activation",
 addons:"Bundle mein jodein",notOffered:"Aapko nahi diya ja sakta, aur kyon",add:"Jodein",remove:"Hatayein",
 broken:"Ye bundle catalogue ka ek niyam todta hai.",fixIt:"Aage badhne ke liye theek karein.",gstUnlock:"Active GSTIN ke bina hum ye nahi bech sakte",gstUnlock2:"Partner aapko GST registration mein madad kar sakta hai, phir hum inhein khol denge.",gstAsk:"Partner se call karwayein",gstDone:"Ho gaya: partner aapko call karega.",
 cont:"Verification par aage badhein",surveyNote:"Daam final hone se pehle humara surveyor aapki site confirm karega.",
 back:"Wapas",
 consentH:"Aapke documents padhne se pehle",agree:"Main sahmat hoon",decline:"Abhi nahi",consentVer:"Sahmati notice",c1:"Maqsad",c2:"Hum kya padhte hain",c3:"Hum kya rakhte hain",c4:"AI advisor",c5:"Aapka control",
 c1d:"Sirf is order ke liye aapka business verify karna (KYC). Aur kuch nahi.",c2d:"GST certificate, Udyam certificate, signatory ID aur taza address proof.",c3d:"Jaanch ka nateeja aur masked ID number. Verification khatam hote hi document ki tasveerein delete.",c4d:"Aapke document ki tasveerein ya poora ID number kabhi nahi dekhta.",c5d:"Kabhi bhi wapas lein. Processing ruk jati hai aur humare paas ka data delete ho jata hai, jab tak kanoon rakhne ko na kahe.",
 kycH:"Apna business verify karein",kycP:"Aapke documents verification service padhti hai, AI advisor nahi. Jaanch khatam hote hi tasveerein delete ho jati hain.",
 consentOn:"Sahmati di gayi",withdraw:"Sahmati wapas lein",withdrawQ:"Sahmati wapas lein? Processing ruk jayegi, humare paas ka data delete hoga aur order ruk jayega.",withdrawYes:"Wapas lein",keep:"Sahmati rakhein",
 withdrawn:"Sahmati wapas li gayi",withdrawnP:"Processing ruk gayi hai aur humare paas ka data delete ho gaya. Aapka order ruka hua hai. Aap jab chahein dobara sahmati de sakte hain.",giveAgain:"Dobara sahmati dein",
 tabSpec:"Namuna applicant try karein",tabUp:"Apne documents upload karein",specHelp:"Case pack ke baarah applicants. Hints judges ke liye hain; checker unhein nahi dekhta.",
 d_gst:"GST certificate",d_udyam:"Udyam certificate (optional)",d_id:"Signatory ID",d_addr:"Address proof (pichhle 90 din)",drop:"PNG ya JPG yahan daalein, ya click karein",
 typedL:"Certificate ki photo dhundhli hai? GSTIN type karein",typedPh:"15 akshar",typedBad:"GSTIN mein 15 akshar aur ank hote hain.",
 check:"Documents jaanchein",checkAgain:"Dobara jaanchein",checking:"Jaanch ho rahi hai…",needDocs:"Pehle namuna chunein ya kam se kam ek document daalein.",
 s1:"Documents padhe ja rahe hain",s2:"GSTIN ka format aur checksum dekha ja raha hai",s3:"Registry mein dekha ja raha hai",s4:"Naam, pata aur ID ka milaan",
 VERIFIED:"Verify ho gaya",LIMITED:"Non-GST products ke liye verify",REVIEW:"Chhoti manual review chahiye",REUPLOAD:"Theek karke dobara upload karein",
 VERIFIEDd:"Sab theek hai. Aap order place kar sakte hain.",LIMITEDd:"Aapka GSTIN active nahi hai, isliye jinhein GSTIN chahiye wo products hata diye gaye. Baaki sab aage badh sakta hai.",REVIEWd:"Aap order place kar sakte hain. Installation plan hote waqt ek vyakti flag kiya hua item confirm karega.",REUPLOADd:"Kuch bhi hamesha ke liye reject nahi hua. Neeche wali cheez theek karke dobara jaanchein.",
 removedGst:"GST active na hone se hataya gaya",newTotal:"Naya mahine ka total",masked:"ID masked hain. Jaanch ke baad tasveerein delete",yes:"haan",no:"nahi",toCheckout:"Checkout par aage badhein",
 coH:"Apna order place karein",pay:"Bhugtan",payP:"UPI autopay mandate. Mock: is prototype mein paisa nahi katta.",upiL:"UPI ID",upiPh:"naam@bank",upiBad:"UPI ID is tarah likhein: naam@bank.",place:"Autopay set karein aur order place karein",placing:"Place ho raha hai…",
 orderH:"Order",expected:"Anumaanit activation",noCall:"Jaanne ke liye call karne ki zaroorat nahi.",updates:"Aapko bheje gaye update",planned:"tay",done:"hua",copyLink:"Tracking link copy karein",copied:"Link copy ho gaya",trackOther:"Doosra order track karein",
 demo:"Demo controls",demoP:"Ye customer view ka hissa nahi hain. Ye simulated ghadi aage badhate hain taaki tracker kaam karta dikhe.",plus1:"+1 din",plus3:"+3 din",slip:"Install 2 din aage",office:"Back office kholein",
 netErr:"Network mein dikkat. Dobara koshish karein.",restartQ:"Dobara shuru karein? Is screen ke abhi ke jawab hat jayenge.",
 trouble:"Kisi vyakti se baat karein",sorry:"Kuch gadbad hui. Dobara koshish karein."}};
const S={sid:null,lang:"en",view:"hero",rec:null,tier:"recommended",bundle:{},quote:null,orderId:null,order:null,busy:false,kycTab:"spec",spec:"",files:{},typed:"",consent:false,kycRes:null,poll:null,orderSig:""};
const t=k=>(I[S.lang]&&I[S.lang][k])??I.en[k]??k;
const save=()=>{try{localStorage.setItem("ud",JSON.stringify({orderId:S.orderId,lang:S.lang}))}catch(e){}};
const load=()=>{try{return JSON.parse(localStorage.getItem("ud")||"{}")}catch(e){return{}}};

/* ---------------- plumbing ---------------- */
async function api(path,body,form){
 try{const o=form?{method:"POST",body:form}:body!==undefined?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}:{};
  const r=await fetch(path,o);let data={};try{data=await r.json()}catch(e){}return{ok:r.ok,status:r.status,data}}
 catch(e){toast(t("netErr"),true);return{ok:false,status:0,data:{error:t("netErr")}}}}
function toast(msg,bad){const d=document.createElement("div");d.className="toast"+(bad?" bad":"");d.textContent=msg;$("#toasts").appendChild(d);setTimeout(()=>d.remove(),3500)}
function ask(text,yes,no){return new Promise(res=>{$("#modalText").textContent=text;$("#modalYes").textContent=yes;$("#modalNo").textContent=no;$("#modal").classList.remove("hide");
 const done=v=>{$("#modal").classList.add("hide");$("#modalYes").onclick=$("#modalNo").onclick=null;res(v)};$("#modalYes").onclick=()=>done(true);$("#modalNo").onclick=()=>done(false)})}
const VIEWS=["hero","chat","escalated","quote","consent","kyc","checkout","order"],STEP={hero:0,chat:1,escalated:1,quote:2,consent:3,kyc:3,checkout:4,order:4};
function go(v){S.view=v;VIEWS.forEach(x=>$("#v-"+x).classList.toggle("hide",x!==v));renderStepper();window.scrollTo({top:0});if(v!=="order")stopPoll()}
function renderStepper(){const n=STEP[S.view];$("#stepper").innerHTML=n?t("steps").map((s,i)=>`<li class="${i+1===n?"on":i+1<n?"done":""}"><span class="n">${i+1<n?"✓":i+1}</span><span class="t">${esc(s)}</span></li>`).join(""):""}
function applyLang(){$("#btnPeek").innerHTML=`<span class="full">${esc(t("peek"))}</span><span class="short">ⓘ</span>`;$("#btnRestart").innerHTML=`<span class="full">${esc(t("restart"))}</span><span class="short">↺</span>`;$("#btnPeek").setAttribute("aria-label",t("peek"));$("#btnRestart").setAttribute("aria-label",t("restart"));$("#tagline").textContent=t("tag");$("#peekTitle").textContent=t("peek");$("#peekHelp").textContent=t("peekHelp");$("#peekClose").textContent=t("close");document.documentElement.lang=S.lang==="hi"?"hi":"en";renderStepper()}
const dshort=s=>s?new Date(s+"T00:00:00").toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"}):"";
const backBtn=to=>`<button class="back" data-back="${to}">← ${esc(t("back"))}</button>`;
document.addEventListener("click",e=>{const b=e.target.closest("[data-back]");if(b){const v=b.dataset.back;if(v==="quote")renderQuote();if(v==="kyc")renderKyc();go(v)}});

/* ---------------- hero ---------------- */
function renderHero(){$("#v-hero").innerHTML=`<div class="card hero"><span class="pill red">Accel Business</span><h1>${esc(t("heroH"))}</h1><p class="lead">${esc(t("heroP"))}</p>
 <div class="feat"><div><b>${esc(t("f1"))}</b><span>${esc(t("f1d"))}</span></div><div><b>${esc(t("f2"))}</b><span>${esc(t("f2d"))}</span></div><div><b>${esc(t("f3"))}</b><span>${esc(t("f3d"))}</span></div></div>
 <div class="row"><button class="btn lg" id="startEn">${esc(I.en.startEn)}</button><button class="btn lg alt" id="startHi">${esc(I.hi.startHi)}</button></div></div>
 <div class="card"><h2>${esc(t("trackH"))}</h2><div class="track"><input type="text" id="trackId" placeholder="${esc(t("trackPh"))}" aria-label="${esc(t("trackH"))}"><button class="btn alt" id="trackBtn">${esc(t("trackBtn"))}</button></div><p class="muted small" id="trackMsg"></p></div>`;
 $("#startEn").onclick=()=>begin("en");$("#startHi").onclick=()=>begin("hi");
 const go_=async()=>{const id=$("#trackId").value.trim().toUpperCase();if(!id)return;const r=await openOrder(id);if(r)$("#trackMsg").textContent=r};
 $("#trackBtn").onclick=go_;$("#trackId").addEventListener("keydown",e=>{if(e.key==="Enter")go_()})}

/* ---------------- advisor chat ---------------- */
function chatShell(){$("#v-chat").innerHTML=`<div class="card"><div class="pmeta"><span id="pq"></span><span id="ppct"></span></div><div class="progress"><i id="pbar" style="width:0"></i></div>
 <div class="chatbox" id="chat"></div><div class="chips hide" id="chips"></div>
 <form class="inputbar" id="inputbar" autocomplete="off"><input type="text" id="txt" placeholder="${esc(t("typeHere"))}" aria-label="${esc(t("typeHere"))}"><button class="btn" id="send" type="submit">${esc(t("send"))}</button></form>
 <div class="foot"><button class="linkbtn muted" id="human">${esc(t("person"))}</button></div></div>`;
 $("#inputbar").onsubmit=e=>{e.preventDefault();const v=$("#txt").value.trim();if(v)send(v)};$("#human").onclick=()=>escalate("Owner asked to talk to a person")}
function setProgress(p){if(!p)return;const[i,n]=p;$("#pq").textContent=i>0?`${t("q")} ${Math.min(i,n)} ${t("of")} ${n}`:"";$("#pbar").style.width=Math.round(100*i/n)+"%";$("#ppct").textContent=Math.round(100*i/n)+"%"}
function addMsg(text,who){const row=document.createElement("div");row.className="msgrow "+who;row.innerHTML=(who==="bot"?'<span class="av">A</span>':"")+`<div class="msg ${who}"></div>`;$(".msg",row).textContent=text;$("#chat").appendChild(row);row.scrollIntoView({block:"end",behavior:"smooth"});return row}
async function botSay(msgs){const chips=$("#chips");chips.classList.add("hide");
 for(const m of msgs){const row=document.createElement("div");row.className="msgrow bot";row.innerHTML='<span class="av">A</span><div class="msg bot typing"><i></i><i></i><i></i></div>';$("#chat").appendChild(row);row.scrollIntoView({block:"end",behavior:"smooth"});
  await sleep(Math.min(250+m.text.length*4,900));const b=$(".msg",row);b.classList.remove("typing");b.textContent=m.text}
 const last=msgs[msgs.length-1];chips.innerHTML="";
 if(last&&last.chips&&last.chips.length){last.chips.forEach(c=>{const b=document.createElement("button");b.type="button";b.className="chip"+(c.value==="__done__"?" done":"");b.textContent=c.label;b.onclick=()=>send(c.value,c.label);chips.appendChild(b)});chips.classList.remove("hide");chips.scrollIntoView({block:"end",behavior:"smooth"})}
 const hideInput=!!(last&&last.input==="none");$("#inputbar").classList.toggle("hide",hideInput)}
async function newSession(){const{ok,data}=await api("/api/session",{});if(!ok)return false;S.sid=data.sid;S.rec=null;S.orderId=null;S.order=null;S.quote=null;return data}
function setBusy(v){S.busy=v;const t_=$("#txt"),s_=$("#send");if(t_)t_.disabled=v;if(s_)s_.disabled=v;$$("#chips .chip").forEach(c=>c.disabled=v)}
async function begin(lang){if(S.busy)return;S.busy=true;const first=await newSession();if(!first){S.busy=false;return}
 S.lang=lang;applyLang();chatShell();go("chat");S.busy=false;await send(lang==="hi"?"Hindi":"English",null,true)}
async function send(value,label,silent){if(S.busy)return;setBusy(true);
 if(!silent&&value!=="__done__")addMsg(label||value,"me");$("#txt").value="";$("#chips").classList.add("hide");
 const{ok,data}=await api("/api/chat",{sid:S.sid,text:value});
 if(!ok){toast(data.error||t("sorry"),true);$("#chips").classList.remove("hide");setBusy(false);return}
 if(data.lang&&data.lang!==S.lang){S.lang=data.lang;applyLang()}
 setProgress(data.progress);await botSay(data.messages||[]);
 if(data.escalated){setBusy(false);showEscalated(data.lead)}
 else if(data.recommendation){S.rec=data.recommendation;$("#inputbar").classList.add("hide");$("#chips").classList.add("hide");addMsg(t("preparing"),"bot");setProgress([8,8]);await sleep(700);setBusy(false);startQuote(data.lead)}
 else{setBusy(false);if(!$("#inputbar").classList.contains("hide"))$("#txt").focus({preventScroll:true})}}
async function escalate(reason){const{ok,data}=await api("/api/escalate",{sid:S.sid,reason});if(ok)showEscalated(data.lead)}
function showEscalated(lead){const c=lead.captured||{};const rows=[["Business",c.business_type],["City",c.city],["Staff",c.employees],["Locations",c.sites],["Language",c.lang==="hi"?"Hindi":"English"]].filter(r=>r[1]);
 $("#v-escalated").innerHTML=`<div class="card"><span class="pill ok">✓ ${esc(lead.id)}</span><h2 style="margin-top:8px">${esc(t("escH"))}</h2><p>${esc(t("escP"))}</p>
 <div class="note"><b>${esc(t("escRoute"))}:</b> ${esc(lead.route)}</div>${rows.length?`<table class="facts"><tr><td colspan=2 style="text-transform:none;color:var(--ink);font-weight:600;font-family:inherit">${esc(t("escCaptured"))}</td></tr>${rows.map(r=>`<tr><td>${esc(r[0])}</td><td style="font-family:inherit">${esc(r[1])}</td></tr>`).join("")}</table>`:""}
 <div class="row" style="margin-top:14px"><button class="btn alt" id="newConv">${esc(t("escNew"))}</button></div></div>`;
 $("#newConv").onclick=()=>restart(true);go("escalated")}

/* ---------------- quote ---------------- */
const curBundle=()=>Object.fromEntries(Object.entries(S.bundle).filter(([,q])=>q>0));
async function requote(){const{ok,data}=await api("/api/quote",{sid:S.sid,order_id:S.orderId,bundle:curBundle()});if(!ok){toast(data.error||t("sorry"),true);return}S.quote=data;renderQuote()}
function startQuote(lead){S.tier="recommended";pickTier("recommended");S.needsSurvey=!!lead||!!S.rec.needs_survey;renderQuote();go("quote")}
function pickTier(k){S.tier=k;const x=S.rec.tiers.find(y=>y.key===k);S.bundle={...x.bundle};S.quote={...x.quote,addons:S.rec.addons}}
const CATORDER=["Connectivity","Mobility","Productivity","Security","Voice","Business apps","IoT"];
function renderQuote(){const r=S.rec,q=S.quote,p=q.price;const names=l=>l.map(x=>esc(x.name));
 const tiers=r.tiers.map(x=>`<button class="tier ${x.key===S.tier?"sel":""}" data-k="${x.key}" aria-pressed="${x.key===S.tier}">${x.key==="recommended"?`<span class="badge">${esc(t("popular"))}</span>`:""}<div class="nm">${esc(t(x.key))}</div>
   <div class="p">${inr(x.quote.price.monthly)} <small>${esc(t("perMonth"))}</small></div>${x.quote.price.setup?`<div class="muted small">+ ${inr(x.quote.price.setup)} ${esc(t("setupFee"))}</div>`:""}
   <ul class="inc">${x.quote.price.lines.slice(0,5).map(l=>`<li>${esc(l.name)}${l.qty>1?" × "+l.qty:""}</li>`).join("")}</ul></button>`).join("");
 const rows=p.lines.map(l=>`<tr><td><div class="nm">${esc(l.name)}</div><div class="u">${inr(l.unit_price)} ${esc(l.unit)}${l.setup?`, ${inr(l.setup)} ${esc(t("setupFee"))}`:""}</div></td>
   <td><span class="qty"><button data-pid="${l.pid}" data-d="-1" aria-label="-">−</button><span>${l.qty}</span><button data-pid="${l.pid}" data-d="1" aria-label="+">+</button></span></td>
   <td class="r"><b>${inr(l.monthly)}</b></td><td class="r"><button class="x" data-rm="${l.pid}" title="${esc(t("remove"))}" aria-label="${esc(t("remove"))} ${esc(l.name)}">×</button></td></tr>`).join("");
 const allowed=(q.addons||[]).filter(a=>a.allowed&&!/^(Biz Fibre|Biz 5G|Business Postpaid|Internet Leased)/.test(a.name));
 const groups={};allowed.forEach(a=>(groups[a.category||"More"]??=[]).push(a));
 const gkeys=Object.keys(groups).sort((a,b)=>(CATORDER.indexOf(a)<0?99:CATORDER.indexOf(a))-(CATORDER.indexOf(b)<0?99:CATORDER.indexOf(b)));
 const addHtml=gkeys.map(g=>`<details class="grp"><summary>${esc(g)} <span class="muted small">${groups[g].length}</span></summary>${groups[g].map(a=>`<div class="addrow"><div><div class="nm">${esc(a.name)}</div><div class="u muted small">${inr(a.unit_price)} ${esc(a.unit)}${a.setup?`, ${inr(a.setup)} ${esc(t("setupFee"))}`:""}</div></div><button class="btn alt sm" data-add="${a.pid}" data-q="${a.default_qty}">+ ${esc(t("add"))}</button></div>`).join("")}</details>`).join("");
 const seen=new Set(),no=[];[...(r.removed||[]).map(x=>({pid:x.product,name:x.name,why:x.reasons})),...(q.addons||[]).filter(a=>!a.allowed).map(a=>({pid:a.pid,name:a.name,why:a.why_not}))].forEach(x=>{if(!seen.has(x.pid)){seen.add(x.pid);no.push(x)}});
 const viol=q.violations.length?`<div class="errbox"><b>${esc(t("broken"))}</b><ul class="plain">${q.violations.map(v=>`<li>${esc(v.name)}: ${esc(v.detail)}</li>`).join("")}</ul>${esc(t("fixIt"))}</div>`:"";
 const gst=r.gst_unlock&&r.gst_unlock.length&&!S.gstAsked?`<div class="note">${esc(t("gstUnlock"))} ${esc(r.gst_unlock.slice(0,4).join(", "))}${r.gst_unlock.length>4?" …":""}. ${esc(t("gstUnlock2"))} <button class="linkbtn" id="gsthelp">${esc(t("gstAsk"))}</button></div>`:S.gstAsked?`<div class="note"><b>${esc(t("gstDone"))}</b></div>`:"";
 $("#v-quote").innerHTML=`<div class="card"><span class="pill red">${esc(r.segment_label)}</span><h2 style="margin-top:8px">${esc(t("yourBundle"))}</h2><p>${esc(r.explanation.headline)}</p><ul class="plain">${r.explanation.lines.map(l=>`<li>${esc(l)}</li>`).join("")}</ul>
  ${r.notes.map(n=>`<div class="note">${esc(n)}</div>`).join("")}${S.needsSurvey?`<div class="warnbox">${esc(t("surveyNote"))}</div>`:""}</div>
 <div class="tiers">${tiers}</div>
 <div class="card"><table class="lines">${rows}</table>
  <div style="margin-top:8px"><div class="sumrow"><span>${esc(t("total"))}</span><b>${inr(p.monthly)}</b></div>${p.setup?`<div class="sumrow"><span>${esc(t("setupFee"))}</span><span>${inr(p.setup)}</span></div>`:""}
  <div class="sumrow"><span>${esc(t("contract"))}</span><span>${p.contract_months} ${esc(t("months"))}</span></div><div class="sumrow"><span>${esc(t("activation"))}</span><span>${esc(dshort(q.expected_install_date))}</span></div>
  <div class="sumrow big"><span>${esc(t("firstBill"))}</span><span>${inr(q.first_bill)}</span></div></div>${viol}</div>
 ${addHtml?`<div class="card"><h2>${esc(t("addons"))}</h2>${addHtml}</div>`:""}
 ${no.length?`<div class="card"><details class="grp" style="border:0"><summary>${esc(t("notOffered"))} <span class="muted small">${no.length}</span></summary><ul class="plain">${no.map(x=>`<li><b>${esc(x.name)}</b>: ${esc((x.why||[]).map(w=>w.detail).join("; "))}</li>`).join("")}</ul></details></div>`:""}
 ${gst}
 <p class="center show-sm"><button class="linkbtn muted" id="human3">${esc(t("person"))}</button></p>
 <div class="sticky"><div class="tot">${inr(p.monthly)}<small>${esc(t("perMonth"))}${p.setup?` + ${inr(p.setup)} ${esc(t("setupFee"))}`:""}</small></div><div class="row"><button class="btn alt hide-sm" id="human2">${esc(t("person"))}</button><button class="btn" id="go" ${q.valid?"":"disabled"}>${esc(t("cont"))}</button></div></div>`;
 $$(".tier").forEach(el=>el.onclick=()=>{pickTier(el.dataset.k);renderQuote()});
 $$("[data-d]").forEach(b=>b.onclick=()=>{const k=b.dataset.pid;S.bundle[k]=Math.max(0,(S.bundle[k]||0)+ +b.dataset.d);guardEmpty();requote()});
 $$("[data-rm]").forEach(b=>b.onclick=()=>{S.bundle[b.dataset.rm]=0;guardEmpty();requote()});
 $$("[data-add]").forEach(b=>b.onclick=()=>{S.bundle[b.dataset.add]=+b.dataset.q||1;requote()});
 $("#go").onclick=createOrder;$("#human2").onclick=$("#human3").onclick=()=>escalate("Owner asked to talk to a person from the quote");
 const gh=$("#gsthelp");if(gh)gh.onclick=async()=>{await api("/api/escalate",{sid:S.sid,reason:"Owner wants help with GST registration to unlock GST-only products"});S.gstAsked=true;renderQuote()}}
function guardEmpty(){if(!Object.keys(curBundle()).length){toast(S.lang==="hi"?"Bundle khaali nahi ho sakta":"A bundle cannot be empty",true);S.bundle={...S.rec.tiers[0].bundle}}}
async function createOrder(){const{ok,data}=await api("/api/order",{sid:S.sid,bundle:curBundle()});
 if(!ok){S.quote={...S.quote,violations:data.violations||[],valid:false};renderQuote();toast(data.error||t("sorry"),true);return}
 S.orderId=data.order_id;S.consent=!!data.consent;save();startPoll(true);if(S.consent){renderKyc();go("kyc")}else{renderConsent();go("consent")}}

/* ---------------- consent ---------------- */
async function renderConsent(){const{data}=await api("/api/consent?lang="+S.lang);const ic=["🎯","📄","🗄️","🤖","↩️"],hd=["c1","c2","c3","c4","c5"];
 $("#v-consent").innerHTML=`${backBtn("quote")}<div class="card"><h2>${esc(data.title)}</h2><div class="cgrid">${["c1d","c2d","c3d","c4d","c5d"].map((k,i)=>`<div class="citem"><span class="ci">${ic[i]}</span><div><b>${esc(t(hd[i]))}</b><span>${esc(t(k))}</span></div></div>`).join("")}</div>
 <p class="muted small">${esc(t("consentVer"))} ${esc(data.version)}</p><div class="row"><button class="btn" id="agree">${esc(data.agree)}</button><button class="btn alt" id="decline">${esc(data.decline)}</button></div></div>`;
 $("#agree").onclick=async()=>{const r=await api(`/api/order/${S.orderId}/consent`,{lang:S.lang});if(r.ok){S.consent=true;S.kycRes=null;renderKyc();go("kyc")}};$("#decline").onclick=()=>{renderQuote();go("quote")}}

/* ---------------- KYC ---------------- */
const SPEC={K01:"Cancelled GSTIN",K02:"Skewed scan",K03:"Look-alike characters",K04:"Blurred certificate",K05:"No Udyam certificate",K06:"GSTIN typo",K07:"Name mismatch",K08:"Look-alike characters",K09:"Clean documents",K10:"GSTIN typo",K11:"Old address proof",K12:"Clean documents"};
const DOCS=[["gst_certificate","d_gst"],["udyam_certificate","d_udyam"],["signatory_id","d_id"],["address_proof","d_addr"]];
function renderKyc(){const keep=S.kycRes;
 $("#v-kyc").innerHTML=`${backBtn("quote")}<div class="card"><div class="row between"><h2>${esc(t("kycH"))}</h2>${S.consent?`<span class="pill ok">✓ ${esc(t("consentOn"))}</span>`:""}</div><p class="muted">${esc(t("kycP"))}</p>
 <div class="tabs"><button data-tab="spec" class="${S.kycTab==="spec"?"on":""}">${esc(t("tabSpec"))}</button><button data-tab="up" class="${S.kycTab==="up"?"on":""}">${esc(t("tabUp"))}</button></div>
 <div id="tabSpec" class="${S.kycTab==="spec"?"":"hide"}"><p class="muted small">${esc(t("specHelp"))}</p><div class="spec">${Object.entries(SPEC).map(([k,v])=>`<button data-spec="${k}" class="${S.spec===k?"on":""}"><b>${k}</b><span>${esc(v)}</span></button>`).join("")}</div></div>
 <div id="tabUp" class="${S.kycTab==="up"?"":"hide"}"><div class="drops">${DOCS.map(([k,l])=>`<label class="drop ${S.files[k]?"has":""}" data-drop="${k}"><input type="file" accept="image/png,image/jpeg" data-doc="${k}"><b>${esc(t(l))}</b>${S.files[k]?`<img alt="" src="${S.files[k].url}"><small>${esc(S.files[k].file.name)}</small><button type="button" class="rm" data-rmf="${k}" aria-label="remove">×</button>`:`<small>${esc(t("drop"))}</small>`}</label>`).join("")}</div></div>
 <label class="lab" for="typed">${esc(t("typedL"))}</label><input type="text" id="typed" maxlength="15" placeholder="${esc(t("typedPh"))}" value="${esc(S.typed)}" autocapitalize="characters" style="text-transform:uppercase"><p class="errbox hide" id="typedErr" style="margin-top:6px">${esc(t("typedBad"))}</p>
 <div class="row" style="margin-top:16px"><button class="btn" id="runkyc">${esc(keep?t("checkAgain"):t("check"))}</button><button class="btn alt" id="withdraw">${esc(t("withdraw"))}</button></div></div><div id="kycres"></div>`;
 $$("[data-tab]").forEach(b=>b.onclick=()=>{S.kycTab=b.dataset.tab;renderKyc()});
 $$("[data-spec]").forEach(b=>b.onclick=()=>{S.spec=S.spec===b.dataset.spec?"":b.dataset.spec;$$("[data-spec]").forEach(x=>x.classList.toggle("on",x.dataset.spec===S.spec))});
 $$(".drop").forEach(d=>{const inp=$("input",d);inp.onchange=()=>setFile(d.dataset.drop,inp.files[0]);["dragenter","dragover"].forEach(ev=>d.addEventListener(ev,e=>{e.preventDefault();d.classList.add("over")}));["dragleave","drop"].forEach(ev=>d.addEventListener(ev,e=>{e.preventDefault();d.classList.remove("over")}));d.addEventListener("drop",e=>{if(e.dataTransfer.files[0])setFile(d.dataset.drop,e.dataTransfer.files[0])})});
 $$("[data-rmf]").forEach(b=>b.onclick=e=>{e.preventDefault();e.stopPropagation();delete S.files[b.dataset.rmf];renderKyc()});
 $("#typed").oninput=e=>{S.typed=e.target.value.toUpperCase();$("#typedErr").classList.add("hide")};
 $("#runkyc").onclick=runKyc;$("#withdraw").onclick=withdraw;if(keep)renderKycResult(keep)}
function setFile(k,f){if(!f)return;if(!/^image\/(png|jpeg)$/.test(f.type)){toast("PNG or JPG only",true);return}if(f.size>8e6){toast("Max 8 MB",true);return}S.files[k]={file:f,url:URL.createObjectURL(f)};S.kycTab="up";renderKyc()}
async function withdraw(){if(!await ask(t("withdrawQ"),t("withdrawYes"),t("keep")))return;const{ok}=await api(`/api/order/${S.orderId}/consent/withdraw`,{});if(!ok)return;S.consent=false;S.kycRes=null;S.files={};S.spec="";S.typed="";
 $("#v-kyc").innerHTML=`<div class="card"><span class="pill warn">${esc(t("withdrawn"))}</span><p>${esc(t("withdrawnP"))}</p><div class="row"><button class="btn" id="regive">${esc(t("giveAgain"))}</button><button class="btn alt" id="toQuote">${esc(t("back"))}</button></div></div>`;
 $("#regive").onclick=()=>{renderConsent();go("consent")};$("#toQuote").onclick=()=>{renderQuote();go("quote")}}
async function runKyc(){const useFiles=S.kycTab==="up"&&Object.keys(S.files).length,spec=S.kycTab==="spec"?S.spec:"";
 if(!useFiles&&!spec){toast(t("needDocs"),true);return}
 const typed=S.typed.trim();if(typed&&!/^[0-9A-Z]{15}$/.test(typed)){$("#typedErr").classList.remove("hide");return}
 const fd=new FormData();if(spec)fd.append("specimen",spec);if(useFiles)Object.entries(S.files).forEach(([k,v])=>fd.append(k,v.file));if(typed)fd.append("typed_gstin",typed);
 const btn=$("#runkyc");btn.disabled=true;btn.textContent=t("checking");
 const steps=["s1","s2","s3","s4"];$("#kycres").innerHTML=`<div class="card"><ul class="checks" id="checks">${steps.map(s=>`<li data-s="${s}"><span class="d"></span>${esc(t(s))}</li>`).join("")}</ul></div>`;
 $("#kycres").scrollIntoView({block:"center",behavior:"smooth"});
 let i=0,stop=false;const tick=async()=>{while(!stop&&i<steps.length){const li=$$("#checks li")[i];if(!li)return;li.className="run";await sleep(1100);if(stop)return;li.className="ok";li.querySelector(".d").textContent="✓";i++}};tick();
 const{ok,status,data}=await api(`/api/order/${S.orderId}/kyc`,undefined,fd);stop=true;btn.disabled=false;btn.textContent=t("checkAgain");
 if(!ok){$("#kycres").innerHTML=`<div class="errbox">${esc(data.reason||data.error||t("sorry"))}</div>`;if(status===403)S.consent=false;return}
 S.kycRes=data;S.quote={...S.quote,...data.quote,addons:S.quote.addons};startPoll(true);renderKycResult(data);$("#kycres").scrollIntoView({block:"start",behavior:"smooth"})}
function renderKycResult(d){const icon={VERIFIED:"✅",LIMITED:"⚠️",REVIEW:"🕒",REUPLOAD:"📷"}[d.decision]||"ℹ️",cls={VERIFIED:"ok",LIMITED:"warn",REVIEW:"warn",REUPLOAD:"bad"}[d.decision]||"blue";
 const pass=["VERIFIED","LIMITED","REVIEW"].includes(d.decision),facts=Object.entries(d.facts||{}).filter(([k,v])=>v!==null&&v!=="").map(([k,v])=>`<tr><td>${esc(k.replace(/_/g," "))}</td><td>${esc(v)}</td></tr>`).join("");
 $("#kycres").innerHTML=`<div class="card v-${d.decision}"><div class="verdict"><span class="vicon">${icon}</span><div><span class="pill ${cls}">${esc(t(d.decision))}</span><p style="margin:6px 0 0">${esc(t(d.decision+"d"))}</p></div></div>
 ${(d.flags||[]).map(f=>`<div class="flag ${f.level}">${esc(f.text)}</div>`).join("")}
 ${d.removed_products&&d.removed_products.length?`<div class="warnbox"><b>${esc(t("removedGst"))}:</b> ${esc(d.removed_products.join(", "))}.<br>${esc(t("newTotal"))}: <b>${inr(d.quote.price.monthly)}</b></div>`:""}
 ${facts?`<table class="facts">${facts}</table>`:""}<p class="muted small" style="margin-top:10px">${esc(t("masked"))}: <b>${d.images_deleted?t("yes"):t("no")}</b>.</p>
 ${pass?`<div class="row" style="margin-top:8px"><button class="btn lg" id="tocheckout">${esc(t("toCheckout"))}</button></div>`:""}</div>`;
 const b=$("#tocheckout");if(b)b.onclick=()=>{renderCheckout();go("checkout")}}

/* ---------------- checkout ---------------- */
function renderCheckout(){const p=S.quote.price;
 $("#v-checkout").innerHTML=`${backBtn("kyc")}<div class="card"><h2>${esc(t("coH"))}</h2><table class="summ" style="width:100%;border-collapse:collapse;margin-top:8px">${p.lines.map(l=>`<tr><td>${esc(l.name)}${l.qty>1?" × "+l.qty:""}</td><td class="r">${inr(l.monthly)}</td></tr>`).join("")}</table>
 <div class="sumrow big"><span>${esc(t("total"))}</span><span>${inr(p.monthly)}</span></div>${p.setup?`<div class="sumrow"><span>${esc(t("setupFee"))}</span><span>${inr(p.setup)}</span></div>`:""}
 <div class="sumrow"><span>${esc(t("contract"))}</span><span>${p.contract_months} ${esc(t("months"))}</span></div></div>
 <div class="card"><h2>${esc(t("pay"))}</h2><p class="muted">${esc(t("payP"))}</p><label class="lab" for="upi">${esc(t("upiL"))}</label><div class="upi"><input type="text" id="upi" placeholder="${esc(t("upiPh"))}" value="demo@upi" autocomplete="off" autocapitalize="off"></div><p class="errbox hide" id="upiErr" style="margin-top:8px">${esc(t("upiBad"))}</p>
 <div class="row" style="margin-top:14px"><button class="btn lg" id="place">${esc(t("place"))}</button></div></div>`;
 $("#place").onclick=async()=>{const v=$("#upi").value.trim();if(!/^[\w.\-]{2,}@[A-Za-z]{2,}$/.test(v)){$("#upiErr").classList.remove("hide");return}$("#upiErr").classList.add("hide");
  const b=$("#place");b.disabled=true;b.textContent=t("placing");const{ok,data}=await api(`/api/order/${S.orderId}/checkout`,{upi:v});b.disabled=false;b.textContent=t("place");
  if(!ok){$("#upiErr").textContent=data.error||t("sorry");$("#upiErr").classList.remove("hide");return}save();renderOrder(data)}}

/* ---------------- tracker ---------------- */
async function openOrder(id){const{ok,status,data}=await api(`/api/order/${encodeURIComponent(id)}`);if(!ok)return status===404?t("trackBad"):t("sorry");
 if(!data.milestones||!data.milestones.length)return t("trackNotPlaced");S.orderId=id;S.lang=(data.profile&&data.profile.lang)||S.lang;S.quote=data.quote;save();applyLang();renderOrder(data);return""}
async function renderOrder(o){if(!o){const r=await api(`/api/order/${S.orderId}`);if(!r.ok)return;o=r.data}S.order=o;
 const ms=o.milestones||[],doneN=ms.filter(m=>m.actual).length,pct=Math.round(100*doneN/Math.max(1,ms.length)),slipped=ms.some(m=>m.slipped&&!m.actual);
 $("#v-order").innerHTML=`<div class="card"><div class="row between"><h2>${esc(t("orderH"))} ${esc(o.id)}</h2><span class="pill ${doneN===ms.length?"ok":"blue"}">${esc(o.status)}</span></div>
  <p class="muted" style="margin:10px 0 0">${esc(t("expected"))}</p><div class="big-date">${esc(dshort(o.expected_activation))}${slipped?' <span class="pill warn" style="vertical-align:middle">updated</span>':""}</div><p class="muted">${esc(t("noCall"))}</p>
  <div class="bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:${pct}%"></i></div>
  <ul class="timeline">${ms.map(m=>`<li class="${m.actual?"done":""} ${m.slipped&&!m.actual?"slip":""}"><span>${esc(m.label)}</span><span class="d">${esc(m.actual?t("done"):t("planned"))} ${esc(dshort(m.actual||m.planned))}</span></li>`).join("")}</ul>
  <div class="row" style="margin-top:12px"><button class="btn alt sm" id="copyLink">${esc(t("copyLink"))}</button><button class="btn alt sm" id="trackOther">${esc(t("trackOther"))}</button></div></div>
 <div class="card"><h2>${esc(t("updates"))}</h2>${(o.messages||[]).length?o.messages.map(m=>`<div class="wa"><small>${esc(m.channel)} (simulated) · ${esc((m.ts||"").replace("T"," "))}</small>${esc(m.text)}</div>`).join(""):""}</div>
 <div class="card"><details class="grp" style="border:0"><summary>${esc(t("demo"))}</summary><p class="muted">${esc(t("demoP"))}</p><div class="row"><button class="btn alt sm" data-adv="1">${esc(t("plus1"))}</button><button class="btn alt sm" data-adv="3">${esc(t("plus3"))}</button><button class="btn alt sm" id="slip">${esc(t("slip"))}</button><a class="btn alt sm" style="text-decoration:none" href="/office" target="_blank" rel="noopener">${esc(t("office"))}</a></div></details></div>`;
 $$("[data-adv]").forEach(b=>b.onclick=async()=>{const r=await api(`/api/order/${S.orderId}/demo/advance`,{days:+b.dataset.adv});if(r.ok)renderOrder(r.data)});
 $("#slip").onclick=async()=>{const r=await api(`/api/order/${S.orderId}/demo/slip`,{days:2,reason:"engineer availability"});if(r.ok)renderOrder(r.data)};
 $("#copyLink").onclick=async()=>{const u=location.origin+"/?order="+S.orderId;try{await navigator.clipboard.writeText(u);toast(t("copied"))}catch(e){toast(u)}};
 $("#trackOther").onclick=()=>restart(true);
 S.orderSig=JSON.stringify([ms.map(m=>[m.actual,m.planned]),(o.messages||[]).length]);go("order");startOrderPoll()}
function startOrderPoll(){stopPoll();S.poll=setInterval(async()=>{if(S.view!=="order"||!S.orderId)return;const r=await fetch(`/api/order/${S.orderId}`).then(x=>x.json()).catch(()=>null);if(!r||!r.milestones)return;
 const sig=JSON.stringify([r.milestones.map(m=>[m.actual,m.planned]),(r.messages||[]).length]);if(sig!==S.orderSig&&!$("details[open]",$("#v-order")))renderOrder(r)},5000)}
function stopPoll(){if(S.poll){clearInterval(S.poll);S.poll=null}}

/* ---------------- behind the scenes ---------------- */
const EVN={order_created:"Order created",order_updated:"Order updated",consent_given:"Consent recorded",consent_withdrawn:"Consent withdrawn",data_deleted:"Data deleted",kyc_started:"Verification started",kyc_blocked:"Blocked: no consent",kyc_result:"Verification result",images_deleted:"Document images deleted",checkout:"Order placed",milestone:"Milestone reached",date_slipped:"Date moved",sent_to_back_office:"Sent to back office"};
let evTimer=null;
function startPoll(now){if(evTimer)clearInterval(evTimer);const f=async()=>{if(!S.orderId)return;const r=await fetch(`/api/audit?order=${S.orderId}`).then(x=>x.json()).catch(()=>null);if(!r)return;
 $("#events").innerHTML=r.events.length?r.events.map(e=>`<div class="ev"><span class="who ${esc(e.actor)}">${esc(e.actor)}</span><b>${esc(EVN[e.action]||e.action.replace(/_/g," "))}</b><span class="d">${esc(e.detail)}</span></div>`).join(""):""};if(now)f();evTimer=setInterval(f,3000)}
$("#btnPeek").onclick=()=>{const o=$("#aside").classList.toggle("open");$("#btnPeek").setAttribute("aria-expanded",o)};$("#peekClose").onclick=()=>{$("#aside").classList.remove("open")};
document.addEventListener("keydown",e=>{if(e.key==="Escape"){$("#aside").classList.remove("open");if(!$("#modal").classList.contains("hide"))$("#modalNo").click()}});

/* ---------------- restart & boot ---------------- */
async function restart(skipAsk){if(!skipAsk&&S.view!=="hero"&&!await ask(t("restartQ"),t("restart"),t("back")))return;
 stopPoll();if(evTimer){clearInterval(evTimer);evTimer=null}Object.assign(S,{sid:null,view:"hero",rec:null,tier:"recommended",bundle:{},quote:null,orderId:null,order:null,busy:false,kycTab:"spec",spec:"",files:{},typed:"",consent:false,kycRes:null,gstAsked:false,needsSurvey:false});
 $("#events").innerHTML="";try{localStorage.removeItem("ud")}catch(e){}history.replaceState(null,"","/");applyLang();renderHero();go("hero")}
$("#btnRestart").onclick=()=>restart(false);
(async function boot(){const saved=load(),params=new URLSearchParams(location.search);S.lang=saved.lang||"en";applyLang();renderHero();go("hero");
 const sess=params.get("s");
 if(sess){const r=await api(`/api/session/${encodeURIComponent(sess)}/recommendation`);
  if(r.ok){S.sid=sess;S.rec=r.data.recommendation;S.lang=r.data.lang||S.lang;applyLang();startQuote(null);history.replaceState(null,"","/");return}
  toast(r.status===404?t("trackBad"):t("sorry"),true)}
 const q=params.get("order")||saved.orderId;
 if(q){const msg=await openOrder(q.toUpperCase());if(msg){$("#trackMsg").textContent=params.get("order")?msg:"";if(!params.get("order")){try{localStorage.removeItem("ud")}catch(e){}}}else startPoll(true)}})();
