const ZSParse={
_pt:/TOOL_CALL:\s*(\w+)\s*\(([\s\S]*?)\)/g,
_av:(s)=>{if(!s)return{};const r={};let m;const kv=/(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)'|(\d+(?:\.\d+)?)|true|false)/g;while((m=kv.exec(s))!==null){let v=m[2]??m[3]??m[4];if(v==="true")v=true;else if(v==="false")v=false;else if(m[4]!==undefined)v=parseFloat(m[4]);r[m[1]]=v}return r},
parse:(t)=>{ZS._pt.lastIndex=0;const m=ZS._pt.exec(t);if(!m)return null;return{name:m[1],args:ZS._av(m[2])}},
hasToolCall:(t)=>/TOOL_CALL:\s*\w+\s*\(/.test(t),
};var ZSParse=ZSParse;
