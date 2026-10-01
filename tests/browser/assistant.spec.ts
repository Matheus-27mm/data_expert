import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('assistant answers in natural language, creates a plan and exports the analysis as PDF',async({page})=>{
 await page.route('https://auth.example.test/**',route=>route.fulfill({json:route.request().url().endsWith('/token')?{token:'browser-test-token'}:{user:{id:'assistant-user',email:'assistant@example.test'},session:{id:'s',expiresAt:new Date(Date.now()+3600000).toISOString()}}}));
 const company=await(await page.request.post('/api/workspace/companies',{headers:{Authorization:'Bearer browser-test-token'},data:{name:'Loja da IA'}})).json();
 await page.addInitScript(id=>localStorage.setItem('lucra-company:assistant-user',id),company.id);
 await page.setViewportSize({width:1440,height:960});
 await page.goto('/#/workspace/assistant');
 await expect(page.getByRole('heading',{name:'Pergunte sobre a sua empresa'})).toBeVisible();
 await page.getByRole('button',{name:'Faça um resumo executivo da empresa neste período.'}).click();
 const answer=page.getByRole('article',{name:'Resposta do assistente'});
 await expect(answer.getByRole('heading',{name:'Resumo executivo de teste'})).toBeVisible();
 await expect(answer).toContainText('A empresa Loja da IA faturou');
 await expect(page.getByRole('complementary',{name:'Análises anteriores'})).toContainText('Resumo executivo de teste');
 expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa']).analyze()).violations).toEqual([]);
 await page.screenshot({path:'output/review/assistant-1440.png',fullPage:true});
 await answer.getByRole('button',{name:'Criar plano de ação'}).click();
 await expect(answer.getByRole('button',{name:'Plano criado'})).toBeDisabled();
 const download=page.waitForEvent('download');
 await answer.getByRole('button',{name:'Exportar PDF'}).click();
 expect((await download).suggestedFilename()).toMatch(/^analise-.*\.pdf$/);
 await page.setViewportSize({width:360,height:800});
 await page.screenshot({path:'output/review/assistant-360.png',fullPage:true});
 await page.goto('/#/workspace/plans');
 await expect(page.getByText('Revisar preços com margem baixa')).toBeVisible();
});
