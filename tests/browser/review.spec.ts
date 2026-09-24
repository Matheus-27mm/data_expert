import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
const pages=['simulator','dashboard','analysis','products','sales','expenses','adjustments','settlements','reconciliation','payment_terms','imports','integrations','backups','reports','report_schedules','inventory','stock_movements','payables','bills','bill_payments','bank_imports','plans','customers','settings'];
test('presentation review: every workspace page renders with data on desktop and phone',async({page})=>{
 test.setTimeout(240000);
 const runtime:string[]=[];
 page.on('pageerror',e=>runtime.push(e.message));
 await page.route('https://auth.example.test/**',route=>route.fulfill({json:new URL(route.request().url()).pathname.endsWith('/token')?{token:'browser-test-token'}:{user:{id:'review-user',name:'Review',email:'review@example.test',emailVerified:true},session:{id:'review-session',userId:'review-user',token:'opaque',expiresAt:new Date(Date.now()+3600000).toISOString()}}}));
 const headers={Authorization:'Bearer browser-test-token'};
 const created=await page.request.post('/api/workspace/companies',{headers,data:{name:'Empresa de revisão'}});
 expect(created.status()).toBe(201);const company=await created.json();
 await page.addInitScript(cid=>localStorage.setItem('lucra-company:review-user',cid),company.id);
 async function record(table:string,data:object){const r=await page.request.post(`/api/workspace/${company.id}/records/${table}`,{headers,data});expect(r.status()).toBe(201);return r.json()}
 const product=await record('products',{sku:'REVIEW-01',name:'Produto de revisão',category:'Apresentação',unit_cost:10000,unit_price:20000});
 const sale=await record('sales',{external_id:'REVIEW-SALE',sold_on:new Date().toISOString().slice(0,10),product:'Produto de revisão',category:'Apresentação',quantity:1,revenue:20000,cmv:10000,tax:1200,card:1500,commission:500,installments:3});
 await record('expenses',{description:'Despesa de revisão',category:'Operação',incurred_on:new Date().toISOString().slice(0,10),amount:1000});
 await record('stock_movements',{product_id:product.id,occurred_on:'2026-09-01',direction:'in',quantity:3,reference:'REVIEW-IN',description:'Estoque inicial'});
 await record('settlements',{sale_id:sale.id,reference:'REVIEW-PAYMENT',received_on:'2026-09-23',amount:18500});
 await record('customers',{name:'Cliente de revisão',email:'cliente@example.test',phone:'11999990000'});
 await record('action_plans',{title:'Revisar margem',description:'Validar as condições de venda.',priority:'high'});
 const failures:string[]=[];
 for(const area of pages){
  await page.setViewportSize({width:1440,height:960});
  await page.goto('/#/workspace/'+area);
  await expect(page.locator('#workspace-main h1')).toBeVisible();
  await expect(page.getByText('Carregando sua empresa…',{exact:true})).toHaveCount(0);
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
  await expect(page.locator('.workspace-error')).toHaveCount(0);
  for(const width of [1440,820,1180,360]){
   await page.setViewportSize({width,height:960});
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),area+' '+width).toBeTruthy();
   if(width<=1200)expect(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight+1),area+' viewport height '+width).toBeTruthy();
   const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze();
   for(const v of axe.violations)failures.push(area+' '+width+': '+v.id+' '+v.nodes.map(n=>n.target.join(' ')).join(', '));
   if(['sales','payables','inventory','stock_movements','payment_terms','analysis','products','customers','imports','backups','plans','settings'].includes(area))await page.screenshot({path:`output/review/${area}-${width}.png`,fullPage:true});
  }
 }
 await page.setViewportSize({width:1024,height:768});
 await page.goto('/#/workspace/products');
 await page.getByRole('button',{name:'Adicionar produto',exact:true}).click();
 await expect(page.getByRole('dialog')).toBeVisible();
 await expect(page.getByRole('button',{name:'Salvar produto',exact:true})).toBeInViewport();
 await page.screenshot({path:'output/review/product-form-tablet.png'});
 await page.keyboard.press('Escape');
 await expect(page.getByRole('dialog')).not.toBeVisible();
 await page.getByRole('button',{name:'Abrir navegação'}).click();
 await expect(page.getByRole('link',{name:'Clientes',exact:true})).toBeVisible();
 expect(runtime).toEqual([]);expect(failures).toEqual([]);
});
