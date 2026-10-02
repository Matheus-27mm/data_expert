import React,{useEffect,useRef,useState} from 'react';
import {Sparkles,Send,History,LoaderCircle} from 'lucide-react';
import type {Requester,Row} from './BusinessPages';
import {AssistantAnswer,PERIODS,when,today} from './AssistantAnswer';
import './assistant.css';

const SUGGESTIONS=[
 'Faça um resumo executivo da empresa neste período.',
 'Quais produtos estão me dando prejuízo e por quê?',
 'Como fica meu caixa nos próximos 30 dias?',
 'Compare este período com o anterior. O que mudou?',
 'O que devo priorizar esta semana para melhorar o resultado?',
 'Minhas despesas estão altas para o que eu vendo?',
];

/** Dedicated assistant page. `reportId` opens a stored analysis (link from the floating assistant). */
export function AssistantPage({base,request,reportId}:{base:string;request:Requester;reportId?:string}){
 const [overview,setOverview]=useState<Row|null>(null),[report,setReport]=useState<Row|null>(null);
 const [question,setQuestion]=useState(''),[period,setPeriod]=useState('monthly'),[anchor,setAnchor]=useState(today());
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const answerRef=useRef<HTMLDivElement>(null);
 const load=()=>request(base+'/assistant').then(r=>r.json()).then(setOverview).catch(e=>setError(e.message));
 const reveal=()=>setTimeout(()=>answerRef.current?.scrollIntoView({behavior:'smooth',block:'start'}),50);
 useEffect(()=>{load()},[base]);
 useEffect(()=>{if(reportId)open(reportId)},[base,reportId]);
 async function ask(text=question){
  const q=text.trim();if(q.length<3||busy)return;
  setQuestion(q);setBusy(true);setError('');
  try{const saved=await (await request(base+'/assistant',{method:'POST',body:JSON.stringify({question:q,period,anchor})})).json();setReport(saved);history.replaceState(null,'','#/workspace/assistant/'+saved.id);load();reveal()}
  catch(e){setError((e as Error).message)}
  finally{setBusy(false)}
 }
 async function open(id:string){setError('');try{setReport(await (await request(base+'/assistant/'+id)).json());history.replaceState(null,'','#/workspace/assistant/'+id);reveal()}catch(e){setError((e as Error).message)}}
 return <section className="assistant-page" aria-busy={busy}>
  <div className="assistant-layout">
   <div className="assistant-main">
    <article className="assistant-composer">
     <header><span className="assistant-icon"><Sparkles size={20}/></span><div><h2>Pergunte sobre a sua empresa</h2><p>O Sobrevo lê as vendas, margens, despesas, contas, estoque, recebíveis e planos da empresa ativa e responde em linguagem simples. Nenhum dado sai do sistema.</p></div></header>
     <form onSubmit={e=>{e.preventDefault();ask()}}>
      <label className="assistant-question">Sua pergunta<textarea value={question} disabled={busy} maxLength={1000} rows={3} placeholder="Ex.: Por que meu lucro caiu este mês?" onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();ask()}}}/></label>
      <div className="assistant-controls">
       <label>Período<select value={period} disabled={busy} onChange={e=>setPeriod(e.target.value)}>{Object.entries(PERIODS).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label>
       <label>Data de referência<input type="date" value={anchor} disabled={busy} required onChange={e=>{if(e.target.value)setAnchor(e.target.value)}}/></label>
       <button className="primary-button" disabled={busy||question.trim().length<3}>{busy?<LoaderCircle className="assistant-spin" size={17}/>:<Send size={17}/>}{busy?'Analisando…':'Analisar'}</button>
      </div>
     </form>
     <div className="assistant-suggestions" aria-label="Sugestões de perguntas">{SUGGESTIONS.map(s=><button type="button" key={s} disabled={busy} onClick={()=>ask(s)}>{s}</button>)}</div>
     <p className="assistant-quota">Pergunte sobre resumo, produtos e margens, caixa, comparação com o período anterior, despesas, estoque, clientes ou prioridades. Ctrl + Enter envia. O assistente também fica disponível nas outras telas, no botão "Perguntar ao Sobrevo".</p>
    </article>
    {error&&<p role="alert" className="workspace-error">{error}</p>}
    {busy&&<article className="assistant-progress" role="status"><LoaderCircle className="assistant-spin" size={22}/><div><strong>Analisando os números da empresa…</strong></div></article>}
    <div ref={answerRef}>{report&&!busy&&<AssistantAnswer key={report.id} report={report} base={base} request={request}/>}</div>
    {!report&&!busy&&overview&&<div className="empty-state"><Sparkles size={28}/><h3>Sua primeira análise começa com uma pergunta</h3><p>Escolha uma sugestão acima ou escreva com suas palavras. A resposta pode ser exportada em PDF e virar planos de ação.</p></div>}
   </div>
   <aside className="assistant-history" aria-label="Análises anteriores"><h2><History size={18}/> Análises anteriores</h2>
    {!overview?<p role="status">Carregando…</p>:!overview.history.length?<p className="muted">As análises geradas ficam salvas aqui.</p>:<ol>{overview.history.map((h:Row)=><li key={h.id}><button aria-current={report?.id===h.id?'true':undefined} onClick={()=>open(h.id)}><strong>{h.title||h.question}</strong><small>{when(h.created_at)} · {PERIODS[h.period]}</small></button></li>)}</ol>}
   </aside>
  </div>
 </section>
}
