import {test,expect,type Page} from '@playwright/test';

// Unsigned JWT-shaped token accepted only by tests/e2e_api.py.
const jwt=(secondsLeft:number)=>'e2e.'+Buffer.from(JSON.stringify({sub:'loading-user',exp:Math.floor(Date.now()/1000)+secondsLeft})).toString('base64url')+'.sig';

async function simulatorWithFailingCatalog(page:Page,token:string){
 const counter={tokens:0,fail:true};
 await page.route('https://auth.example.test/**',async route=>{
  if(route.request().url().endsWith('/token')){
   counter.tokens++;
   await new Promise(resolve=>setTimeout(resolve,100));
   await route.fulfill({json:{token}});
  }else await route.fulfill({json:{user:{id:'loading-user',email:'loading@example.test'},session:{id:'loading-session',expiresAt:new Date(Date.now()+3600000).toISOString()}}});
 });
 const company=await(await page.request.post('/api/workspace/companies',{headers:{Authorization:'Bearer browser-test-token'},data:{name:'Carregamento teste'}})).json();
 await page.addInitScript(id=>localStorage.setItem('lucra-company:loading-user',id),company.id);
 await page.route('**/records/products',route=>counter.fail?route.fulfill({status:503,json:{detail:'Teste de nova tentativa'}}):route.continue());
 await page.goto('/#/workspace/simulator');
 await expect(page.getByRole('alert')).toContainText('Teste de nova tentativa');
 return counter;
}

test('a token near expiry is never reused; parallel requests still share one lookup',async({page})=>{
 const counter=await simulatorWithFailingCatalog(page,jwt(30));
 expect(counter.tokens).toBe(2); // Company list, then one lookup shared by both catalog requests.
 counter.fail=false;
 await page.getByRole('button',{name:'Tentar novamente'}).click();
 await expect(page.getByRole('heading',{name:'Cadastre seu primeiro produto'})).toBeVisible();
 expect(counter.tokens).toBe(3); // Inside the expiry margin: fetched again.
});

test('a valid token is reused across requests until close to expiry',async({page})=>{
 const counter=await simulatorWithFailingCatalog(page,jwt(3600));
 expect(counter.tokens).toBe(1);
 counter.fail=false;
 await page.getByRole('button',{name:'Tentar novamente'}).click();
 await expect(page.getByRole('heading',{name:'Cadastre seu primeiro produto'})).toBeVisible();
 expect(counter.tokens).toBe(1); // A 503 is not an auth failure: no new lookup.
});
