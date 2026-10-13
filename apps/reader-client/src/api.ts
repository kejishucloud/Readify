/** Session-based V2 client. Native auth is intentionally NOT claimed as ready. */
export interface Book { id:number; title:string; author:string; format:string; url:string }
export interface ChapterRef { number:number; title:string }
export interface ChapterData { number:number; title:string; content:string }
export interface ChapterResponse {
  book:{id:number;title:string}; chapter:ChapterData;
  chapters:ChapterRef[]; progress:{chapter:number;position:number};
}
export interface Note {id:number;chapter:number;position:number;selected_text:string;content:string;type:string;created_at:string}

const getToken = () => document.cookie.split("; ").find(v=>v.startsWith("csrftoken="))?.split("=")[1] || "";
const BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function request<T>(path:string, options:RequestInit={}):Promise<T> {
  const response = await fetch(BASE+path,{
    credentials:"include",
    ...options,
    headers:{
      ...(options.body ? {"X-CSRFToken":decodeURIComponent(getToken())} : {}),
      ...options.headers,
    },
  });
  const contentType=response.headers.get("content-type") || "";
  if (!contentType.includes("json")) {
    throw new Error("需要登录 Readify 或配置同源 API；原生端登录尚未实现。");
  }
  const result:unknown=await response.json();
  if (!response.ok) {
    const msg=(result && typeof result==="object" && "error" in result) ? String(result.error) : "HTTP "+response.status;
    throw new Error(msg);
  }
  return result as T;
}
export const api={
  books:()=>request<{books:Book[]}>("/api/v2/books/"),
  chapter:(book:number,n:number)=>request<ChapterResponse>(`/api/v2/books/${book}/chapters/${n}/`),
  progress:(book:number,n:number,p:number)=>request<{success:boolean}>(`/api/v2/books/${book}/progress/`,{
    method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({chapter:n,position:p}),
  }),
  notes:(book:number)=>request<{notes:Note[]}>(`/api/v2/books/${book}/notes/`),
  saveNote:(book:number,n:number,p:number,selection:string,content:string)=>request<{id:number}>(`/api/v2/books/${book}/notes/create/`,{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({chapter:n,position:p,selected_text:selection,content}),
  }),
};
