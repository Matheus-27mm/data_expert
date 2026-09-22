import {useEffect, useRef, useState} from 'react';
import financeVideo from '../finance.mp4';
import {ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck, Mail, LoaderCircle, Pause, Play} from 'lucide-react';

export function Login({busy,error,notice,onSubmit}:{busy:boolean;error:string;notice:string;onSubmit:(mode:'login'|'signup',email:string,password:string)=>void}){
 const [mode,setMode]=useState<'login'|'signup'>('login');
 const [visible,setVisible]=useState(false);
 const video=useRef<HTMLVideoElement>(null);
 const [paused,setPaused]=useState(false);
 const [videoAvailable,setVideoAvailable]=useState(true);
 useEffect(()=>{
  const preference=window.matchMedia('(prefers-reduced-motion: reduce)');
  const sync=()=>{if(preference.matches){video.current?.pause();setPaused(true)}else{video.current?.play().catch(()=>setPaused(true))}};
  sync();preference.addEventListener('change',sync);return()=>preference.removeEventListener('change',sync);
 },[]);
 function toggleVideo(){if(!video.current)return;if(video.current.paused){video.current.play().catch(()=>setPaused(true))}else video.current.pause()}
 return <main className="auth-page auth-video-page">
  <div className="auth-video-backdrop" aria-hidden="true"><video ref={video} src={financeVideo} poster="/media/finance-poster.jpg" muted loop playsInline preload="metadata" tabIndex={-1} onPlay={()=>setPaused(false)} onPause={()=>setPaused(true)} onError={()=>{setVideoAvailable(false);setPaused(true)}}/><div className="auth-video-shade"/></div>
  <section className="auth-form-side" aria-label="Acesso ao Lucra">
   <div className="auth-form-wrap">
    <a className="auth-brand" href="#/login" aria-label="Lucra — início"><img className="lucra-logo" src="/brand/lucra-light.svg" width="157" height="35" alt="Lucra"/></a>
    <h1>{mode==='login'?'Bom ter você de volta.':'Crie sua conta.'}</h1><p>{mode==='login'?'Clareza para o próximo passo da sua empresa.':'Organize os números do seu negócio.'}</p>
    <form onSubmit={e=>{e.preventDefault();const data=new FormData(e.currentTarget);onSubmit(mode,String(data.get('email')),String(data.get('password')))}}>
     <label htmlFor="auth-email">E-mail profissional</label><div className="auth-email-field"><Mail size={18} aria-hidden="true"/><input id="auth-email" name="email" type="email" autoComplete="email" placeholder="voce@empresa.com.br" required disabled={busy}/></div>
     <label htmlFor="auth-password">Senha</label><div className="auth-password"><LockKeyhole className="auth-input-icon" size={18} aria-hidden="true"/><input id="auth-password" name="password" type={visible?'text':'password'} autoComplete={mode==='login'?'current-password':'new-password'} minLength={mode==='signup'?8:undefined} placeholder={mode==='signup'?'Crie uma senha com 8 ou mais caracteres':'Digite sua senha'} required disabled={busy}/><button type="button" aria-label={visible?'Ocultar senha':'Mostrar senha'} aria-pressed={visible} onClick={()=>setVisible(!visible)}>{visible?<EyeOff size={19}/>:<Eye size={19}/>}</button></div>
     {error&&<p className="workspace-error" role="alert">{error}</p>}{notice&&<p className="workspace-notice" role="status">{notice}</p>}
     <button className="auth-submit" disabled={busy}>{busy?'Aguarde…':mode==='login'?'Entrar na minha empresa':'Criar minha conta'}{busy?<LoaderCircle className="auth-spinner" size={18}/>:<ArrowRight size={18}/>}</button>
    </form><p className="auth-switch">{mode==='login'?'Primeira vez por aqui?':'Já tem uma conta?'} <button disabled={busy} onClick={()=>setMode(mode==='login'?'signup':'login')}>{mode==='login'?'Criar conta':'Fazer login'}</button></p>
    <div className="auth-assurance"><ShieldCheck size={17}/><span>Acesso individual. Dados da sua empresa.</span></div>
    <a className="auth-demo" href="#/demo/overview">Explorar demonstração <ArrowRight size={13}/></a>
   </div>
  </section>
  {videoAvailable&&<button className="auth-video-control" type="button" onClick={toggleVideo} aria-label={paused?'Reproduzir vídeo de fundo':'Pausar vídeo de fundo'}>{paused?<Play size={15}/>:<Pause size={15}/>}</button>}
 </main>
}
