import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('login, settings and logout work across desktop and mobile',async({page})=>{
 let signedIn=false;
 let rejectOrigin=true;
 const identity={user:{id:'owner-a',name:'Ana',email:'ana@example.test',emailVerified:true,createdAt:new Date().toISOString(),updatedAt:new Date().toISOString()},session:{id:'session-a',userId:'owner-a',token:'test-token',expiresAt:new Date(Date.now()+3600000).toISOString()}};
 await page.route('**/api/config',r=>r.fulfill({json:{configured:true,neon_auth_url:'https://auth.example.test/auth'}}));
 await page.route('https://auth.example.test/**',async r=>{
  const path=new URL(r.request().url()).pathname;
  if(path.endsWith('/sign-in/email')&&rejectOrigin){rejectOrigin=false;await r.fulfill({status:403,json:{code:'INVALID_ORIGIN',message:'Invalid origin'}});return;}
  if(path.endsWith('/sign-in/email'))signedIn=true;
  if(path.endsWith('/sign-out'))signedIn=false;
  await r.fulfill({json:path.endsWith('/token')?{token:'test-token'}:signedIn?identity:null});
 });
 await page.route('**/api/workspace/**',r=>r.fulfill({json:r.request().url().endsWith('/companies')?[{id:'store-a',name:'Loja da Ana'}]:{company:'Loja da Ana',start:'2026-09-01',end:'2026-09-30',totals:{revenue:0,cmv:0,tax:0,card:0,commission:0,net:0,expenses:0,refunds:0,cost_recovered:0,operating:0},products:[]}}));
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Bom ter você de volta.'})).toBeVisible();
 const background=page.locator('.auth-video-backdrop video');
 await expect.poll(()=>background.evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThanOrEqual(2);
 await expect.poll(()=>background.evaluate((v:HTMLVideoElement)=>!v.paused)).toBe(true);
 expect(await background.evaluate((v:HTMLVideoElement)=>v.muted&&v.loop&&v.playsInline)).toBe(true);
 await page.getByRole('button',{name:'Pausar vídeo de fundo'}).click();
 await expect.poll(()=>background.evaluate((v:HTMLVideoElement)=>v.paused)).toBe(true);
 await background.evaluate((v:HTMLVideoElement)=>new Promise<void>(resolve=>{v.addEventListener('seeked',()=>resolve(),{once:true});v.currentTime=3}));
 for(const width of [360,768,1440]){
  await page.setViewportSize({width,height:900});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 }
 await page.screenshot({path:'output/login-desktop.png',fullPage:true});
 expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze()).violations).toEqual([]);
 await page.getByLabel('E-mail profissional').fill('ana@example.test');
 await page.getByLabel('Senha',{exact:true}).fill('test-password');
 await page.getByRole('button',{name:'Mostrar senha'}).click();
 await expect(page.getByLabel('Senha',{exact:true})).toHaveAttribute('type','text');
 await page.getByRole('button',{name:'Ocultar senha'}).click();
 await page.getByRole('button',{name:'Entrar na minha empresa'}).click();
 await expect(page.getByRole('alert')).toContainText('Este endereço ainda não está autorizado');
 await page.getByRole('button',{name:'Entrar na minha empresa'}).click();
 await expect(page.getByRole('heading',{name:'Visão geral',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Configurações',exact:true}).click();
 await expect(page.getByLabel('E-mail da conta')).toHaveValue('ana@example.test');
 await expect(page.getByRole('link',{name:'Configurar taxas e parcelamento'})).toHaveAttribute('href','#/workspace/payment_terms');
 await page.screenshot({path:'output/settings-desktop.png',fullPage:true});
 await page.setViewportSize({width:360,height:800});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze()).violations).toEqual([]);
 await page.getByRole('button',{name:'Abrir navegação'}).click();
 await expect(page.getByRole('navigation',{name:'Área da empresa'})).toBeVisible();
 await page.locator('.workspace-signout').click();
 await expect(page.getByRole('heading',{name:'Bom ter você de volta.'})).toBeVisible();
 await expect(page.getByLabel('Senha',{exact:true})).toHaveValue('');
 await page.screenshot({path:'output/login-mobile.png',fullPage:true});
 await page.reload();
 await expect(page.getByRole('heading',{name:'Bom ter você de volta.'})).toBeVisible();
 await page.emulateMedia({reducedMotion:'reduce'});
 await expect.poll(()=>background.evaluate((v:HTMLVideoElement)=>v.paused)).toBe(true);
 await page.getByRole('button',{name:'Criar conta',exact:true}).click();
 await expect(page.getByLabel('Senha',{exact:true})).toHaveAttribute('autocomplete','new-password');
});
