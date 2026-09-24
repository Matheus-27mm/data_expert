import {test,expect} from '@playwright/test';

test('parallel page requests share token lookup and retry obtains a fresh token',async({page})=>{
 let tokens=0;
 await page.route('https://auth.example.test/**',async route=>{
  if(route.request().url().endsWith('/token')){
   tokens++;
   await new Promise(resolve=>setTimeout(resolve,100));
   await route.fulfill({json:{token:'browser-test-token'}});
  }else await route.fulfill({json:{user:{id:'loading-user',email:'loading@example.test'},session:{id:'loading-session',expiresAt:new Date(Date.now()+3600000).toISOString()}}});
 });
 const company=await(await page.request.post('/api/workspace/companies',{headers:{Authorization:'Bearer browser-test-token'},data:{name:'Carregamento teste'}})).json();
 await page.addInitScript(id=>localStorage.setItem('lucra-company:loading-user',id),company.id);
 let fail=true;
 await page.route('**/records/products',route=>fail?route.fulfill({status:503,json:{detail:'Teste de nova tentativa'}}):route.continue());
 await page.goto('/#/workspace/simulator');
 await expect(page.getByRole('alert')).toContainText('Teste de nova tentativa');
 expect(tokens).toBe(2); // Company list, then one lookup shared by both catalog requests.
 fail=false;
 await page.getByRole('button',{name:'Tentar novamente'}).click();
 await expect(page.getByRole('heading',{name:'Cadastre seu primeiro produto'})).toBeVisible();
 expect(tokens).toBe(3); // No persistent token cache after completion or failure.
});
