import type {ChangeEvent,KeyboardEvent} from 'react';

export function phoneMask(value:string){
 const digits=value.replace(/\D/g,'');
 const country=value.trim().startsWith('+');
 if(country&&!digits.startsWith('55'))return '+'+digits.slice(0,15);
 const prefix=country?'+55 ':'';
 const local=(country?digits.slice(2):digits.length>11&&digits.startsWith('55')?digits.slice(2):digits).slice(0,11);
 if(!local)return country?'+55':'';
 if(local.length<=2)return prefix+'('+local;
 const split=local.length>10?7:6;
 return prefix+'('+local.slice(0,2)+') '+local.slice(2,split)+(local.length>split?'-'+local.slice(split):'');
}

export function documentMask(value:string){
 const raw=value.replace(/[^a-z0-9]/gi,'').toUpperCase().slice(0,14);
 const cnpj=raw.length>11||/[A-Z]/.test(raw);
 const stops:Record<number,string>=cnpj?{2:'.',5:'.',8:'/',12:'-'}:{3:'.',6:'.',9:'-'};
 return [...raw].map((c,i)=>(stops[i]||'')+c).join('');
}

type Mask=(value:string)=>string;
function update(input:HTMLInputElement,raw:string,position:number,mask:Mask){
 const count=raw.slice(0,position).replace(/[^a-z0-9]/gi,'').length;
 const formatted=mask(raw);
 input.value=formatted;
 let caret=0,seen=0;
 while(caret<formatted.length&&seen<count){if(/[a-z0-9]/i.test(formatted[caret]))seen++;caret++;}
 if(position===raw.length)caret=formatted.length;
 input.setSelectionRange(caret,caret);
}
export function maskedChange(mask:Mask){return (event:ChangeEvent<HTMLInputElement>)=>{
 const input=event.currentTarget;update(input,input.value,input.selectionStart??input.value.length,mask);
};}
// Let Backspace/Delete cross formatting characters instead of getting stuck on them.
export function maskedKeyDown(mask:Mask){return (event:KeyboardEvent<HTMLInputElement>)=>{
 const input=event.currentTarget,start=input.selectionStart,end=input.selectionEnd;
 if(start===null||start!==end||!['Backspace','Delete'].includes(event.key))return;
 let index=event.key==='Backspace'?start-1:start;
 if(index<0||index>=input.value.length||/[a-z0-9]/i.test(input.value[index]))return;
 event.preventDefault();
 const direction=event.key==='Backspace'?-1:1;
 while(index>=0&&index<input.value.length&&!/[a-z0-9]/i.test(input.value[index]))index+=direction;
 if(index<0||index>=input.value.length)return;
 const raw=input.value.slice(0,index)+input.value.slice(index+1);
 update(input,raw,event.key==='Backspace'?index:start,mask);
};}
