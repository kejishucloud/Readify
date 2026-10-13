import {useCallback, useEffect, useMemo, useRef, useState} from "react";
import {api, type Book, type ChapterResponse, type Note} from "./api";

/** Shared PWA/Desktop/Mobile layout; native sign-in/secure storage pending. */
export default function App(){
  const [books,setBooks]=useState<Book[]>([]);
  const [selected,setSelected]=useState<Book|null>(null);
  const [page,setPage]=useState<ChapterResponse|null>(null);
  const [notes,setNotes]=useState<Note[]>([]);
  const [panel,setPanel]=useState<"books"|"chapters"|"notes">("books");
  const [error,setError]=useState("");
  const [font,setFont]=useState(20);
  const [dark,setDark]=useState(false);
  const [status,setStatus]=useState("连接中");
  const [speaking,setSpeaking]=useState(false);
  const scroll=useRef<HTMLElement>(null);
  const selectedRef=useRef<number|null>(null);
  const chapterRef=useRef<number|null>(null);
  const position=useRef(0);
  const timer=useRef<number|undefined>(undefined);

  useEffect(()=>{
    api.books().then(r=>{setBooks(r.books);setStatus("已连接");}).catch(e=>{setError(String(e));setStatus("无法连接");});
    return ()=>{window.clearTimeout(timer.current);window.speechSynthesis?.cancel();};
  },[]);
  const load=useCallback(async(book:Book,n:number)=>{
    try{
      setStatus("读取中");
      const result=await api.chapter(book.id,n);
      selectedRef.current=book.id;chapterRef.current=n;
      position.current=result.progress.chapter===n?result.progress.position:0;
      setPage(result);setError("");setStatus("已载入");
      if(scroll.current)scroll.current.scrollTop=0;
    }catch(e){setError(String(e));setStatus("读取失败");}
  },[]);
  const chapters=page?.chapters||[];
  const parts=useMemo(()=>page?.chapter.content.split(/\n\s*\n/).map(p=>p.trim()).filter(Boolean)||[],[page]);
  const index=chapters.findIndex(x=>x.number===page?.chapter.number);

  const save=useCallback(async(bookId:number,n:number,p:number)=>{
    try{await api.progress(bookId,n,p);setStatus("已同步");}
    catch{setStatus("同步失败");}
  },[]);

  const next=async(delta:number)=>{
    if(!selected || !page)return;
    const target=chapters[index+delta];if(!target)return;
    window.clearTimeout(timer.current);
    await save(selected.id,page.chapter.number,position.current);
    window.speechSynthesis?.cancel();setSpeaking(false);
    await load(selected,target.number);
  };

  const onScroll=()=>{
    if(!page||!selected||!scroll.current)return;
    const elements=scroll.current.querySelectorAll<HTMLElement>("[data-pidx]");
    const rect=scroll.current.getBoundingClientRect();
    let p=0;for(const el of elements){if(el.getBoundingClientRect().top < rect.top+100)p=Number(el.dataset.pidx);}
    if(p===position.current)return;
    position.current=p;setStatus("未同步");
    window.clearTimeout(timer.current);
    const b=selected.id,n=page.chapter.number;
    timer.current=window.setTimeout(()=>save(b,n,p),900);
  };

  const addNote=async()=>{
    if(!selected||!page)return;
    const quote=window.getSelection()?.toString().slice(0,1000)||"";
    const note=window.prompt("输入阅读笔记（可仅保存选中的文字）","");if(note===null)return;
    if(!quote.trim()&&!note.trim())return;
    try{
      await api.saveNote(selected.id,page.chapter.number,position.current,quote,note.slice(0,2000));
      setStatus("笔记已保存");
      const result=await api.notes(selected.id);setNotes(result.notes);
    }catch(e){setError(String(e));}
  };

  const showNotes=async()=>{
    if(!selected)return;
    try{const result=await api.notes(selected.id);setNotes(result.notes);setPanel("notes");}
    catch(e){setError(String(e));}
  };

  const speak=()=>{
    if(!("speechSynthesis" in window)) {setError("当前设备不支持系统语音");return;}
    if(speaking){window.speechSynthesis.cancel();setSpeaking(false);return;}
    if(!page)return;
    const phrase=new SpeechSynthesisUtterance(parts.slice(position.current).join(" ").slice(0,1800));
    phrase.rate=1;phrase.onend=()=>setSpeaking(false);phrase.onerror=()=>setSpeaking(false);
    window.speechSynthesis.speak(phrase);setSpeaking(true);
  };

  return <div className={"shell "+(dark?"dark":"")}>
    <header className="header">
      <strong className="logo" onClick={()=>{setSelected(null);setPage(null);setPanel("books");}}>Readify <span>V2</span></strong>
      <span className="head-title">{selected?.title||"智能阅读空间"}</span>
      <div className="actions">
        <button onClick={()=>setPanel(panel==="books"?"chapters":"books")}>☰</button>
        {selected&&<><button onClick={addNote}>✎ 摘录</button><button onClick={speak}>{speaking?"■ 停止":"▶ 朗读"}</button></>}
        <button onClick={()=>setDark(!dark)} aria-label="切换主题">{dark?"☀":"◐"}</button>
      </div>
    </header>
    <div className="content-grid">
      <aside className="sidebar"><h2>{panel==="books"?"我的书库":panel==="chapters"?"章节目录":"我的笔记"}</h2>
      {panel==="books"&&books.map(b=><button className="side-entry" key={b.id} onClick={()=>{setSelected(b);setPanel("chapters");void load(b,1);}}><strong>{b.title}</strong><small>{b.author||b.format}</small></button>)}
      {panel==="chapters"&&chapters.map(ch=><button className={"side-entry "+(page?.chapter.number===ch.number?"active":"")} key={ch.number} onClick={()=>{if(selected)void load(selected,ch.number);}}>{ch.title||"第 "+ch.number+" 章"}</button>)}
      {panel==="notes"&&notes.map(n=><button className="side-entry" key={n.id} onClick={()=>{if(selected)void load(selected,n.chapter);}}><small>第 {n.chapter} 章</small>{n.selected_text||n.content}</button>)}
      <div className="side-footer">{selected&&<button onClick={()=>void showNotes()}>查看笔记</button>}<a href="/user/login/">账户登录</a></div>
      </aside>
      <main ref={scroll} className="read-pane" onScroll={onScroll}><div className="page">
        {error&&<p className="error" role="alert">{error}</p>}
        {!selected?<><p className="eyebrow">WELCOME TO READIFY</p><h1>让每一次阅读，都更有收获。</h1><p className="muted">从左侧书库选取一本书。首次访问请在同源 Readify 服务完成登录。</p>
          {books.length===0&&!error&&<p className="muted">书库暂无书籍，或正在载入。</p>}</>
        :page?<><p className="eyebrow">CHAPTER {page.chapter.number}</p>
          <h1>{page.chapter.title||"第 "+page.chapter.number+"章"}</h1>
          <article style={{fontSize:font}}>{parts.map((t,i)=><p data-pidx={i} key={i}>{t}</p>)}</article>
          <nav className="pager"><button disabled={index<=0} onClick={()=>void next(-1)}>← 上一章</button><span>{index+1} / {chapters.length}</span><button disabled={index>=chapters.length-1} onClick={()=>void next(1)}>下一章 →</button></nav>
        </>:<p>正在加载…</p>}
      </div></main>
      <aside className="rightpane"><h2>阅读设置</h2>
        <label htmlFor="font">字体大小 · {font}px</label>
        <input id="font" type="range" min="15" max="30" value={font} onChange={e=>setFont(Number(e.target.value))}/>
        <p className="muted">本客户端是独立 React 跨平台工程；授权声音克隆暂通过现有 V2 Django 阅读器使用。</p>
        {selected&&<a href={selected.url}>打开语音克隆阅读器 ↗</a>}
      </aside>
    </div><footer className="bottom"><span>{status}</span><span>{selected?.title||"跨设备阅读 · Web / Desktop / Mobile"}</span></footer>
  </div>;
}
