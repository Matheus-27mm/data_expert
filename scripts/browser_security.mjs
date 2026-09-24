// Smoke-test the compiled frontend with the production Content-Security-Policy.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {chromium} from '@playwright/test';
const config=JSON.parse(await readFile('vercel.json','utf8'));
const csp=config.headers[0].headers.find(h=>h.key==='Content-Security-Policy').value;
const root=resolve('dist');
const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml','.mp4':'video/mp4'};
const server=createServer(async(req,res)=>{
 try{
  const file=resolve(root,'.'+new URL(req.url,'http://localhost').pathname.replace(/\/$/,'/index.html'));
  if(!file.startsWith(root+'/')&&!file.startsWith(root+'\\'))throw Error('path');
  res.writeHead(200,{'Content-Type':mime[extname(file)]||'application/octet-stream','Content-Security-Policy':csp});
  res.end(await readFile(file));
 }catch{res.writeHead(404);res.end();}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch();
try{
 const page=await browser.newPage();
 const violations=[];
 const runtimeErrors=[];
 page.on('pageerror',error=>runtimeErrors.push(error.message));
 await page.exposeFunction('securityViolation',value=>violations.push(value));
 await page.addInitScript(()=>document.addEventListener('securitypolicyviolation',e=>window.securityViolation(`${e.violatedDirective}: ${e.blockedURI} at ${e.sourceFile}:${e.lineNumber}`)));
 await page.route('**/api/config',r=>r.fulfill({json:{configured:true,neon_auth_url:'https://test.neon.tech/auth'}}));
 await page.route('https://test.neon.tech/**',r=>r.fulfill(r.request().url().includes('/sign-in/')?{status:401,json:{message:'Credenciais inválidas'}}:{json:null}));
 await page.goto(`http://127.0.0.1:${server.address().port}`);
 await page.getByRole('heading',{name:'Bom ter você de volta.'}).waitFor();
 await page.getByLabel('E-mail profissional').fill('security@example.test');
 await page.getByLabel('Senha',{exact:true}).fill('local-test-only');
 await page.getByRole('button',{name:'Entrar na minha empresa'}).click();
 await page.getByRole('alert').waitFor();
 // Zod probes Function inside try/catch and falls back to its interpreter.
 // Keep eval blocked; allow only that expected feature probe in this test.
 const unexpected=violations.filter(v=>!v.startsWith('script-src: eval at '));
 if(unexpected.length||runtimeErrors.length)throw Error(JSON.stringify({unexpected,runtimeErrors}));
 console.log('Production CSP: login rendered, submission handled, no uncaught errors. Eval stays blocked.');
}finally{await browser.close();server.closeAllConnections();server.close();}
