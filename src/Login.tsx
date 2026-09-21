import {useState} from 'react';
import {ArrowRight, BarChart3, Eye, EyeOff, LockKeyhole, ShieldCheck, TrendingUp, Mail, CircleCheck, LoaderCircle} from 'lucide-react';

export function Login({busy,error,notice,onSubmit}:{busy:boolean;error:string;notice:string;onSubmit:(mode:'login'|'signup',email:string,password:string)=>void}){
 const [mode,setMode]=useState<'login'|'signup'>('login');
 const [visible,setVisible]=useState(false);
 return <main className="auth-page">
  <section className="auth-story" aria-label="Conheça o Lucra">
   <a className="auth-brand" href="#/login"><span><BarChart3 size={25}/></span>lucra<span className="auth-dot">.</span></a>
   <div className="auth-orbits" aria-hidden="true"><i/><i/><i/></div>
   <div className="auth-story-body"><span className="auth-kicker"><span/> INTELIGÊNCIA PARA O SEU NEGÓCIO</span><h1>O próximo passo<br/>começa com<br/><em>clareza.</em></h1><p>Entenda seus resultados. Encontre oportunidades.<br/>Decida com a tranquilidade de quem sabe.</p>
    <div className="auth-preview">
     <div className="auth-preview-top"><span className="auth-preview-symbol"><BarChart3 size={17}/></span><span>Seu negócio em perspectiva<small>VISÃO FINANCEIRA</small></span><span className="auth-preview-live"><span/> Lucra</span></div>
     <div className="auth-preview-heading"><div><span>Do faturamento ao resultado.</span><strong>Cada detalhe conta.</strong></div><TrendingUp size={24}/></div>
     <div className="auth-chart" aria-hidden="true"><svg viewBox="0 0 420 100" fill="none"><defs><linearGradient id="auth-chart-fill" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#c6d8a7" stopOpacity=".24"/><stop offset="1" stopColor="#c6d8a7" stopOpacity="0"/></linearGradient></defs><path d="M0 25H420M0 55H420M0 85H420" stroke="#ffffff" strokeOpacity=".08" strokeDasharray="3 5"/><path d="M0 88C30 86 40 61 70 68S116 73 143 52 178 71 213 43 254 51 287 30 321 39 352 18 397 28 420 5V100H0Z" fill="url(#auth-chart-fill)"/><path d="M0 88C30 86 40 61 70 68S116 73 143 52 178 71 213 43 254 51 287 30 321 39 352 18 397 28 420 5" stroke="#ccdfb1" strokeWidth="2.5"/></svg></div>
     <div className="auth-preview-bottom"><span><CircleCheck size={14}/> Vendas</span><span><CircleCheck size={14}/> Despesas</span><span><CircleCheck size={14}/> Resultados</span></div>
    </div>
   </div><div className="auth-story-footer"><span>Menos incerteza. Mais direção.</span><span>GESTÃO COM CLAREZA <ArrowRight size={14}/></span></div>
  </section>
  <section className="auth-form-side"><a className="auth-demo" href="#/demo/overview">Conheça o Lucra <span>Explorar demonstração <ArrowRight size={14}/></span></a>
   <div className="auth-form-wrap"><span className="auth-welcome-icon"><LockKeyhole size={22}/></span><span className="auth-kicker">SEU ESPAÇO DE GESTÃO</span><h2>{mode==='login'?'Bom ter você de volta.':'Um novo começo para sua gestão.'}</h2><p>{mode==='login'?'Entre na sua conta para acompanhar sua empresa.':'Crie sua conta e organize os números do seu negócio.'}</p>
    <form onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);onSubmit(mode,String(data.get('email')),String(data.get('password')))}}>
     <label htmlFor="auth-email">E-mail profissional</label><div className="auth-email-field"><Mail size={18} aria-hidden="true"/><input id="auth-email" name="email" type="email" autoComplete="email" placeholder="voce@empresa.com.br" required disabled={busy}/></div>
     <label htmlFor="auth-password">Senha</label><div className="auth-password"><LockKeyhole className="auth-input-icon" size={18} aria-hidden="true"/><input id="auth-password" name="password" type={visible?'text':'password'} autoComplete={mode==='login'?'current-password':'new-password'} minLength={mode==='signup'?8:undefined} placeholder={mode==='signup'?'Crie uma senha com 8 ou mais caracteres':'Digite sua senha'} required disabled={busy}/><button type="button" aria-label={visible?'Ocultar senha':'Mostrar senha'} aria-pressed={visible} onClick={()=>setVisible(!visible)}>{visible?<EyeOff size={19}/>:<Eye size={19}/>}</button></div>
     {error&&<p className="workspace-error" role="alert">{error}</p>}{notice&&<p className="workspace-notice" role="status">{notice}</p>}
     <button className="auth-submit" disabled={busy}>{busy?'Aguarde…':mode==='login'?'Entrar na minha empresa':'Criar minha conta'}{busy?<LoaderCircle className="auth-spinner" size={18}/>:<ArrowRight size={18}/>}</button>
    </form><p className="auth-switch">{mode==='login'?'Primeira vez por aqui?':'Já tem uma conta?'} <button disabled={busy} onClick={()=>setMode(mode==='login'?'signup':'login')}>{mode==='login'?'Criar conta':'Fazer login'}</button></p>
    <div className="auth-assurance"><ShieldCheck size={17}/><span>Acesso individual. Dados da sua empresa.</span></div>
   </div><footer><span>© {new Date().getFullYear()} Lucra</span><span>Clareza para decidir melhor.</span></footer>
  </section>
 </main>
}
