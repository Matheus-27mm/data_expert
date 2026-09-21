import {useState} from 'react';
import {ArrowRight, BarChart3, Check, Eye, EyeOff, LockKeyhole, ShieldCheck, TrendingUp} from 'lucide-react';

export function Login({busy,error,notice,onSubmit}:{busy:boolean;error:string;notice:string;onSubmit:(mode:'login'|'signup',email:string,password:string)=>void}){
 const [mode,setMode]=useState<'login'|'signup'>('login');
 const [visible,setVisible]=useState(false);
 return <main className="auth-page">
  <section className="auth-story" aria-label="Conheça o Lucra">
   <a className="auth-brand" href="#/login"><span><BarChart3 size={25}/></span>lucra<span className="auth-dot">.</span></a>
   <div className="auth-story-body"><span className="auth-kicker">CLAREZA PARA DECIDIR MELHOR</span><h1>Seu negócio,<br/>sem pontos<br/><em>cegos.</em></h1><p>Menos números espalhados.<br/>Mais clareza sobre o que fica com você.</p>
    <div className="auth-preview"><div><span>Uma visão do seu negócio</span><TrendingUp size={20}/></div><strong>Controle em dia.</strong><div className="auth-bars" aria-hidden="true">{[28,42,36,55,48,70,65,85,78,100].map((h,i)=><i key={i} style={{height:h+'%'}}/>)}</div><span className="auth-preview-note">Vendas, despesas e resultados no mesmo lugar.</span></div>
   </div><div className="auth-story-footer"><ShieldCheck size={18}/> Cada empresa com seu próprio acesso.</div>
  </section>
  <section className="auth-form-side"><a className="auth-demo" href="#/demo/overview">Explorar demonstração <ArrowRight size={16}/></a>
   <div className="auth-form-wrap"><span className="auth-welcome-icon"><LockKeyhole size={24}/></span><span className="auth-kicker">SEU ESPAÇO DE GESTÃO</span><h2>{mode==='login'?'Bom ter você de volta.':'Um novo começo para sua gestão.'}</h2><p>{mode==='login'?'Entre na sua conta para acompanhar sua empresa.':'Crie sua conta e organize os números do seu negócio.'}</p>
    <form onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);onSubmit(mode,String(data.get('email')),String(data.get('password')))}}>
     <label htmlFor="auth-email">E-mail profissional</label><input id="auth-email" name="email" type="email" autoComplete="email" placeholder="voce@empresa.com.br" required disabled={busy}/>
     <label htmlFor="auth-password">Senha</label><div className="auth-password"><input id="auth-password" name="password" type={visible?'text':'password'} autoComplete={mode==='login'?'current-password':'new-password'} minLength={mode==='signup'?8:undefined} placeholder={mode==='signup'?'Crie uma senha com 8 ou mais caracteres':'Digite sua senha'} required disabled={busy}/><button type="button" aria-label={visible?'Ocultar senha':'Mostrar senha'} aria-pressed={visible} onClick={()=>setVisible(!visible)}>{visible?<EyeOff size={19}/>:<Eye size={19}/>}</button></div>
     {error&&<p className="workspace-error" role="alert">{error}</p>}{notice&&<p className="workspace-notice" role="status">{notice}</p>}
     <button className="auth-submit" disabled={busy}>{busy?'Aguarde…':mode==='login'?'Entrar na minha empresa':'Criar minha conta'}<ArrowRight size={18}/></button>
    </form><p className="auth-switch">{mode==='login'?'Primeira vez por aqui?':'Já tem uma conta?'} <button disabled={busy} onClick={()=>setMode(mode==='login'?'signup':'login')}>{mode==='login'?'Criar conta':'Fazer login'}</button></p>
    <div className="auth-assurance"><Check size={16}/><span>Seus registros ficam vinculados à sua conta.</span></div>
   </div><footer>Lucra · Clareza para decidir melhor.</footer>
  </section>
 </main>
}
