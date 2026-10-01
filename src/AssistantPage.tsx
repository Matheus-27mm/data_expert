import React,{useEffect,useRef,useState} from 'react';
import {Sparkles,Send,FileDown,History,ListPlus,Check,Info,LoaderCircle,MessageSquareText} from 'lucide-react';
import type {Requester,Row} from './BusinessPages';
import {MetricGrid,plural} from './ui';
import './assistant.css';

const SUGGESTIONS=[
 'Faça um resumo executivo da empresa neste período.',
 'Quais produtos estão me dando prejuízo e por quê?',
 'Como fica meu caixa nos próximos 30 dias?',
 'Compare este período com o anterior. O que mudou?',
 'O que devo priorizar esta semana para melhorar o resultado?',
 'Minhas despesas estão altas para o que eu vendo?',
];
const PERIODS:Record<string,string>={monthly:'Mensal',weekly:'Semanal',daily:'Diário'};
const TRENDS:Record<string,string>={up:'Em alta',down:'Em queda',flat:'Estável',none:''};
const PRIORITY:Record<string,string>={high:'Prioridade alta',medium:'Prioridade média',low:'Prioridade baixa'};
const STEPS=['Lendo vendas e margens do período…','Conferindo despesas, contas e recebíveis…','Verificando estoque e planos de ação…','Escrevendo a análise…'];
const today=()=>new Date().toLocaleDateString('en-CA');
const when=(v:string)=>new Date(v).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});

export function AssistantPage({base,request}:{base:string;request:Requester}){
 const [overview,setOverview]=useState<Row|null>(null),[report,setReport]=useState<Row|null>(null);
 const [question,setQuestion]=useState(''),[period,setPeriod]=useState('monthly'),[anchor,setAnchor]=useState(today());
 const [busy,setBusy]=useState(false),[elapsed,setElapsed]=useState(0),[error,setError]=useState(''),[notice,setNotice]=useState(''),[planned,setPlanned]=useState<string[]>([]);
 const answerRef=useRef<HTMLElement>(null);
 const load=()=>request(base+'/assistant').then(r=>r.json()).then(setOverview).catch(e=>setError(e.message));
 useEffect(()=>{load()},[base]);
 useEffect(()=>{if(!busy){setElapsed(0);return}const t=setInterval(()=>setElapsed(s=>s+1),1000);return()=>clearInterval(t)},[busy]);
 async function ask(text=question){
  const q=text.trim();if(q.length<3||busy)return;
  setQuestion(q);setBusy(true);setError('');setNotice('');setPlanned([]);
  try{
   // The analysis can take close to a minute; the default 30 s request timeout is too short.
   const r=await request(base+'/assistant',{method:'POST',body:JSON.stringify({question:q,period,anchor}),signal:AbortSignal.timeout(90000)});
   setReport(await r.json());load();setTimeout(()=>answerRef.current?.scrollIntoView({behavior:'smooth',block:'start'}),50);
  }catch(e){setError((e as Error).name==='TimeoutError'?'A análise demorou mais que o esperado. Tente uma pergunta mais específica.':(e as Error).message)}
  finally{setBusy(false)}
 }
 async function open(id:string){setError('');setNotice('');setPlanned([]);try{setReport(await (await request(base+'/assistant/'+id)).json());answerRef.current?.scrollIntoView({behavior:'smooth',block:'start'})}catch(e){setError((e as Error).message)}}
 async function exportPdf(){
  if(!report)return;setError('');
  try{const r=await request(base+'/assistant/'+report.id+'/pdf');const url=URL.createObjectURL(await r.blob());const a=document.createElement('a');a.href=url;a.download=`analise-${report.anchor}.pdf`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setNotice('PDF gerado. Confira a pasta de downloads.')}
  catch(e){setError((e as Error).message)}
 }
 async function plan(action:Row){
  try{await request(base+'/records/action_plans',{method:'POST',body:JSON.stringify({title:action.title.slice(0,160),description:action.description,priority:action.priority})});setPlanned(p=>[...p,action.title]);setNotice('Plano criado. Acompanhe em Planos de ação.')}
  catch(e){setError((e as Error).message)}
 }
 const remaining=overview?Math.max(0,overview.daily_limit-overview.used_today):0;
 const answer=report?.answer;
 if(overview&&!overview.configured)return <section className="assistant-page"><div className="empty-state assistant-off"><Sparkles size={30}/><h2>O assistente ainda não foi ativado</h2><p>Para usar a análise com IA, o administrador do sistema precisa configurar a chave do serviço de IA no servidor. Os dados da empresa continuam disponíveis no Painel de controle e em Relatórios.</p></div></section>;
 return <section className="assistant-page" aria-busy={busy}>
  <div className="assistant-layout">
   <div className="assistant-main">
    <article className="assistant-composer">
     <header><span className="assistant-icon"><Sparkles size={20}/></span><div><h2>Pergunte sobre a sua empresa</h2><p>A IA lê as vendas, margens, despesas, contas, estoque, recebíveis e planos da empresa ativa e responde em linguagem simples.</p></div></header>
     <form onSubmit={e=>{e.preventDefault();ask()}}>
      <label className="assistant-question">Sua pergunta<textarea value={question} disabled={busy} maxLength={1000} rows={3} placeholder="Ex.: Por que meu lucro caiu este mês?" onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();ask()}}}/></label>
      <div className="assistant-controls">
       <label>Período<select value={period} disabled={busy} onChange={e=>setPeriod(e.target.value)}>{Object.entries(PERIODS).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select></label>
       <label>Data de referência<input type="date" value={anchor} disabled={busy} required onChange={e=>{if(e.target.value)setAnchor(e.target.value)}}/></label>
       <button className="primary-button" disabled={busy||question.trim().length<3||remaining===0}>{busy?<LoaderCircle className="assistant-spin" size={17}/>:<Send size={17}/>}{busy?'Analisando…':'Analisar'}</button>
      </div>
     </form>
     <div className="assistant-suggestions" aria-label="Sugestões de perguntas">{SUGGESTIONS.map(s=><button type="button" key={s} disabled={busy||remaining===0} onClick={()=>ask(s)}>{s}</button>)}</div>
     {overview&&<p className="assistant-quota">{remaining===0?'Limite diário de análises atingido para esta empresa. Novas perguntas amanhã.':`${plural(remaining,'análise disponível','análises disponíveis')} hoje · Ctrl + Enter envia a pergunta`}</p>}
    </article>
    {error&&<p role="alert" className="workspace-error">{error}</p>}{notice&&<p role="status" className="workspace-notice">{notice}</p>}
    {busy&&<article className="assistant-progress" role="status"><LoaderCircle className="assistant-spin" size={22}/><div><strong>{STEPS[Math.min(STEPS.length-1,Math.floor(elapsed/6))]}</strong><p>{elapsed}s · uma análise completa leva de 15 a 50 segundos.</p></div></article>}
    {answer&&!busy&&<article className="assistant-answer" ref={answerRef} tabIndex={-1} aria-label="Resposta do assistente">
     <header className="assistant-answer-head"><div><span className="assistant-tag"><Sparkles size={14}/> Análise da IA</span><h2>{answer.title}</h2><p className="assistant-meta">{PERIODS[report!.period]} · referência {report!.anchor.split('-').reverse().join('/')} · {when(report!.created_at)}</p><p className="assistant-asked"><MessageSquareText size={15}/> {report!.question}</p></div>
      <button className="secondary-action" onClick={exportPdf}><FileDown size={17}/>Exportar PDF</button></header>
     <p className="assistant-summary">{answer.summary}</p>
     {answer.highlights.length>0&&<MetricGrid label="Números-chave" items={answer.highlights.map((h:Row)=>({label:h.label,value:h.value,hint:[TRENDS[h.trend],h.note].filter(Boolean).join(' · ')}))}/>}
     {answer.sections.map((s:Row,i:number)=><section className="assistant-section" key={i}><h3>{s.heading}</h3>{s.paragraphs.map((p:string,j:number)=><p key={j}>{p}</p>)}{s.bullets.length>0&&<ul>{s.bullets.map((b:string,j:number)=><li key={j}>{b}</li>)}</ul>}</section>)}
     {answer.actions.length>0&&<section className="assistant-section"><h3>Próximas ações recomendadas</h3><div className="assistant-actions">{answer.actions.map((a:Row)=><article key={a.title} className={'assistant-action is-'+a.priority}><span>{PRIORITY[a.priority]}</span><strong>{a.title}</strong><p>{a.description}</p><button disabled={planned.includes(a.title)} onClick={()=>plan(a)}>{planned.includes(a.title)?<><Check size={15}/>Plano criado</>:<><ListPlus size={15}/>Criar plano de ação</>}</button></article>)}</div></section>}
     {answer.caveats.length>0&&<aside className="assistant-caveats"><Info size={18}/><div><strong>Limitações dos dados</strong><ul>{answer.caveats.map((c:string,i:number)=><li key={i}>{c}</li>)}</ul></div></aside>}
     <p className="assistant-disclaimer">Análise gerada por inteligência artificial a partir dos registros da empresa. Confira os números antes de decidir; não representa saldo bancário nem apuração fiscal.</p>
    </article>}
    {!answer&&!busy&&overview&&<div className="empty-state"><Sparkles size={28}/><h3>Sua primeira análise começa com uma pergunta</h3><p>Escolha uma sugestão acima ou escreva com suas palavras. A resposta pode ser exportada em PDF e virar planos de ação.</p></div>}
   </div>
   <aside className="assistant-history" aria-label="Análises anteriores"><h2><History size={18}/> Análises anteriores</h2>
    {!overview?<p role="status">Carregando…</p>:!overview.history.length?<p className="muted">As análises geradas ficam salvas aqui.</p>:<ol>{overview.history.map((h:Row)=><li key={h.id}><button aria-current={report?.id===h.id?'true':undefined} onClick={()=>open(h.id)}><strong>{h.title||h.question}</strong><small>{when(h.created_at)} · {PERIODS[h.period]}</small></button></li>)}</ol>}
   </aside>
  </div>
 </section>
}
