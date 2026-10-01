const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const KEY="careerpilot";
let S={};try{S=JSON.parse(localStorage.getItem(KEY)||"{}")}catch{}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch{}};
const show=(n,step)=>{Object.entries({1:"s1",2:"s2",3:"s3",L:"sl"}).forEach(([k,id])=>$(id).classList.toggle("hidden",String(k)!==String(n)));
  const st=n==="L"?step:n;[...$("steps").children].forEach((s,i)=>s.classList.toggle("on",i+1===st));window.scrollTo(0,0)};
async function post(url,body,isForm){
  const r=await fetch(url,{method:"POST",...(isForm?{body}:{headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})});
  if(!r.ok){let m="Something went wrong.";try{m=(await r.json()).error||m}catch{}throw new Error(m)}
  return r;
}
const busy=(b,on,t)=>{b.dataset.l=b.dataset.l||b.textContent;b.disabled=on;b.textContent=on?t:b.dataset.l};
const toast=m=>{const t=$("toast");t.textContent=m;t.classList.add("on");clearTimeout(toast.t);toast.t=setTimeout(()=>t.classList.remove("on"),5000)};
let req=0,tick;const loading=(step,title,msgs)=>{$("lt").textContent=title;let i=0;const m=$("lm");m.textContent=msgs[0];
  clearInterval(tick);tick=setInterval(()=>{i=(i+1)%msgs.length;m.textContent=msgs[i]},2200);show("L",step)};
const skLines=()=>`<div class="fb"><div class="sk" style="height:52px;width:110px"></div><div class="sk" style="height:14px;width:80%;margin-top:24px"></div><div class="sk" style="height:14px;width:65%;margin-top:12px"></div><div class="sk" style="height:90px;margin-top:24px"></div></div>`;
const words=s=>new Set(String(s||"").toLowerCase().match(/[a-z0-9+#.]{3,}/g)||[]);
const hl=(t,orig)=>{const o=words(orig);return String(t??"").split(/([A-Za-z0-9+#.]{3,})/).map((p,i)=>i%2?(o.has(p.toLowerCase())?esc(p):`<mark>${esc(p)}</mark>`):esc(p)).join("")};

/* experience question cards (used in step 2 and in the Match tab) */
const CH=["Yes, directly","Something similar","No"];
const qCards=items=>items.map(q=>`<div class="q" data-s="${esc(q.skill)}" data-q="${esc(q.question)}">
  <div class="tag">${esc(q.skill)}${q.importance?` · ${esc(q.importance)}`:""}</div><p>${esc(q.question)}</p>
  <div class="opts">${CH.map(c=>`<button data-c="${c}">${c}</button>`).join("")}</div>
  <input placeholder="Where or how? One sentence is enough"></div>`).join("");
function bindQ(root){root.querySelectorAll(".q .opts button").forEach(b=>b.onclick=()=>{
  b.parentNode.querySelectorAll("button").forEach(x=>x.classList.remove("on"));b.classList.add("on")})}
const readQ=root=>[...root.querySelectorAll(".q")].map(el=>{
  const c=el.querySelector(".on")?.dataset.c,d=el.querySelector("input").value.trim();
  return {skill:el.dataset.s,question:el.dataset.q,answer:c?`${c}${d?". "+d:""}`:d}}).filter(a=>a.answer);
const EXTRA=[["Other experience","Jobs, internships, volunteering or college roles not on your resume"],
 ["Tools","Software or tools you’ve used, even at a basic level"],
 ["Proud of","Something you built or finished that you’re proud of"],
 ["Courses","Courses or certificates you’ve completed"]];

/* home */
function renderHome(){
  const has=S.r?3:S.a?2:0;
  $("banner").innerHTML=has?`<div class="banner"><div><h3>${S.r?"Your resume is ready":"Analysis ready"}</h3>
    <div class="small mute">${esc(S.job?.title||"")}${S.job?.company?" at "+esc(S.job.company):""}. Analyzing again replaces it.</div></div>
    <button id="cont">Continue</button></div>`:"";
  if(has)$("cont").onclick=()=>show(has);
}
$("home").onclick=()=>{req++;clearInterval(tick);renderHome();show(1)};

/* step 1 */
$("file").onchange=()=>$("fname").textContent=$("file").files[0]?.name||"Choose your resume";
const dz=$("drop");["dragenter","dragover"].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.add("over")}));
["dragleave","drop"].forEach(ev=>dz.addEventListener(ev,e=>{e.preventDefault();dz.classList.remove("over")}));
dz.addEventListener("drop",e=>{if(e.dataTransfer.files[0]){$("file").files=e.dataTransfer.files;$("file").onchange()}});
$("go").onclick=async()=>{
  if(!($("file").files[0]||$("rtext").value.trim().length>=50))return toast("Add your resume: upload a file or paste the text.");
  if(!$("jd").value.trim())return toast("Paste the job description.");
  const fd=new FormData();
  if($("file").files[0]) fd.append("resume",$("file").files[0]);
  fd.append("resume_text",$("rtext").value);
  S.job={title:$("title").value,company:$("company").value,jd:$("jd").value};
  Object.entries(S.job).forEach(([k,v])=>fd.append(k,v));
  const my=++req;
  loading(2,"Reading your resume",["Reading your resume…","Matching it against the job…","Finding skills the role expects…","Preparing your questions…"]);
  try{const a=await (await post("/api/analyze",fd,true)).json();if(my!==req)return;
    S.a=a;S.r=null;S.answers=[];S.extra={};S.prac=null;save();renderStep2();show(2);renderHome()}
  catch(e){if(my!==req)return;show(1);toast(e.message)}
  clearInterval(tick);
};

/* step 2 */
function renderStep2(){
  const a=S.a,lack=a.requirements.filter(x=>x.status!=="matched");
  $("score").innerHTML=`<h1 style="margin-bottom:24px">${esc(S.job.title||"Your match")}</h1>
   <div class="stats"><div><div class="big">${a.score}%</div><div class="bar"><i style="width:${a.score}%"></i></div><div class="mute small">match with this job</div></div>
   <div><div class="big">${lack.length}</div><div class="mute small">missing or unclear</div></div></div>
   ${lack.map(x=>`<div class="req"><i class="dot ${x.status}"></i><div><h3>${esc(x.skill)}</h3>
     <div class="small mute">${x.evidence?"Partly shown: “"+esc(x.evidence)+"”":"Not found in your resume"}</div></div>
     <div class="small mute">${esc(x.importance)}</div></div>`).join("")}
   ${a.hidden_skills?.length?`<h3 style="margin-top:40px">Skills this role usually expects</h3>
    <p class="mute small" style="margin:4px 0 0">Not in the posting, but common for the job.</p>
    <div class="chips">${a.hidden_skills.map(h=>`<span title="${esc(h.why)}">${esc(h.skill)}</span>`).join("")}</div>`:""}`;
  $("qs").innerHTML=qCards(a.questions||[])||'<p class="mute">Nothing to clarify.</p>';bindQ($("qs"));
  $("extra").innerHTML=EXTRA.map(([k,l])=>`<label>${l}</label><input data-k="${k}">`).join("");
}
$("back").onclick=()=>show(1);

async function generate(from,after){
  const my=++req;
  loading(3,"Writing your resume",["Rewriting your summary for this job…","Reordering skills by relevance…","Checking every line against your resume…","Finding courses for your gaps…"]);
  try{
    const r=await (await post("/api/generate",{resume_text:S.a.resume_text,...S.job,answers:S.answers,extra:S.extra,
      requirements:(S.r?.requirements)||S.a.requirements,keywords:S.a.keywords||[],hidden_skills:S.a.hidden_skills||[]})).json();
    if(my!==req)return;
    S.r=r;S.prac=null;save();renderAll();clearInterval(tick);renderHome();after();
  }catch(e){if(my!==req)return;clearInterval(tick);show(from);toast(e.message)}
}
$("gen").onclick=()=>{
  S.answers=readQ($("qs"));
  S.extra=Object.fromEntries([...$("extra").querySelectorAll("input")].map(i=>[i.dataset.k,i.value.trim()]).filter(x=>x[1]));
  generate(2,()=>show(3));
};

/* step 3 */
const setPath=(o,p,v)=>{const k=p.split(".");let t=o;k.slice(0,-1).forEach(x=>t=t[x]);t[k.at(-1)]=v};
function renderAll(){
  const r=S.r,reqs=r.requirements,before=S.a.score,after=Math.max(S.a.score,r.score),orig=S.a.resume_text;
  /* match tab */
  const more=reqs.filter(x=>x.status!=="matched").map(x=>({skill:x.skill,importance:x.importance,question:`Any experience with this? Work, college, projects or training all count.`}));
  r.missing_keywords.filter(k=>!reqs.some(x=>x.skill.toLowerCase().includes(k.toLowerCase()))).forEach(k=>more.push({skill:k,question:`Have you used or done anything with ${k}?`}));
  $("t-match").innerHTML=`<h2>${esc(S.job.title||"Your match")}${S.job.company?" at "+esc(S.job.company):""}</h2>
   <div class="stats"><div><div class="big">${before}% → ${after}%</div><div class="bar"><i style="width:${after}%"></i></div><div class="mute small">job match, before and after</div></div>
   <div><div class="big">${r.ats}%</div><div class="bar"><i style="width:${r.ats}%"></i></div><div class="mute small">job keywords in your resume</div></div>
   <div><div class="big">${r.gaps.length}</div><div class="mute small">skills to build</div></div></div>
   ${reqs.map(x=>`<div class="req"><i class="dot ${x.status}"></i><div><h3>${esc(x.skill)}</h3>
     <div class="small mute">${x.evidence?esc(x.evidence):"Not shown yet"}</div></div>
     <div class="small mute">${esc(x.importance)}</div></div>`).join("")}
   ${more.length?`<h2 style="margin-top:56px">Still missing</h2>
    <p class="mute" style="margin:0 0 8px">Tell us what’s true and we’ll add it to your resume. Skip anything that isn’t.</p>
    <div id="more">${qCards(more.slice(0,12))}</div>
    <div style="margin-top:24px"><button id="upd">Update my resume</button></div>`:""}`;
  if($("more")){bindQ($("more"));$("upd").onclick=()=>{
    const n=readQ($("more"));if(!n.length)return toast("Answer at least one question first.");
    S.answers=[...(S.answers||[]).filter(a=>!n.some(x=>x.skill===a.skill)),...n];
    generate(3,()=>{show(3);document.querySelector('#tabs [data-t="t-resume"]').click()})}}

  /* resume tab: edit + compare */
  const ed=(p,t,tag="span")=>`<${tag} contenteditable data-p="${p}">${esc(t)}</${tag}>`;
  const bl=(sec,i,b)=>b.map((x,j)=>`<li>${ed(`${sec}.${i}.bullets.${j}.text`,x.text)}</li>`).join("");
  const bc=b=>b.map(x=>`<li>${hl(x.text,/answers/i.test(x.original)?"":x.original)}${x.why?`<div class="why">${esc(x.why)}</div>`:""}</li>`).join("");
  const o=words(orig),hd=r.header||{};
  const contactEd=["email","phone","location"].filter(k=>hd[k]).map(k=>ed("header."+k,hd[k])).join(" | ");
  const realLinks=(hd.links||[]).map((l,i)=>[l,i]).filter(([l])=>!/^(mailto|tel):/.test(l.url||""));
  const linksEd=realLinks.map(([l,i])=>ed(`header.links.${i}.url`,l.url||l.label)).join(" | ");
  $("t-resume").innerHTML=`
   <div class="card">${r.flags.length?`<h3>Truth check: ${r.flags.length} to review</h3>${r.flags.map(f=>`<div class="flag"><b>${esc(f.text)}</b><div class="small mute">${esc(f.reason)}</div></div>`).join("")}`
     :`<h3 class="ok">Truth check passed</h3><p class="mute small" style="margin:6px 0 0">Every line is backed by your resume or your answers.</p>`}
     ${r.unclear.length?`<h3 style="margin-top:20px">Could be clearer</h3>${r.unclear.map(u=>`<div class="small" style="margin-top:6px"><b>${esc(u.section)}</b> <span class="mute">${esc(u.note)}</span></div>`).join("")}`:""}</div>
   <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center"><div class="seg" id="rv"><button class="on" data-v="edit">Edit</button><button data-v="cmp">Compare</button></div>
    <button id="pdf">Download PDF</button></div>
   <div id="v-edit"><p class="small mute" style="margin:12px 0 0">Click any line to edit. Use the arrows to reorder projects. Clear the summary to drop it. The PDF uses your edits.</p>
   <div class="paper" id="paper">${ed("header.name",hd.name||"","h1")}${hd.headline?`<div>${ed("header.headline",hd.headline)}</div>`:""}
    <div>${contactEd}</div>${linksEd?`<div>${linksEd}</div>`:""}
    <h4>Summary</h4>${ed("summary",r.summary,"div")}
    <h4>Skills</h4>${ed("skills",r.skills.join(", "),"div").replace("<div ","<div data-list ")}
    ${r.experience.length?`<h4>Experience</h4>`+r.experience.map((e,i)=>`<div class="head"><span>${esc(e.title)}, ${esc(e.org)}</span><span>${esc(e.dates)}</span></div><ul>${bl("experience",i,e.bullets)}</ul>`).join(""):""}
    ${r.projects.length?`<h4>Projects</h4>`+r.projects.map((p,i)=>`<div class="head"><span>${esc(p.title)}</span><span class="ctl">${i?`<button data-mv="${i}:-1" title="Move up">↑</button>`:""}${i<r.projects.length-1?`<button data-mv="${i}:1" title="Move down">↓</button>`:""}<button data-rm="${i}" title="Remove project">✕</button></span></div>${p.tech?`<div><i>${ed(`projects.${i}.tech`,p.tech)}</i></div>`:""}<ul>${bl("projects",i,p.bullets)}</ul>`).join(""):""}
    ${r.education.length?`<h4>Education</h4>`+r.education.map((e,i)=>ed("education."+i,e,"div")).join(""):""}
    ${(r.sections||[]).map((sc,i)=>`<h4>${esc(sc.title)}</h4><ul>${sc.items.map((t,j)=>`<li>${ed(`sections.${i}.items.${j}`,t)}</li>`).join("")}</ul>`).join("")}</div></div>
   <div id="v-cmp" class="hidden"><p class="legend"><mark>Highlighted</mark> text is new or reworded. Grey notes say why.</p>
    <div class="cmp"><div><h3>Original</h3><div class="paper"><pre>${esc(orig)}</pre></div></div>
    <div><h3>Tailored</h3><div class="paper"><b style="font-size:18px">${esc(hd.name)}</b>${hd.headline?`<div>${esc(hd.headline)}</div>`:""}<div>${esc([hd.email,hd.phone,hd.location].filter(Boolean).join(" | "))}</div><div>${esc(realLinks.map(([l])=>l.url||l.label).join(" | "))}</div>
     <h4>Summary</h4>${hl(r.summary,orig)}${r.summary_why?`<div class="why">${esc(r.summary_why)}</div>`:""}
     <h4>Skills</h4>${r.skills.map(s=>o.has(s.toLowerCase().split(/\s+/)[0])&&orig.toLowerCase().includes(s.toLowerCase())?esc(s):`<mark>${esc(s)}</mark>`).join(", ")}
     ${r.experience.length?`<h4>Experience</h4>`+r.experience.map(e=>`<div class="head"><span>${esc(e.title)}, ${esc(e.org)}</span><span>${esc(e.dates)}</span></div><ul>${bc(e.bullets)}</ul>`).join(""):""}
     ${r.projects.length?`<h4>Projects</h4>`+r.projects.map(p=>`<div class="head">${esc(p.title)}</div>${p.tech?`<div><i>${esc(p.tech)}</i></div>`:""}<ul>${bc(p.bullets)}</ul>`).join(""):""}
     ${r.education.length?`<h4>Education</h4>`+r.education.map(esc).join("<br>"):""}
     ${(r.sections||[]).map(sc=>`<h4>${esc(sc.title)}</h4><ul>${sc.items.map(t=>`<li>${esc(t)}</li>`).join("")}</ul>`).join("")}</div></div></div></div>`;
  $("paper").oninput=e=>{const p=e.target.dataset.p;if(!p)return;const t=e.target.innerText;
    setPath(r,p,e.target.hasAttribute("data-list")?t.split(",").map(s=>s.trim()).filter(Boolean):t);save()};
  $("paper").onclick=e=>{const b=e.target.closest("button");if(!b)return;
    if(b.dataset.mv){const[i,d]=b.dataset.mv.split(":").map(Number),a=r.projects;[a[i],a[i+d]]=[a[i+d],a[i]]}
    else if(b.dataset.rm)r.projects.splice(+b.dataset.rm,1);else return;
    save();renderAll()};
  $("rv").onclick=e=>{const v=e.target.dataset.v;if(!v)return;
    document.querySelectorAll("#rv button").forEach(b=>b.classList.toggle("on",b===e.target));
    $("v-edit").classList.toggle("hidden",v!=="edit");$("v-cmp").classList.toggle("hidden",v!=="cmp")};
  $("pdf").onclick=async()=>{busy($("pdf"),true,"Preparing…");
    try{const res=await post("/api/pdf",r),url=URL.createObjectURL(await res.blob()),a=document.createElement("a");
      a.href=url;a.download=(hd.name||"Resume").replace(/[^\w.-]+/g,"_")+"_Resume.pdf";a.click();URL.revokeObjectURL(url)}
    catch(e){toast(e.message)}busy($("pdf"),false)};

  /* courses */
  $("t-learn").innerHTML=`<h2>Courses to take</h2><p class="mute" style="margin:0 0 24px">Skills the job wants that your resume doesn’t show yet. Free options first.</p>`+
   (r.gaps.length?r.gaps.map(g=>`<div class="card"><h3>${esc(g.skill)} <span class="mute small">${esc(g.importance)}</span></h3>
    <p class="mute small" style="margin:6px 0 0">${esc(g.why)}</p>
    ${g.study?`<p class="small" style="margin:10px 0 0">Study: ${esc(Array.isArray(g.study)?g.study.join(", "):g.study)}</p>`:""}
    <div class="links">${g.resources.map(l=>`<a href="${l.url}" target="_blank" rel="noopener">${l.name}<span>${l.tag}</span></a>`).join("")}</div></div>`).join("")
   :`<p class="mute">No gaps found.</p>`);
  renderPractice();
}

/* practice interview */
function renderPractice(){
  const r=S.r,qs=r.interview_questions;S.prac=S.prac||{i:0,res:[]};const p=S.prac,box=$("t-int");
  if(!qs.length){box.innerHTML='<p class="mute">No questions yet.</p>';return}
  if(p.i>=qs.length){
    const avg=p.res.length?(p.res.reduce((a,x)=>a+x.score,0)/p.res.length).toFixed(1)+"/10":"–",weak=[...p.res].sort((a,b)=>a.score-b.score).slice(0,2);
    box.innerHTML=`<h2>Practice complete</h2><div class="stats"><div><div class="big">${avg}</div><div class="mute small">average score</div></div></div>
     ${weak.length?`<h3>Work on these next</h3>${weak.map(w=>`<div class="req" style="grid-template-columns:1fr"><div><h3>${esc(w.q)}</h3><div class="small mute">Scored ${w.score}/10. ${esc(w.improve||"")}</div></div></div>`).join("")}`:""}
     <div style="margin-top:24px;display:flex;gap:12px"><button id="again">Practice again</button><button class="ghost" id="tolearn">See courses</button></div>`;
    $("again").onclick=()=>{S.prac=null;renderPractice()};$("tolearn").onclick=()=>document.querySelector('#tabs [data-t="t-learn"]').click();return}
  const q=qs[p.i];
  box.innerHTML=`<div class="mute small">Question ${p.i+1} of ${qs.length}</div>
   <h2 style="margin-top:8px">${esc(q.question)}<span class="tg">${esc(q.type||"")}</span></h2>
   <textarea id="ans" placeholder="Type your answer as you would say it in the interview"></textarea>
   <div style="margin-top:16px;display:flex;gap:12px"><button id="fbk">Get feedback</button><button class="ghost" id="skip">Skip</button></div>
   <div id="fb"></div>`;
  $("skip").onclick=()=>{p.i++;save();renderPractice()};
  $("fbk").onclick=async()=>{
    const a=$("ans").value.trim();if(a.length<10)return toast("Write a short answer first.");
    busy($("fbk"),true,"Reading your answer…");$("fb").innerHTML=skLines();
    try{
      const f=await (await post("/api/practice",{resume_text:S.a.resume_text,...S.job,answers:S.answers,extra:S.extra,question:q.question,tip:q.tip,answer:a})).json();
      p.res.push({q:q.question,score:f.score,improve:(f.improve||[])[0]});save();
      $("fb").innerHTML=`<div class="fb"><div class="big">${f.score}/10</div>
       <h3 style="margin-top:16px">What worked</h3><ul>${(f.strengths||[]).map(x=>`<li>${esc(x)}</li>`).join("")}</ul>
       <h3>To improve</h3><ul>${(f.improve||[]).map(x=>`<li>${esc(x)}</li>`).join("")}</ul>
       <h3>A stronger answer</h3><div class="sample">${esc(f.sample)}</div>
       ${f.follow_up?`<p class="mute small">Likely follow-up: ${esc(f.follow_up)}</p>`:""}
       <button id="nx">${p.i+1<qs.length?"Next question":"Finish"}</button></div>`;
      $("fbk").classList.add("hidden");$("skip").classList.add("hidden");$("nx").onclick=()=>{p.i++;save();renderPractice()};
    }catch(e){$("fb").innerHTML="";toast(e.message)}busy($("fbk"),false);
  };
}

$("tabs").onclick=e=>{const t=e.target.dataset.t;if(!t)return;
  document.querySelectorAll("#tabs button").forEach(b=>b.classList.toggle("on",b===e.target));
  ["t-match","t-resume","t-learn","t-int"].forEach(x=>$(x).classList.toggle("hidden",x!==t));window.scrollTo(0,0)};
$("restart").onclick=()=>{S={};save();location.reload()};
try{if(S.r){renderAll();show(3)}else if(S.a){renderStep2();show(2)}else show(1)}catch(e){S={};save();show(1)}
renderHome();
