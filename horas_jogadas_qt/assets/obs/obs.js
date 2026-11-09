"use strict";
(() => {
  const widget=document.getElementById("widget");
  const fragment=new URLSearchParams(location.hash.slice(1));
  let key=fragment.get("key")||"";
  try{if(key)sessionStorage.setItem("horas-obs-key",key);else key=sessionStorage.getItem("horas-obs-key")||"";}catch(_){}
  history.replaceState(null,"",location.pathname);
  let pending=false;
  async function sync(){
    if(pending)return;pending=true;
    const cancel=new AbortController(),timeout=setTimeout(()=>cancel.abort(),2000);
    try{
      const response=await fetch("/state",{headers:{Authorization:"Bearer "+key},signal:cancel.signal,cache:"no-store",credentials:"omit",referrerPolicy:"no-referrer"});
      if(!response.ok)throw Error("unavailable");
      const data=await response.json();
      if(!Number.isSafeInteger(data.seconds)||data.seconds<0||!data.visible)throw Error("unavailable");
      const hours=String(Math.floor(data.seconds/3600)).padStart(2,"0");
      document.getElementById("hours").textContent=hours;
      document.getElementById("minutes").textContent=String(Math.floor(data.seconds/60)%60).padStart(2,"0");
      document.getElementById("seconds").textContent=String(data.seconds%60).padStart(2,"0");
      document.getElementById("name").textContent=data.name||"";
      const english=data.language==="en";document.documentElement.lang=english?"en":"pt-BR";
      ["hours","minutes","seconds"].forEach((id,i)=>document.getElementById(id+"-label").textContent=(english?["HOURS","MINUTES","SECONDS"]:["HORAS","MINUTOS","SEGUNDOS"])[i]);
      widget.className=["arcade","minimal","digital"].includes(data.style)?data.style:"minimal";
      if(/^#[a-f0-9]{6}$/i.test(data.color))document.documentElement.style.setProperty("--ink",data.color);
      widget.style.setProperty("--scale",String(Math.max(1,hours.length/2.7)));
      widget.hidden=false;
    }catch(_){widget.hidden=true;}
    finally{clearTimeout(timeout);pending=false;}
  }
  sync();setInterval(sync,1000);
})();
