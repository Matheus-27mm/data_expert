import React from 'react';
import type {LucideIcon} from 'lucide-react';
// Styles: src/ui.css, imported last by Workspace.tsx so it wins the cascade.

/** Shared building blocks. New screens use these instead of page-specific card markup. */
export type Metric={label:string;value:React.ReactNode;hint?:string;icon?:LucideIcon;tone?:'highlight'|'alert'};

export function MetricGrid({items,label}:{items:Metric[];label?:string}){
 return <div className="ui-metric-grid" role="list" aria-label={label} style={{'--metric-columns':Math.min(items.length,4)} as React.CSSProperties}>
  {items.map(({label,value,hint,icon:Icon,tone})=><article role="listitem" key={label} className={'ui-metric-card'+(tone?' is-'+tone:'')}>
   <span className="ui-metric-label">{Icon&&<Icon size={16} aria-hidden="true"/>}{label}</span>
   <strong className="ui-metric-value">{value}</strong>
   {hint&&<small className="ui-metric-hint">{hint}</small>}
  </article>)}
 </div>
}

/** "1 resultado" / "3 resultados". */
export const plural=(n:number,one:string,many:string)=>`${n} ${n===1?one:many}`;
