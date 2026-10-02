import React,{useEffect,useRef,useState} from 'react';
import {Sparkles,Send,X,LoaderCircle,ArrowRight} from 'lucide-react';
import type {Requester,Row} from './BusinessPages';
import {AssistantAnswer,PERIODS,today} from './AssistantAnswer';
import './assistant.css';

/** Questions that make sense from each screen; the first one fits the page the owner is on. */
const CONTEXT:Record<string,{label:string;questions:string[]}>={
 dashboard:{label:'Painel de controle',questions:['Faça um resumo executivo da empresa neste período.','Compare este período com o anterior. O que mudou?','O que devo priorizar esta semana?']},
 analysis:{label:'Painel de controle',questions:['Faça um resumo executivo da empresa neste período.','Compare este período com o anterior. O que mudou?','O que devo priorizar esta semana?']},
 products:{label:'Produtos',questions:['Quais produtos estão me dando prejuízo e por quê?','Quais produtos mais deixam resultado?','Minhas margens estão boas?']},
 sales:{label:'Vendas',questions:['Quais produtos estão me dando prejuízo e por quê?','Compare as vendas com o período anterior.','Como fica meu caixa nos próximos 30 dias?']},
 receivables:{label:'Valores a receber',questions:['Como fica meu caixa nos próximos 30 dias?','Tenho recebimentos atrasados?','Faça um resumo executivo da empresa neste período.']},
 simulator:{label:'Simulador de preço',questions:['Quais produtos estão me dando prejuízo e por quê?','O parcelamento está tirando minha margem?','Minhas margens estão boas?']},
 payables:{label:'Contas a pagar',questions:['Como fica meu caixa nos próximos 30 dias?','Minhas despesas estão altas para o que eu vendo?','Tenho contas vencidas?']},
 inventory:{label:'Estoque',questions:['Como está meu estoque? O que preciso repor?','O que está sem saldo no estoque?','Faça um resumo executivo da empresa neste período.']},
 customers:{label:'Clientes',questions:['Quais clientes preciso contatar esta semana?','Faça um resumo executivo da empresa neste período.','O que devo priorizar esta semana?']},
 plans:{label:'Planos de ação',questions:['O que devo priorizar esta semana para melhorar o resultado?','Faça um resumo executivo da empresa neste período.','Quais produtos estão me dando prejuízo e por quê?']},
};
const FALLBACK={label:'',questions:['Faça um resumo executivo da empresa neste período.','O que devo priorizar esta semana?','Como fica meu caixa nos próximos 30 dias?']};

export function AssistantDock({base,request,area}:{base:string;request:Requester;area:string}){
 const [open,setOpen]=useState(false),[question,setQuestion]=useState(''),[period,setPeriod]=useState('monthly');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[report,setReport]=useState<Row|null>(null);
 const panel=useRef<HTMLElement>(null),input=useRef<HTMLTextAreaElement>(null),trigger=useRef<HTMLButtonElement>(null);
 const context=CONTEXT[area]||FALLBACK;
 const wasOpen=useRef(false);
 // Focus the question on open; give focus back to the trigger once it re-mounts on close.
 useEffect(()=>{if(open)setTimeout(()=>input.current?.focus(),30);else if(wasOpen.current)trigger.current?.focus();wasOpen.current=open},[open]);
 useEffect(()=>{setReport(null);setError('')},[base]);
 useEffect(()=>{if(!open)return;const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(false)};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[open]);
 async function ask(text=question){
  const q=text.trim();if(q.length<3||busy)return;
  setQuestion(q);setBusy(true);setError('');setReport(null);
  try{setReport(await (await request(base+'/assistant',{method:'POST',body:JSON.stringify({question:q,period,anchor:today()})})).json());setTimeout(()=>panel.current?.querySelector('.assistant-answer')?.scrollIntoView({behavior:'smooth',block:'start'}),50)}
  catch(e){setError((e as Error).message)}
  finally{setBusy(false)}
 }
 return <>
  {!open&&<button ref={trigger} className="assistant-fab" onClick={()=>setOpen(true)} aria-haspopup="dialog" aria-label="Perguntar ao Sobrevo"><Sparkles size={19}/><span>Perguntar ao Sobrevo</span></button>}
  {open&&<aside ref={panel} className="assistant-dock" role="dialog" aria-label="Assistente de análise">
   <header className="assistant-dock-head"><span className="assistant-icon"><Sparkles size={18}/></span><div><h2>Assistente de análise</h2><p>{context.label?`Você está em ${context.label}. `:''}Pergunte sobre os números da empresa.</p></div>
    <button className="assistant-dock-close" aria-label="Fechar assistente" onClick={()=>setOpen(false)}><X size={18}/></button></header>
   <form className="assistant-dock-form" onSubmit={e=>{e.preventDefault();ask()}}>
    <label className="assistant-question">Sua pergunta<textarea ref={input} rows={2} maxLength={1000} value={question} disabled={busy} placeholder="Ex.: Por que meu lucro caiu este mês?" onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask()}}}/></label>
    <div className="assistant-dock-row"><label>Período<select value={period} disabled={busy} onChange={e=>setPeriod(e.target.value)}>{Object.entries(PERIODS).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label>
     <button className="primary-button" disabled={busy||question.trim().length<3}>{busy?<LoaderCircle className="assistant-spin" size={16}/>:<Send size={16}/>}{busy?'Analisando…':'Perguntar'}</button></div>
   </form>
   {!report&&!busy&&<div className="assistant-suggestions" aria-label="Sugestões para esta tela">{context.questions.map(s=><button type="button" key={s} onClick={()=>ask(s)}>{s}</button>)}</div>}
   {error&&<p role="alert" className="workspace-error">{error}</p>}
   {busy&&<p className="assistant-progress" role="status"><LoaderCircle className="assistant-spin" size={18}/> Analisando os números da empresa…</p>}
   {report&&!busy&&<AssistantAnswer key={report.id} report={report} base={base} request={request} compact/>}
   <a className="assistant-dock-link" href="#/workspace/assistant">Abrir a página do assistente <ArrowRight size={15}/></a>
  </aside>}
 </>
}
