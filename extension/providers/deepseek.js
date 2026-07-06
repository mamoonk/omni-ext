const ZSProvider={
_q:(s)=>document.querySelector(s),
_qs:()=>document.querySelector('[data-testid="chat-input"] textarea, #chat-input textarea, textarea[placeholder*="message"]'),
_qb:()=>document.querySelector('[data-testid="send-button"], button[aria-label="Send"]'),
send(t){
 const i=this._qs();if(!i)return;
 i.focus();document.execCommand("insertText",false,t);
 const b=this._qb();if(b)setTimeout(()=>b.click(),100);
},
};
