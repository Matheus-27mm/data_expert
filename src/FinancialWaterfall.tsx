import React from 'react';
const brl=(v:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(v/100);
export function DynamicWaterfall({totals}:{totals:Record<string,number>}){
 const steps=[['Receita',totals.revenue],['CMV',-totals.cmv],['Impostos',-totals.tax],['Cartão',-totals.card],['Comissões',-totals.commission],['Despesas',-(totals.expenses||0)],['Devoluções',-(totals.refunds||0)],['CMV recuperado',totals.cost_recovered||0]] as [string,number][];
 let current=0;const bars=steps.map(([label,value])=>{const before=current;current+=value;return {label,value,before,after:current}});bars.push({label:'Resultado',value:current,before:0,after:current});
 const low=Math.min(0,...bars.flatMap(b=>[b.before,b.after])),high=Math.max(1,...bars.flatMap(b=>[b.before,b.after]));const y=(v:number)=>190-(v-low)/(high-low)*140;
 return <div className="dynamic-waterfall" tabIndex={0} role="region" aria-label="Gráfico de formação do resultado"><svg viewBox="0 0 810 260" role="img" aria-label={'Cascata do período: '+bars.map(b=>b.label+' '+brl(b.value)).join('; ')}><line x1="10" x2="800" y1={y(0)} y2={y(0)} stroke="#b8c6be"/>{bars.map((b,i)=><g key={b.label}><rect x={12+i*89} y={Math.min(y(b.before),y(b.after))} width="60" height={Math.max(1,Math.abs(y(b.before)-y(b.after)))} rx="3" fill={b.value<0?'#bb6655':'#2a7050'}/><text x={42+i*89} y={Math.min(y(b.before),y(b.after))-9} textAnchor="middle" fontSize="10" fill="#264535">{brl(b.value)}</text><text x={42+i*89} y="222" textAnchor="middle" fontSize="9" fill="#4b6656">{b.label}</text></g>)}</svg></div>
}
