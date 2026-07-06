const ZSProvider={
_q:(s)=>document.querySelector(s),
_qi:()=>document.querySelector('div[contenteditable="true"]'),
_qb:()=>document.querySelector('button[aria-label*="send"], button.send-button'),
send(t){const i=this._qi(),b=this._qb();if(i){i.focus();i.textContent=t;if(b)b.click()}},
};
