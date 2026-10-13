"use strict";

/** V2 book reader. Strict textContent rendering prevents executable book HTML. */
class ReaderV2 {
  constructor() {
    this.id = Number(document.body.dataset.bookId);
    this.token = document.querySelector('[name=csrfmiddlewaretoken]').value;
    this.$ = id => document.getElementById(id);
    this.chapters = []; this.chapter = null; this.paragraphs = [];
    this.position = 0; this.loading = null; this.talking = false; this.audio = null;
    this.systemVoices = []; this.timer = null;
    this.prefs = this.readPrefs();
    this.bind(); this.applyPrefs(); this.load(Number(new URLSearchParams(location.search).get("chapter")) || 1);
    this.loadVoices();
    if ("speechSynthesis" in window) {
      this.populateVoices(); speechSynthesis.onvoiceschanged = () => this.populateVoices();
    }
  }
  readPrefs() {
    try { return {...{theme:"paper",font:20,line:1.9,rate:1},...JSON.parse(localStorage.getItem("readify:v2:reader") || "{}")}; }
    catch { return {theme:"paper",font:20,line:1.9,rate:1}; }
  }
  applyPrefs() {
    const p=this.prefs;
    if (!["paper","warm","dark"].includes(p.theme)) p.theme="paper";
    document.body.dataset.theme=p.theme;
    document.documentElement.style.setProperty("--font", Math.min(32,Math.max(15,Number(p.font)||20))+"px");
    document.documentElement.style.setProperty("--leading",String(Math.min(2.6,Math.max(1.4,Number(p.line)||1.9))));
    for (const [field,value,label] of [["font",p.font,"font-label"],["line",p.line,"line-label"],["rate",p.rate,"rate-label"]]) this.$(field).value=value;
    this.$("font-label").textContent=p.font+"px"; this.$("line-label").textContent=Number(p.line).toFixed(1);this.$("rate-label").textContent=Number(p.rate).toFixed(1)+"×";
  }
  savePrefs() { try{localStorage.setItem("readify:v2:reader",JSON.stringify(this.prefs));}catch{} }
  async json(url,options={}) {
    const r=await fetch(url,{credentials:"same-origin",...options}),data=await r.json().catch(()=>({}));
    if (!r.ok) throw Error(data.error||"请求失败："+r.status);
    return data;
  }
  error(message) { const el=this.$("error");el.textContent=message;el.hidden=false;this.$("save-state").textContent="失败"; }
  async load(chapterNumber) {
    this.stop(); this.loading?.abort(); const controller=new AbortController();this.loading=controller;
    this.$("save-state").textContent="读取中";
    try {
      const data=await this.json(`/api/v2/books/${this.id}/chapters/${chapterNumber}/`,{signal:controller.signal});
      if (this.loading!==controller) return;
      this.chapter=data.chapter;this.chapters=data.chapters;
      this.$("chapter-caption").textContent="CHAPTER "+chapterNumber;
      this.$("chapter-title").textContent=data.chapter.title||"第 "+chapterNumber+" 章";
      this.$("error").hidden=true;
      const article=this.$("content");article.replaceChildren();
      this.paragraphs=String(data.chapter.content||"").split(/\n\s*\n/).map(x=>x.trim()).filter(Boolean).map((text,index)=>{
        const p=document.createElement("p");p.textContent=text;p.dataset.index=index;article.appendChild(p);return p;
      });
      this.position=data.progress?.chapter===chapterNumber?Math.max(0,Math.min(this.paragraphs.length-1,data.progress.position)):0;
      this.renderNav();this.updatePosition();
      this.$("reader").scrollTop=0;
      if (this.position) this.paragraphs[this.position]?.scrollIntoView({block:"start"});
      this.$("save-state").textContent="已读取";
      history.replaceState(null,"",`/books/${this.id}/v2/?chapter=${chapterNumber}`);
    } catch(e) { if(e.name!=="AbortError") this.error(e.message); }
  }
  renderNav() {
    const nav=this.$("chapters");nav.replaceChildren();
    this.chapters.forEach(ch=>{
      const b=document.createElement("button");b.type="button";b.textContent=ch.title||"第 "+ch.number+" 章";
      b.setAttribute("aria-current",String(ch.number===this.chapter.number));
      b.addEventListener("click",()=>{this.closePanels();this.moveTo(ch.number);});nav.append(b);
    });
    const index=this.chapters.findIndex(c=>c.number===this.chapter.number);
    this.$("prev").disabled=index===0;this.$("next").disabled=index===this.chapters.length-1;
    this.$("chapter-index").textContent=`${index+1} / ${this.chapters.length}`;
  }
  updatePosition() {
    const count=Math.max(1,this.paragraphs.length),pct=Math.round(100*(this.position+1)/count);
    this.$("position").textContent=`第 ${this.chapter?.number||1} 章 · 第 ${this.position+1}/${count} 段`;
    this.$("percent").textContent=pct+"%";this.$("fill").style.width=pct+"%";
  }
  async persist() {
    if (!this.chapter) return;
    try{
      await this.json(`/api/v2/books/${this.id}/progress/`,{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":this.token},body:JSON.stringify({chapter:this.chapter.number,position:this.position})});
      this.$("save-state").textContent="已同步";
    }catch {this.$("save-state").textContent="同步失败";}
  }
  scheduleSave() {clearTimeout(this.timer);this.$("save-state").textContent="未同步";this.timer=setTimeout(()=>this.persist(),900);}
  async moveTo(number) {if(this.chapter) await this.persist();this.load(number);}
  adjacent(step) {const i=this.chapters.findIndex(c=>c.number===this.chapter?.number),next=this.chapters[i+step];if(next)this.moveTo(next.number);}
  closePanels() {this.$("toc").classList.remove("open");this.$("settings").hidden=true;this.$("shade").hidden=true;}
  togglePanel(which) {
    const toc=this.$("toc"),settings=this.$("settings");
    const willOpen=which==="toc"?!toc.classList.contains("open"):settings.hidden;
    this.closePanels();if(willOpen){if(which==="toc")toc.classList.add("open");else settings.hidden=false;this.$("shade").hidden=false;}
  }
  bind() {
    this.$("prev").onclick=()=>this.adjacent(-1);this.$("next").onclick=()=>this.adjacent(1);
    this.$("toc-toggle").onclick=()=>this.togglePanel("toc");this.$("settings-toggle").onclick=()=>this.togglePanel("settings");
    for (const id of ["toc-close","settings-close","shade"])this.$(id).onclick=()=>this.closePanels();
    let queued=false;this.$("reader").addEventListener("scroll",()=>{
      if(queued)return;queued=true;requestAnimationFrame(()=>{
        queued=false;const top=this.$("reader").getBoundingClientRect().top+60;let i=0;
        this.paragraphs.forEach((el,n)=>{if(el.getBoundingClientRect().top<=top)i=n;});
        if(this.chapter&&i!==this.position){this.position=i;this.updatePosition();this.scheduleSave();}
      });
    },{passive:true});
    for(const [id,key] of [["font","font"],["line","line"],["rate","rate"]]){
      this.$(id).oninput=e=>{this.prefs[key]=Number(e.target.value);this.applyPrefs();this.savePrefs();};
    }
    document.querySelectorAll("[data-reader-theme]").forEach(el=>el.onclick=()=>{this.prefs.theme=el.dataset.readerTheme;this.applyPrefs();this.savePrefs();});
    this.$("speak").onclick=()=>this.talking?this.stop():this.start();
    this.$("save-note").onclick=()=>this.createNote();
    this.$("show-notes").onclick=()=>this.showNotes();
    this.$("add-voice").onclick=()=>this.$("voice-dialog").showModal();
    this.$("cancel-voice").onclick=this.$("close-voice").onclick=()=>this.$("voice-dialog").close();
    this.$("voice-form").onsubmit=e=>this.createVoice(e);
    document.addEventListener("keydown",e=>{if(e.target.closest("input,textarea,select,[contenteditable]"))return;if(e.key==="Escape")this.closePanels();if(e.altKey&&e.key==="ArrowRight")this.adjacent(1);if(e.altKey&&e.key==="ArrowLeft")this.adjacent(-1);});
    window.addEventListener("pagehide",()=>{clearTimeout(this.timer);this.persist();this.stop();});
  }
  populateVoices() {
    this.systemVoices=speechSynthesis.getVoices();
    const select=this.$("voice"),selected=select.value;select.replaceChildren(new Option("系统默认",""));
    this.systemVoices.forEach((voice,i)=>select.add(new Option(`${voice.name} · ${voice.lang}`,String(i))));
    if([...select.options].some(x=>x.value===selected))select.value=selected;
  }
  async loadVoices() {
    try{
      const result=await this.json("/api/v2/voices/");
      [...this.$("voice-mode").options].forEach(opt=>{if(opt.value!=="browser")opt.disabled=!result.clone_available;});
      const select=this.$("clone-profile");select.replaceChildren(new Option("选择授权音色",""));
      result.voices.forEach(v=>select.add(new Option(v.name,String(v.id))));
    }catch{}
  }
  async createVoice(event) {
    event.preventDefault();const error=this.$("voice-error");error.hidden=true;
    if(!this.$("consent").checked){error.textContent="必须确认声音权利";error.hidden=false;return;}
    const data=new FormData(this.$("voice-form"));data.append("consent","yes");
    try{
      const voice=await this.json("/api/v2/voices/create/",{method:"POST",headers:{"X-CSRFToken":this.token},body:data});
      this.$("voice-dialog").close();this.$("voice-form").reset();
      await this.loadVoices();this.$("clone-profile").value=String(voice.id);
      this.$("save-state").textContent="音色已保存";
    }catch(e){error.textContent=e.message;error.hidden=false;}
  }
  async createNote() {
    if (!this.chapter) return;
    const selection=String(window.getSelection()?.toString() || "").slice(0,1000);
    const parent=window.getSelection()?.anchorNode?.parentElement;
    const indexEl=parent?.closest("#content p");
    const position=indexEl?Number(indexEl.dataset.index):this.position;
    const note=window.prompt("请输入笔记（可空，仅保存所选摘录）", "");
    if (note===null) return;
    if (!selection.trim() && !note.trim()) return;
    try{
      await this.json(`/api/v2/books/${this.id}/notes/create/`,{
        method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":this.token},
        body:JSON.stringify({chapter:this.chapter.number,position,selected_text:selection,content:note.slice(0,2000)})
      });
      this.$("save-state").textContent="笔记已保存";
      window.getSelection()?.removeAllRanges();
    }catch(e){this.error(e.message);}
  }
  async showNotes() {
    if (!this.chapter) return;
    try{
      const result=await this.json(`/api/v2/books/${this.id}/notes/`);
      const list=this.$("notes-list");list.replaceChildren();
      if (!result.notes.length){list.textContent="尚无笔记。选中正文后点击「记笔记」。";return;}
      result.notes.forEach(note=>{
        const item=document.createElement("button");item.type="button";
        item.textContent=`第 ${note.chapter} 章 · ${(note.selected_text||note.content).slice(0,70)}`;
        item.onclick=()=>{this.closePanels();this.load(note.chapter).then(()=>{
          this.paragraphs[Math.min(note.position,this.paragraphs.length-1)]?.scrollIntoView({block:"center"});
        });};
        list.append(item);
      });
    }catch(e){this.error(e.message);}
  }
  async start() {
    if(!this.chapter||!this.paragraphs.length)return;
    if(this.$("voice-mode").value==="browser"&&!("speechSynthesis" in window)){this.error("当前设备不支持浏览器语音");return;}
    if(this.$("voice-mode").value!=="browser"&&!this.$("clone-profile").value){this.error("请先选择一个已授权音色");return;}
    this.talking=true;this.$("speak").textContent="■ 停止";this.say(this.position);
  }
  async say(index) {
    if(!this.talking)return;if(index>=this.paragraphs.length){this.stop();return;}
    this.position=index;this.updatePosition();this.scheduleSave();
    this.paragraphs.forEach(p=>p.classList.remove("speaking"));
    const p=this.paragraphs[index];p.classList.add("speaking");p.scrollIntoView({block:"center"});
    const mode=this.$("voice-mode").value,text=p.textContent;
    if(mode==="browser"){
      speechSynthesis.cancel();const phrase=new SpeechSynthesisUtterance(text.slice(0,900));
      const v=this.$("voice").value;if(v)phrase.voice=this.systemVoices[Number(v)]||null;
      phrase.rate=Number(this.prefs.rate)||1;phrase.onend=()=>{if(this.talking)this.say(index+1);};
      phrase.onerror=()=>{if(this.talking){this.stop();this.error("系统语音暂不可用");}};
      speechSynthesis.speak(phrase);return;
    }
    try{
      const r=await fetch("/api/v2/tts/synthesize/",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json","X-CSRFToken":this.token},
        body:JSON.stringify({mode,style:this.$("voice-style").value,voice_id:Number(this.$("clone-profile").value),text:text.slice(0,500)})});
      if(!r.ok){const err=await r.json().catch(()=>({}));throw Error(err.error||"语音合成失败");}
      if(!this.talking)return;
      const url=URL.createObjectURL(await r.blob()),audio=new Audio(url);this.audio=audio;
      audio.onended=()=>{URL.revokeObjectURL(url);if(this.talking)this.say(index+1);};
      audio.onerror=()=>{URL.revokeObjectURL(url);this.stop();this.error("播放失败");};
      await audio.play();
    }catch(e){this.stop();this.error(e.message);}
  }
  stop() {
    this.talking=false;this.$("speak").textContent="▶ 朗读";
    this.paragraphs.forEach(p=>p.classList.remove("speaking"));
    if("speechSynthesis" in window)speechSynthesis.cancel();
    if(this.audio){this.audio.pause();this.audio.src="";this.audio=null;}
  }
}
document.addEventListener("DOMContentLoaded",()=>{
  if(document.body.dataset.bookId)new ReaderV2();
  if("serviceWorker" in navigator && (location.protocol==="https:" || location.hostname==="localhost")){
    navigator.serviceWorker.register("/static/js/readify-sw.js",{scope:"/static/"}).catch(()=>{});
  }
});
