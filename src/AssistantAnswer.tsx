import React,{useState} from 'react';
import {Sparkles,FileDown,ListPlus,Check,Info,MessageSquareText,ArrowRight} from 'lucide-react';
import type {Requester,Row} from './BusinessPages';
import {MetricGrid} from './ui';

export const PERIODS:Record<string,string>={monthly:'Mensal',weekly:'Semanal',daily:'Diário'};
const TRENDS:Record<string,string>={up:'Em alta',down:'Em queda',flat:'Estável',none:''};
const PRIORITY:Record<string,string>={high:'Prioridade alta',medium:'Prioridade média',low:'Prioridade baixa'};
export const when=(v:string)=>new Date(v).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
export const today=()=>new Date().toLocaleDateString('en-CA');

/** One stored analysis. `compact` is the version shown in the floating assistant. */
export function AssistantAnswer({report,base,request,compact=false}:{report:Row;base:string;request:Requester;compact?:boolean}){
 const [planned,setPlanned]=useState<string[]>([]),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const answer=report.answer;
 async function exportPdf(){
  setError('');
  try{const r=await request(base+'/assistant/'+report.id+'/pdf');const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=`analise-${report.anchor}.pdf`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setNotice('PDF gerado. Confira a pasta de downloads.')}
  catch(e){setError((e as Error).message)}
 }
 async function plan(action:Row){
  setError('');
  try{await request(base+'/records/action_plans',{method:'POST',body:JSON.stringify({title:action.title.slice(0,160),description:action.description,priority:action.priority})});setPlanned(p=>[...p,action.title]);setNotice('Plano criado. Acompanhe em Planos de ação.')}
  catch(e){setError((e as Error).message)}
 }
 const actions=compact?answer.actions.slice(0,3):answer.actions;
 return <article className={'assistant-answer'+(compact?' is-compact':'')} tabIndex={-1} aria-label="Resposta do assistente">
  <header className="assistant-answer-head"><div><span className="assistant-tag"><Sparkles size={14}/> Análise automática</span><h2>{answer.title}</h2>
   <p className="assistant-meta">{PERIODS[report.period]} · referência {report.anchor.split('-').reverse().join('/')} · {when(report.created_at)}</p>
   {!compact&&<p className="assistant-asked"><MessageSquareText size={15}/> {report.question}</p>}</div>
   {!compact&&<button className="secondary-action" onClick={exportPdf}><FileDown size={17}/>Exportar PDF</button>}</header>
  {error&&<p role="alert" className="workspace-error">{error}</p>}{notice&&<p role="status" className="workspace-notice">{notice}</p>}
  <p className="assistant-summary">{answer.summary}</p>
  {answer.highlights.length>0&&<MetricGrid label="Números-chave" items={(compact?answer.highlights.slice(0,4):answer.highlights).map((h:Row)=>({label:h.label,value:h.value,hint:[TRENDS[h.trend],h.note].filter(Boolean).join(' · ')}))}/>}
  {!compact&&answer.sections.map((s:Row,i:number)=><section className="assistant-section" key={i}><h3>{s.heading}</h3>{s.paragraphs.map((p:string,j:number)=><p key={j}>{p}</p>)}{s.bullets.length>0&&<ul>{s.bullets.map((b:string,j:number)=><li key={j}>{b}</li>)}</ul>}</section>)}
  {actions.length>0&&<section className="assistant-section"><h3>{compact?'O que fazer agora':'Próximas ações recomendadas'}</h3><div className="assistant-actions">{actions.map((a:Row)=><article key={a.title} className={'assistant-action is-'+a.priority}><span>{PRIORITY[a.priority]}</span><strong>{a.title}</strong><p>{a.description}</p><button disabled={planned.includes(a.title)} onClick={()=>plan(a)}>{planned.includes(a.title)?<><Check size={15}/>Plano criado</>:<><ListPlus size={15}/>Criar plano de ação</>}</button></article>)}</div></section>}
  {!compact&&answer.caveats.length>0&&<aside className="assistant-caveats"><Info size={18}/><div><strong>Limitações dos dados</strong><ul>{answer.caveats.map((c:string,i:number)=><li key={i}>{c}</li>)}</ul></div></aside>}
  {compact?<div className="assistant-compact-actions"><a className="primary-button" href={'#/workspace/assistant/'+report.id}>Ver análise completa <ArrowRight size={16}/></a><button className="secondary-action" onClick={exportPdf}><FileDown size={16}/>PDF</button></div>
   :<p className="assistant-disclaimer">Análise gerada automaticamente pelo Sobrevo a partir dos registros da empresa. Confira os números antes de decidir; não representa saldo bancário nem apuração fiscal.</p>}
 </article>
}
