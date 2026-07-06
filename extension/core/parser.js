/* Param-value parser for TOOL_CALL: name(key="val", key=123) */
function _av(s){
 if(!s)return{};
 const r={};
 const kv=/(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)'|(\d+(?:\.\d+)?)|true|false)/g;
 let m;
 while((m=kv.exec(s))!==null){
  let v=m[2]??m[3]??m[4];
  if(v==="true")v=true;
  else if(v==="false")v=false;
  else if(m[4]!==undefined)v=parseFloat(m[4]);
  if(v!==undefined)r[m[1]]=v;
 }
 return r;
}

/* Balanced-paren parser that handles ) inside quoted strings.
   Extracts the first TOOL_CALL from text and returns {name, args}.
   Uses char-by-char scanning to track paren depth and skip string literals. */
function _parseToolCall(text){
 const start=/TOOL_CALL:\s*(\w+)\s*\(/;
 start.lastIndex=0;
 const m=start.exec(text);
 if(!m)return null;
 const name=m[1];
 const bodyStart=m.index+m[0].length;
 let depth=1;
 let inStr=null; // null|'"'|"'"
 let esc=false;
 let i=bodyStart;
 while(i<text.length&&depth>0){
  const ch=text[i];
  if(esc){esc=false;i++;continue}
  if(ch==='\\'&&inStr){esc=true;i++;continue}
  if(ch==='"'||ch==="'"){if(!inStr)inStr=ch;else if(inStr===ch)inStr=null;i++;continue}
  if(!inStr){
   if(ch==='(')depth++;
   else if(ch===')')depth--;
  }
  i++;
 }
 if(depth!==0)return null;
 const argsStr=text.slice(bodyStart,i-1);
 return{name:name,args:_av(argsStr)};
}

const ZSParse={
 parse:_parseToolCall,
 hasToolCall:(t)=>/TOOL_CALL:\s*\w+\s*\(/.test(t),
};var ZSParse=ZSParse;
