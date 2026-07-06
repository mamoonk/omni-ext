const ZSProvider={
_q:(s)=>document.querySelector(s),
_qi:()=>document.querySelector('[contenteditable="true"], textarea, .input-area'),
_qb:()=>document.querySelector('button[type="submit"], .send-btn, [class*="send"]'),
send(t){const i=this._qi(),b=this._qb();if(i){i.focus();i.textContent=t;if(b)b.click()}},
};
