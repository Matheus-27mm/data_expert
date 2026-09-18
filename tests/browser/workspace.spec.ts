import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('demo adapts to phone and desktop, changes period and exports PDF',async({page})=>{
 await page.goto('/#/demo/overview');
 await expect(page.getByText('R$ 150.000,00',{exact:true}).first()).toBeVisible();
 for(const width of [360,768,1440]){
  await page.setViewportSize({width,height:1000});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 }
 const download=page.waitForEvent('download');
 await page.getByRole('button',{name:'Exportar relatório',exact:true}).click();
 expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
 await page.getByRole('button',{name:'Diário',exact:true}).click();
 await expect(page.getByText('R$ 150.000,00',{exact:true})).toHaveCount(0);
});

test('workspace persists company, stock, bills, CSV and PDF; accessible on mobile',async({page})=>{
 test.setTimeout(60000);
 await page.route('https://auth.example.test/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  const body=path.endsWith('/token')?{token:'browser-test-token'}:{
   user:{id:'browser-user',name:'Browser',email:'browser@example.test',emailVerified:true,createdAt:new Date().toISOString(),updatedAt:new Date().toISOString()},
   session:{id:'browser-session',userId:'browser-user',token:'browser-test-token',expiresAt:new Date(Date.now()+3600000).toISOString()}
  };
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.goto('/#/workspace/dashboard');
 await page.getByLabel('Nome da empresa').fill('Empresa de teste navegador');
 await page.getByRole('button',{name:'Criar empresa',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Da receita ao resultado'})).toBeVisible();
 await page.getByRole('link',{name:'Produtos',exact:true}).click();
 await page.getByLabel('SKU',{exact:true}).fill('SKU-001');
 await page.getByLabel('Produto',{exact:true}).fill('Caneca');
 await page.getByLabel('Categoria',{exact:true}).fill('Casa');
 await page.getByLabel('Custo unitário (R$)').fill('10');
 await page.getByLabel('Preço unitário (R$)').fill('20');
 await page.getByRole('button',{name:'Cadastrar',exact:true}).click();
 await expect(page.getByRole('cell',{name:'Caneca',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Movimentar estoque',exact:true}).click();
 await page.getByRole('combobox',{name:'Produto',exact:true}).selectOption({label:'SKU-001 · Caneca'});
 await page.getByLabel('Quantidade',{exact:true}).fill('5');
 await page.getByLabel('Referência única').fill('EST-001');
 await page.getByLabel('Motivo').fill('Saldo inicial');
 await page.getByRole('button',{name:'Cadastrar',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'Registro salvo'})).toBeVisible();
 await page.getByRole('link',{name:'Estoque',exact:true}).click();
 await expect(page.getByRole('cell',{name:'5',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Cadastrar conta',exact:true}).click();
 await page.getByLabel('Referência única').fill('CONTA-001');
 await page.getByLabel('Fornecedor').fill('Imobiliária');
 await page.getByLabel('Descrição',{exact:true}).fill('Aluguel');
 await page.getByLabel('Categoria',{exact:true}).fill('Fixa');
 await page.getByLabel('Valor (R$)',{exact:true}).fill('100');
 await page.getByRole('button',{name:'Cadastrar',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'Registro salvo'})).toBeVisible();
 await page.getByRole('link',{name:'Contas a pagar',exact:true}).click();
 await expect(page.getByRole('cell',{name:'Imobiliária',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'Importar CSV',exact:true}).click();
 const csv='external_id,sold_on,product,category,quantity,revenue,cmv,tax,card,commission,installments\nVENDA-001,2026-09-18,Caneca,Casa,1,20.00,10.00,1.00,0.50,1.00,1\n';
 await page.getByLabel('Arquivo CSV').setInputFiles({name:'vendas.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
 await page.getByRole('button',{name:'Validar e visualizar'}).click();
 await page.getByRole('button',{name:'Confirmar importação'}).click();
 await expect(page.getByRole('status').filter({hasText:'1 vendas importadas'})).toBeVisible();
 await page.getByRole('link',{name:'Relatórios',exact:true}).click();
 const download=page.waitForEvent('download');
 await page.getByRole('button',{name:'Gerar e salvar PDF'}).click();
 expect((await download).suggestedFilename()).toMatch(/\.pdf$/);
 await page.reload();
 await expect(page.getByRole('button',{name:'Baixar PDF',exact:true})).toBeVisible();
 await page.setViewportSize({width:360,height:800});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
 expect(results.violations).toEqual([]);
});
