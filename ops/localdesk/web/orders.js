/* Match-level visual audit, separate from trading logic. */
var orderState = {model:null,scope:null,page:1,query:"",result:"all",payload:null};
var orderFetchSerial=0,orderTimer=null,modalOpen=false;
var orderSummaryRender=renderScores;

function orderN(x, places){return x===null||x===undefined||Number.isNaN(Number(x))?"未存":Number(x).toFixed(places)}
function orderWater(x){if(x===null||x===undefined)return "未保存";return Number(x).toFixed(3).replace(/0$/,"").replace(/\.0$/,".00")}
function orderLine(x){if(x===null||x===undefined)return "—";var v=Number(x);return v>0?"+"+v.toString():v.toString()}
function orderTime(x){return x?date(x):"未记录"}
function outcomeClass(x){return x==="全赢"||x==="半赢"?"green":x==="全输"||x==="半输"?"red":""}
function orderModelName(model){return model==="m1"?"M1 AH":model==="mr1"?"MR1 AH":model==="m3"?"M3":"M4"}
function orderGame(item){return (item.home_zh||item.home)+" vs "+(item.away_zh||item.away)}
function orderMarket(item){return item.market==="OU"?"大小球":"让球"}
function orderSideMarket(item,side){
 if(item.market==="OU")return {name:side==="home"?"大球":"小球",line:item.selection_line,water:side==="home"?item.home_hk:item.away_hk};
 var isHome=side==="home";
 return {name:(isHome?item.home_zh||item.home:item.away_zh||item.away),line:isHome?item.home_line:item.away_line,water:isHome?item.home_hk:item.away_hk};
}

function orderScoping(){
 return (selected==="m1"||selected==="mr1")?period:"all";
}
function orderPanelMarkup(){
 const label=selected==="m4"?
  "M4 目前没有独立新订单；逐场引用 MR1 的真实皇冠报价，展示原订单和研究中的“保留／跳过”假设。":
 selected==="m3"?
  "M3 逐笔影子预测；只显示已保存的盘口证据，未保存的对侧水位不会推算或伪造。":
  "以下每行是一条真正发到 Telegram 的订单。即使同一场有多条不同正式单，也分别列出，方便找出风险。";
 return '<div id="matchOrders" class="order-audit">'+
   '<div class="order-head"><div><h3>逐场订单与盘口明细</h3><div class="order-sub">'+label+'</div></div><button onclick="loadOrders(false)">刷新逐场明细</button></div>'+
   '<div class="order-filters"><div class="order-search"><label>查比赛、球队、联赛</label><input id="orderQuery" placeholder="输入中文球队、联赛或比赛号" value="'+esc(orderState.query)+'" oninput="orderSearchChanged(this.value)"></div>'+
   '<div style="min-width:140px"><label>结算状态</label><select id="orderResultFilter" onchange="orderFilterChanged(this.value)">'+
   [['all','所有订单'],['settled','已结算'],['pending','未结算'],['win','盈利订单'],['loss','亏损订单']].map(function(x){return '<option value="'+x[0]+'" '+(x[0]===orderState.result?'selected':'')+'>'+x[1]+'</option>'}).join('')+
   '</select></div></div>'+
   '<div id="orderCoverage" class="order-cover">正在读取逐场订单…</div>'+
   '<div id="orderGrid">正在读取…</div>'+
   '<div id="orderPages" class="order-pager"></div></div>';
}

renderScores = function(){
 if(!data)return;
 var scope=orderScoping(),changed=selected!==orderState.model||scope!==orderState.scope;
 if(changed){
   orderState={model:selected,scope:scope,page:1,query:"",result:"all",payload:null};
 }
 var panel=document.getElementById("matchOrders");
 if(panel&&!changed){
   panel.remove(); // Preserve search focus and pagination through automatic status refreshes.
   orderSummaryRender();
   document.getElementById("details").appendChild(panel);
   if(orderState.payload)orderDraw(orderState.payload);
 }else{
   orderSummaryRender();
   document.getElementById("details").insertAdjacentHTML("beforeend",orderPanelMarkup());
   loadOrders(true);
 }
};

function orderSearchChanged(next){
 orderState.query=next;
 orderState.page=1;
 clearTimeout(orderTimer);
 orderTimer=setTimeout(function(){loadOrders(false)},330);
}
function orderFilterChanged(v){orderState.result=v;orderState.page=1;loadOrders(false)}
function orderPage(p){if(!orderState.payload||p<1||p>orderState.payload.pages)return;orderState.page=p;loadOrders(false);document.getElementById("matchOrders")?.scrollIntoView({behavior:"smooth",block:"start"})}

async function loadOrders(force){
 if(!data||!orderState.model)return;
 const request=++orderFetchSerial;
 const params=new URLSearchParams({
    model:orderState.model,scope:orderState.scope||"all",
    search:orderState.query,result:orderState.result,page:String(orderState.page)
 });
 const coverage=document.getElementById("orderCoverage");
 if(coverage&&force)coverage.textContent="正在读取真实订单与盘口…";
 try{
   const response=await fetch("/api/orders?"+params.toString(),{cache:"no-store"});
   const result=await response.json();
   if(!response.ok)throw new Error(result.error||"明细暂时无法读取");
   if(request!==orderFetchSerial||result.model!==orderState.model)return;
   orderState.payload=result;
   orderDraw(result);
 }catch(err){
   if(request!==orderFetchSerial)return;
   if(coverage)coverage.textContent="明细暂时无法读取："+String(err.message);
 }
}
function orderDraw(payload){
 const area=document.getElementById("orderGrid"),coverage=document.getElementById("orderCoverage"),pages=document.getElementById("orderPages");
 if(!area||!coverage||!pages)return;
 const label=payload.model==="m4"?"MR1 历史研究对照":"模型订单";
 const coveragePercent=payload.total?(payload.with_both_prices/payload.total*100).toFixed(0):"—";
 let explain="当前范围 "+payload.total+" 笔"+label+"，已结 "+payload.settled+"，未结 "+payload.pending+"。";
 if(payload.model==="m1"||payload.model==="mr1"){
   explain+=" 完整双边水位 "+payload.with_both_prices+" 笔；明确验证 Crown 来源 "+payload.verified_crown+" 笔。";
   if(payload.verified_crown<payload.total)explain+=" 未验证来源的旧单会明确标注，不能当成皇冠。";
 }else if(payload.model==="m3"){
   explain+=" 这些是模拟预测，原账本只保存所选方向水位；对侧报价缺失会显示“未保存”。";
 }else{
   explain+=" M4 仅沿用 MR1 盘口做事后对照，绝非独立正式投注。";
 }
 coverage.textContent=explain;
 if(!payload.rows.length){
   area.innerHTML='<p class="order-sub">当前搜索条件下没有订单。可以清空搜索或切换状态。</p>';
   pages.textContent="";
   return;
 }
 area.innerHTML='<div class="order-scroll"><table class="order-table">'+
  '<thead><tr><th class="align-left">比赛／发单时间</th><th class="align-left">主队让球／水位</th><th class="align-left">客队让球／水位</th><th class="align-left">'+(payload.model==="m4"?"原下注／M4假设":"我们选择")+'</th><th>下单水位</th><th>最终比分</th><th>'+(payload.model==="m4"?"原MR1结果":"结果")+'</th><th>'+ (payload.model==="m4"?"研究收益":"净收益") +'</th></tr></thead><tbody>'+
  payload.rows.map(function(x){
    var home=orderSideMarket(x,"home"),away=orderSideMarket(x,"away");
    var result=x.result&&x.result.home!=null&&x.result.away!=null?x.result.home+" : "+x.result.away:"未结算";
    var chosen=(payload.model==="m4"?'<div>'+esc(x.m4_action)+'</div>':'')+
       (payload.model==="m3"?'<span class="quote-quiet">'+esc(x.submodel||"")+' · '+orderMarket(x)+'</span><br>':'')+
       '<span class="selection">'+esc(x.direction)+" "+orderLine(x.selection_line)+'</span>';
    return '<tr data-id="'+esc(x.id)+'" onclick="openOrder(this.dataset.id)">'+
      '<td class="align-left"><div class="match">'+esc(orderGame(x))+'</div><div class="fixture-sub">'+esc(x.league_zh||x.league)+' · '+orderTime(x.posted_at)+'</div>'+
      (x.same_game_orders>1?'<div class="fixture-sub">此范围同场 '+x.same_game_orders+' 单</div>':'')+
      (x.model==='m1'&&!x.bookmaker_verified?'<div class="fixture-sub no-quote">旧单盘口来源未核实</div>':'')+
      (x.quote_at&&x.posted_at?'<div class="fixture-sub">盘口报价距发单 '+shortAge(x.quote_at,x.posted_at)+'</div>':'')+'</td>'+
      '<td class="align-left">'+(x.home_hk!=null?'<div class="quote-main">'+esc(home.name)+' '+orderLine(home.line)+'</div><div class="water-hk">'+orderWater(home.water)+'</div>':'<span class="no-quote">未保存</span>')+'</td>'+
      '<td class="align-left">'+(x.away_hk!=null?'<div class="quote-main">'+esc(away.name)+' '+orderLine(away.line)+'</div><div class="water-hk">'+orderWater(away.water)+'</div>':'<span class="no-quote">未保存</span>')+'</td>'+
      '<td class="align-left">'+chosen+'</td>'+
      '<td><strong>'+orderWater(x.selection_hk)+'</strong></td>'+
      '<td>'+result+'</td>'+
      '<td class="'+outcomeClass(x.settlement)+'">'+esc(x.settlement)+'</td>'+
      '<td class="profit '+col(x.pnl)+'">'+(x.pnl!=null?u(x.pnl):"—")+'</td></tr>';
  }).join("")+'</tbody></table></div>';
 pages.innerHTML='<div class="sub">第 '+payload.page+' / '+payload.pages+' 页 · 共 '+payload.total+' 笔，每笔都可点开查看原始盘口</div>'+
   '<div class="pager-actions"><button '+(payload.page<=1?'disabled':'')+' onclick="orderPage('+(payload.page-1)+')">上一页</button>'+
   '<button '+(payload.page>=payload.pages?'disabled':'')+' onclick="orderPage('+(payload.page+1)+')">下一页</button></div>';
}

function valueOrBlank(x){return x===null||x===undefined?"未存":esc(String(x))}
function shortAge(from,to){
 if(!from||!to)return "无法比较";
 const a=Date.parse(from),b=Date.parse(to);
 if(!Number.isFinite(a)||!Number.isFinite(b))return "无法比较";
 const delta=Math.round((b-a)/60000);
 return delta>=0?delta+" 分钟":"报价时间晚于发单，需核查";
}
function quoteCard(label,name,line,hk,price,best){
 return '<div class="order-pricebox '+(best?'best':'')+'"><div class="price-label">'+esc(label)+'</div>'+
   '<div class="price-name">'+esc(name)+'</div>'+
   '<div class="price-number">'+orderLine(line)+'　'+orderWater(hk)+'</div>'+
   '<div class="price-info">让球线 · 香港水位'+(price!=null?'　|　欧赔 '+orderN(price,3):'')+'</div></div>';
}
function kv(label,value){return '<div class="kv"><span>'+esc(label)+'</span><b>'+esc(value)+'</b></div>'}
function quoteChart(path){
 if(!Array.isArray(path)||path.length<2)return '<p class="order-sub">这笔比赛没有足够的完整双边盘口路径，不能绘制可靠变化图。</p>';
 const records=path.filter(x=>x.home_hk!=null&&x.away_hk!=null);
 if(records.length<2)return '<p class="order-sub">没有足够双边水位观察点。</p>';
 const vals=records.flatMap(x=>[Number(x.home_hk),Number(x.away_hk)]).filter(Number.isFinite);
 if(!vals.length)return '';
 const low=Math.min(...vals),high=Math.max(...vals),margin=Math.max(.035,(high-low)*.18);
 const min=low-margin,max=high+margin,W=740,H=170,left=41,right=714,top=15,bottom=133;
 function xy(i,key){let x=left+i*(right-left)/(records.length-1),v=Number(records[i][key]);return [x,top+(max-v)/(max-min)*(bottom-top)]}
 const make=(key,color)=>'<path d="'+records.map((o,i)=>{var p=xy(i,key);return (i===0?'M':'L')+p[0].toFixed(2)+' '+p[1].toFixed(2)}).join(" ")+'" fill="none" stroke="'+color+'" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"/>'+
   records.map((x,i)=>{var p=xy(i,key);return '<circle cx="'+p[0].toFixed(2)+'" cy="'+p[1].toFixed(2)+'" r="3.5" fill="'+color+'"/>'}).join("");
 return '<div class="order-chart"><svg viewBox="0 0 740 170" role="img" aria-label="主客队历史皇冠水位变化图">'+
 '<line x1="41" x2="714" y1="15" y2="15" stroke="#e3e8f0"/><line x1="41" x2="714" y1="133" y2="133" stroke="#e3e8f0"/>'+
 '<text x="3" y="19" font-size="11" fill="#78889b">'+max.toFixed(2)+'</text><text x="3" y="136" font-size="11" fill="#78889b">'+min.toFixed(2)+'</text>'+
 make("home_hk","#2b71bc")+make("away_hk","#d27a44")+
 '<text x="43" y="158" font-size="11" fill="#6d7e90">早</text><text x="695" y="158" font-size="11" fill="#6d7e90">晚</text></svg>'+
 '<div class="order-chart-legend"><span><i class="legend-line" style="background:#2b71bc"></i>主队水位</span><span><i class="legend-line" style="background:#d27a44"></i>客队水位</span></div></div>';
}
function historyTable(path){
 if(!Array.isArray(path)||!path.length)return '';
 return '<div class="order-history"><table><thead><tr><th class="align-left">报价时间（北京时间）</th><th>主让盘</th><th>主水位</th><th>客让盘</th><th>客水位</th></tr></thead><tbody>'+
 path.map(x=>'<tr><td class="align-left">'+orderTime(x.at)+'</td><td>'+orderLine(x.home_line)+'</td><td>'+orderWater(x.home_hk)+'</td><td>'+orderLine(x.away_line)+'</td><td>'+orderWater(x.away_hk)+'</td></tr>').join("")+
 '</tbody></table></div>';
}
function closeOrder(){
 const node=document.getElementById("orderBackdrop");
 if(node)node.remove();
 document.body.style.overflow="";
 modalOpen=false;
}
function orderEscape(e){if(e.key==="Escape"&&modalOpen)closeOrder()}
document.addEventListener("keydown",orderEscape);

async function openOrder(id){
 const model=orderState.model;
 const modal=document.createElement("div");
 modal.id="orderBackdrop";modal.className="order-modal-backdrop";
 modal.innerHTML='<div class="order-modal"><div class="order-modal-top"><h3>正在读取这场比赛…</h3><button class="close" onclick="closeOrder()">×</button></div></div>';
 document.body.appendChild(modal);
 modal.addEventListener("click",e=>{if(e.target===modal)closeOrder()});
 document.body.style.overflow="hidden";modalOpen=true;
 try{
   const response=await fetch("/api/order?"+new URLSearchParams({model:model,id:id}).toString(),{cache:"no-store"});
   const doc=await response.json();if(!response.ok||!doc.order)throw Error(doc.error||"找不到订单");
   if(!modal.isConnected)return;
   modal.querySelector(".order-modal").innerHTML=orderDetailHtml(doc.order);
 }catch(err){if(modal.isConnected)modal.querySelector(".order-modal").innerHTML='<div class="order-modal-top"><h3>无法读取订单</h3><button class="close" onclick="closeOrder()">×</button></div><p>'+esc(err.message)+'</p>'}
}
function orderDetailHtml(x){
 const result=x.result&&x.result.home!=null&&x.result.away!=null?x.result.home+' : '+x.result.away:'未取得完整结算比分';
 const hk=x.selection_hk;
 const pickTeam=x.direction==='主队'?(x.home_zh||x.home):x.direction==='客队'?(x.away_zh||x.away):(x.selection||'');
 const study=x.model==='m4';
 const mainTitle=orderGame(x);
 const sourceFlag=x.bookmaker_verified?'原始皇冠盘口已验证':x.bookmaker;
 const bothQuote=x.home_hk!=null&&x.away_hk!=null;
 const notes=(x.notes||[]).slice();
 if(!bothQuote)notes.push('对面水位原账本未保存，这里明确显示缺失，不用其他来源事后补价。');
 if(x.quote_matches_selection===false)notes.push('模型订单水位与保存的双边报价不一致，需核对原始记录。');
 const lineLabel=(x.market==='OU'?'大小球':'让球');
 return '<div class="order-modal-top"><div><div class="order-meta">'+esc(x.league_zh||x.league)+' · '+lineLabel+'</div><h3>'+esc(mainTitle)+'</h3><div class="order-meta">比赛开始：'+orderTime(x.kickoff)+'　|　'+(x.tg_sent?'正式 TG 发单':'研究预测')+'：'+orderTime(x.posted_at)+'</div></div><button class="close" onclick="closeOrder()">×</button></div>'+
 '<div class="order-resultbar"><span class="score">'+esc(result)+'</span><span class="outcome '+outcomeClass(x.settlement)+'">'+esc(x.settlement)+'</span><span class="'+col(x.pnl)+'" style="font-weight:760;font-size:20px">'+(x.pnl==null?'待结算':u(x.pnl))+'</span></div>'+
 (study?'<div class="order-alert"><b>'+esc(x.m4_action||"研究比较")+'</b>。本条沿用 MR1 原始订单与实际赛果，仅按研究假设重新计算收益，M4 没有独立正式下注。</div>':'')+
 '<h4>当时双方盘口与我们选择</h4>'+
 '<div class="order-prices">'+
 quoteCard('主队盘口快照',x.home_zh||x.home,x.home_line,x.home_hk,x.home_price,false)+
 quoteCard('客队盘口快照',x.away_zh||x.away,x.away_line,x.away_hk,x.away_price,false)+
 quoteCard(study?'MR1 当时实际选择（M4 仅假设）':'我们的实际选择',pickTeam,x.selection_line,hk,x.selection_price,true)+
 '</div>'+
 '<div class="order-detail-list">'+
 kv('使用盘口来源',sourceFlag)+
 kv('原始报价时间',orderTime(x.quote_at))+
 kv('实际发单／预测时间',orderTime(x.posted_at))+
 kv('报价到发单相隔',shortAge(x.quote_at,x.posted_at))+
 kv('模型预测 EV（只作分析）',x.ev!=null?pct(x.ev*100):'未记录')+
 kv('赛果',result)+
 kv('下单香港水位',orderWater(hk))+
 kv('下单欧赔',x.selection_price!=null?orderN(x.selection_price,3):'未记录')+
 kv('订单结算状态',x.settlement)+
 kv('订单是否已发到 TG',x.tg_sent?'已正式发单':'研究预测，没有正式发单')+
 '</div>'+
 (notes.length?'<div class="order-alert">'+notes.map(esc).join('<br>')+'</div>':'')+
 sameMatchHtml(x)+
 '<h4>历史盘口变化</h4><p class="order-sub">曲线是不同时间记录的主、客香港水位。若让球线发生变化，请同时参考下面的盘口线明细，不能把不同盘口的水位直接当同一盘口比较。</p>'+
 quoteChart(x.quote_path)+historyTable(x.quote_path)+
 (x.raw_text?'<h4>当时记录的原始派单内容</h4><div class="order-original-tg">'+esc(x.raw_text)+'</div>':'')+
 '<details style="margin-top:18px"><summary>原始证据核对信息</summary><p class="order-source">模型：'+esc(orderModelName(x.model))+'<br>比赛编号：'+esc(x.fixture)+'<br>订单编号：'+esc(x.id)+
 '<br>TG 回执：'+esc(x.tg_message_id||"无")+'<br>原始来源：'+esc(x.source||"未知")+
 (x.source_snapshot_key?'<br>盘口记录：'+esc(x.source_snapshot_key):'')+'</p></details>';
}

function sameMatchHtml(order){
 const rows=order.same_match_orders||[];
 if(!rows.length)return '';
 return '<h4>这场比赛的所有'+(order.model==='m3'?'影子预测':order.model==='m4'?'研究对照':'正式订单')+'（'+rows.length+' 笔）</h4>'+
  '<div class="order-history"><table><thead><tr><th class="align-left">'+(order.model==='m3'?'模型／预测时间':'发单时间')+'</th><th>方向</th><th>让球线</th><th>下单水位</th><th>'+(order.model==="m4"?"原MR1结果":"结果")+'</th><th>收益</th></tr></thead><tbody>'+
  rows.map(function(x){return '<tr'+(x.id===order.id?' style="background:#eef5fd"':'')+'><td class="align-left">'+(x.submodel?esc(x.submodel)+' · ':'')+orderTime(x.posted_at)+'</td><td>'+esc(x.direction)+(x.m4_action?'（'+esc(x.m4_action)+'）':'')+'</td><td>'+orderLine(x.selection_line)+'</td><td>'+orderWater(x.selection_hk)+'</td><td>'+esc(x.settlement)+'</td><td class="'+col(x.pnl)+'">'+(x.pnl==null?'待结':u(x.pnl))+'</td></tr>'}).join('')+
  '</tbody></table></div>';
}
/* Focused interface: compact performance, evidence stays available on demand. */
cards = function(){
  return ["m1","mr1","m3","m4"].map(function(id){
    var x=score(id), roi=x.roi==null&&id==="m3"?(x.settled?x.pnl/x.settled*100:null):x.roi;
    var type=id==="m3"?"模拟":id==="m4"?"研究":"";
    var left=id==="m4"?"样本 "+n(x.sent):"发 "+n(x.sent);
    return '<div class="panel card '+(selected===id?'selected':'')+'" role="button" tabindex="0" onclick="selectScore(\''+id+'\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();selectScore(\''+id+'\')}">'+
       '<div class="cardhead"><h3>'+modelNames[id]+'</h3>'+(type?'<span class="kind">'+type+'</span>':'')+'</div>'+
       '<div class="big '+col(x.pnl)+'">'+u(x.pnl)+'</div>'+
       '<div class="compact-roi">收益率 '+pct(roi)+'</div>'+
       '<div class="statrow"><span>'+left+'</span><span>结 '+n(x.settled)+'</span><span>待 '+n(x.pending)+'</span></div>'+
    '</div>';
  }).join("");
};

detail = function(){
  var id=selected,p=data.performance;
  if(id==="m1"||id==="mr1"){
    var w=p[id][period];
    var counts=["全赢","半赢","走水","半输","全输"].map(function(k){
      return '<span>'+k+' <b>'+n(w.states[k])+'</b></span>';
    }).join("");
    return '<div class="compact-detail"><div class="compact-detail-title"><b>'+modelNames[id]+'</b>'+
      '<div class="segments">'+["all","last","this"].map(function(k){return '<button class="'+(period===k?'active':'')+'" onclick="changePeriod(\''+k+'\')">'+({all:'全部',last:'上周',this:'本周'})[k]+'</button>'}).join('')+'</div></div>'+
      '<div class="compact-counts">'+counts+'</div></div>';
  }
  if(id==="m3"){
    return '<div class="compact-detail"><div class="compact-detail-title"><b>M3</b></div>'+
      '<div class="compact-compare compact-compare-header"><span>模型 / 盘口</span><span>已结 / 模拟</span><span>净收益</span><span>收益率</span></div>'+
      p.m3.lines.map(function(x){return '<div class="compact-compare"><span>'+esc(x.name)+' · '+esc(x.market)+'</span><span>'+n(x.settled)+' / '+n(x.sent)+'</span><strong class="'+col(x.pnl)+'">'+u(x.pnl)+'</strong><span class="'+col(x.roi)+'">'+pct(x.roi)+'</span></div>'}).join('')+'</div>';
  }
  var t=p.m4, b=t.baseline||{}, e=t.excluded||{}, h=t.hypothetical||{};
  return '<div class="compact-detail"><div class="compact-detail-title"><b>M4 · 历史比较</b></div>'+
   '<div class="compact-compare compact-compare-header"><span>方案</span><span>样本</span><span>收益</span><span>收益率</span></div>'+
   [[ 'MR1 原单',b], ['剔除联赛',e], ['假设保留',h]].map(function(y){
     var r=y[1];return '<div class="compact-compare"><span>'+y[0]+'</span><span>'+n(r.orders)+'</span><strong class="'+col(r.pnl_units)+'">'+u(r.pnl_units)+'</strong><span>'+pct(r.roi==null?null:r.roi*100)+'</span></div>';
   }).join('')+'</div>';
};

orderPanelMarkup = function(){
  return '<div id="matchOrders" class="order-audit">'+
    '<div class="od-toolbar"><b>逐场明细</b><span id="orderCoverage" class="od-count"></span>'+
    '<input id="orderQuery" aria-label="搜索比赛" placeholder="搜索球队 / 联赛" value="'+esc(orderState.query)+'" oninput="orderSearchChanged(this.value)">'+
    '<select id="orderResultFilter" aria-label="结算状态" onchange="orderFilterChanged(this.value)">'+
    [['all','全部'],['settled','已结'],['pending','待结'],['win','盈利'],['loss','亏损']].map(function(x){return '<option value="'+x[0]+'" '+(x[0]===orderState.result?'selected':'')+'>'+x[1]+'</option>'}).join('')+'</select></div>'+
    '<div id="orderGrid"></div><div id="orderPages" class="order-pager"></div></div>';
};

function shortOrderDate(value){
 if(!value)return '—';
 var dt=new Date(value);
 if(Number.isNaN(dt.getTime()))return '—';
 return new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}).format(dt);
}
function compactWater(x){
 return x===null||x===undefined?'—':orderWater(x);
}
function compactScore(item){
 return item.result&&item.result.home!=null&&item.result.away!=null?
    (item.result.home+' : '+item.result.away):'— : —';
}
function compactOrderRow(x,model){
 var home=orderSideMarket(x,'home'),away=orderSideMarket(x,'away');
 var homeLine=home.water==null?'—':orderLine(home.line);
 var awayLine=away.water==null?'—':orderLine(away.line);
 var fromX=x.league_zh||x.league||'';
 var shortMeta=esc(fromX)+' <span class="od-dot">·</span> '+esc(shortOrderDate(x.posted_at));
 // Historical source evidence is a detail, not a repeated list badge.
 var info=x.model==='m3'?(x.submodel||''):(x.model==='m4'?(x.m4_action||'').replace('研究假设：',''):'');
 var chosen=esc(x.direction||'—')+' '+orderLine(x.selection_line);
 var score=compactScore(x);
 return '<div class="od-row" role="button" tabindex="0" data-id="'+esc(x.id)+'" onclick="openOrder(this.dataset.id)" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();openOrder(this.dataset.id)}">'+
    '<div class="od-game"><div class="od-teams">'+esc(orderGame(x))+'</div>'+
    '<div class="od-meta">'+shortMeta+(info?'<span class="od-note"> · '+esc(info)+'</span>':'')+'</div></div>'+
    '<div class="od-odds"><div><span>主</span><b>'+homeLine+'</b><strong>'+compactWater(home.water)+'</strong></div>'+
      '<div><span>客</span><b>'+awayLine+'</b><strong>'+compactWater(away.water)+'</strong></div></div>'+
    '<div class="od-pick"><span>买</span><b>'+chosen+'</b><strong>'+compactWater(x.selection_hk)+'</strong></div>'+
    '<div class="od-finish"><span class="od-score">'+score+'</span>'+
     '<span class="od-settle '+outcomeClass(x.settlement)+'">'+esc(x.settlement)+'</span>'+
     '<strong class="od-profit '+(x.pnl==null?'':col(x.pnl))+'">'+(x.pnl==null?'—':u(x.pnl))+'</strong></div>'+
 '</div>';
}
orderDraw = function(payload){
 var area=document.getElementById('orderGrid'),cover=document.getElementById('orderCoverage'),pages=document.getElementById('orderPages');
 if(!area||!cover||!pages)return;
 cover.textContent=n(payload.total)+' 笔 · '+n(payload.settled)+' 结 · '+n(payload.pending)+' 待';
 // Keep provenance visible once, not as repeated orange labels on every match.
 let legacy=document.getElementById('orderLegacySource');
 if(!legacy){
   legacy=document.createElement('span');
   legacy.id='orderLegacySource';
   legacy.className='od-source-summary';
   cover.insertAdjacentElement('afterend',legacy);
 }
 const unverified=payload.model==='m1'?Math.max(0,payload.total-(payload.verified_crown||0)):0;
 legacy.textContent=unverified?unverified+' 笔旧单无盘口来源存证':'';
 legacy.title=unverified?'旧 M1 订单保留了双方报价，但缺少原始 Crown 来源验证记录。点开具体订单可核对。':'';
 legacy.hidden=!unverified;
 if(!payload.rows.length){
   area.innerHTML='<div class="od-empty">没有符合条件的订单</div>';
   pages.innerHTML='';
   return;
 }
 area.innerHTML='<div class="od-head"><span>比赛</span><span>盘口水位</span><span>下注</span><span>赛果 / 收益</span></div>'+
   '<div class="od-list">'+payload.rows.map(function(x){return compactOrderRow(x,payload.model)}).join('')+'</div>';
 pages.innerHTML='<div class="od-page-info">'+payload.page+' / '+payload.pages+'</div>'+
   '<div class="pager-actions"><button '+(payload.page<=1?'disabled':'')+' onclick="orderPage('+(payload.page-1)+')">上一页</button>'+
   '<button '+(payload.page>=payload.pages?'disabled':'')+' onclick="orderPage('+(payload.page+1)+')">下一页</button></div>';
};

// Main screen display is deterministic; the underlying accounting remains untouched.
if(data&&currentTab==='scores')renderScores();

/* Short labels for execution/settings; unchanged actions and saved values. */
runLines = function(){
 return ["m1","mr1","m3","m4"].map(function(id){
   return '<div class="runline"><div class="runname">'+modelNames[id]+'</div>'+
    '<div class="runbuttons"><button class="primary" onclick="runModel(\''+id+'\',\'run\')">运行</button>'+
      (id==='m4'?'':'<button onclick="runModel(\''+id+'\',\'settle\')">结算</button>')+
      '<button onclick="goScore(\''+id+'\')">战绩</button></div></div>';
 }).join('');
};
control = function(id){
 var c=data.settings.models[id], research=id==='m3'||id==='m4';
 return '<div class="settingscard" data-model="'+id+'">'+
 '<div class="settingshead"><h3>'+modelNames[id]+'</h3><button onclick="saveModel(\''+id+'\')">保存</button></div>'+
 '<div class="controls">'+
 '<label class="check"><input data-k="schedule_enabled" type="checkbox" '+(c.schedule_enabled?'checked':'')+'>定时</label>'+
 '<div class="control"><label>方式</label><select data-k="schedule_type" onchange="scheduleFields(\''+id+'\')">'+
 '<option value="manual" '+(c.schedule_type==='manual'?'selected':'')+'>只手动</option>'+
 '<option value="times" '+(c.schedule_type==='times'?'selected':'')+'>每日定点</option>'+
 '<option value="interval" '+(c.schedule_type==='interval'?'selected':'')+'>循环间隔</option></select></div>'+
 '<div class="control" data-time="'+id+'"><label>北京时间</label><input data-k="times" value="'+esc(c.times)+'" placeholder="06:00,12:00"></div>'+
 '<div class="control" data-interval="'+id+'"><label>分钟</label><input data-k="interval_minutes" type="number" min="1" value="'+(c.interval_minutes||'')+'"></div>'+
 '<label class="check"><input type="checkbox" data-k="tg_enabled" '+(c.tg_enabled?'checked':'')+'>'+(research?'研究 TG':'正式 TG')+'</label>'+
 '</div></div>';
};
var oldCompactOrderRow=compactOrderRow;
compactOrderRow=function(x,model){
 var content=oldCompactOrderRow(x,model);
 if(x.market==='OU'&&x.selection_line!=null){
   var normalized=String(Number(x.selection_line));
   var plus='+'+normalized;
   // Total-goal lines are thresholds, never a handicap of +N goals.
   content=content.replace(esc(x.direction||'—')+' '+plus,esc(x.direction||'—')+' '+normalized);
 }
 return content;
};

/* Four user-controlled model tests and one-page local connection setup. */
runLines = function(){
 return ["m1","mr1","m3","m4"].map(function(id){
  const c=data.settings.models[id];
  const isResearch=id==="m3"||id==="m4";
  const keySet=(id==="m1"?["M1_TELEGRAM_BOT_TOKEN","M1_TELEGRAM_CHAT_ID"]:
             id==="mr1"?["MR1_TG_BOT_TOKEN","MR1_TG_CHAT_ID"]:
             ["RESEARCH_TG_BOT_TOKEN","RESEARCH_TG_CHAT_ID"]);
  const connected=keySet.every(function(k){return data.credentials[k]});
  return '<div class="runline"><div class="runname">'+modelNames[id]+'</div>'+
    '<label class="check run-tg-label" title="由你控制测试或运行时是否发 TG"><input class="run-tg" type="checkbox" '+(c.tg_enabled?'checked':'')+' onchange="toggleModelTelegram(\''+id+'\',this)">'+(isResearch?'研究 TG':'正式 TG')+'</label>'+
    '<span class="run-connect '+(connected?'linked':'')+'">'+(connected?'已设置':'未设置')+'</span>'+
    '<div class="runbuttons"><button class="model-test-btn" onclick="runModel(\''+id+'\',\'test\')">测试</button>'+
      '<button class="primary" onclick="runModel(\''+id+'\',\'run\')">运行</button>'+
      (id==="m4"?"":'<button onclick="runModel(\''+id+'\',\'settle\')">结算</button>')+
      '<button onclick="goScore(\''+id+'\')">战绩</button></div></div>';
 }).join('');
};

async function toggleModelTelegram(model, checkbox){
 const current=Object.assign({},data.settings.models[model]);
 const previous=!checkbox.checked;
 try{
  const patch=Object.assign({},current,{tg_enabled:checkbox.checked});
  const result=await post("/api/settings",{models:{[model]:patch}});
  data.settings=result.settings;
  toast(modelNames[model]+" TG 已"+(checkbox.checked?"开启":"关闭"));
  renderRuns();
 }catch(error){
  checkbox.checked=previous;
  toast("设置未保存："+error.message,true);
 }
}
function connectionStatus(){
 if(!data)return;
 const groups={
   api:["TOTALCORNER_TOKEN"],
   m1:["M1_TELEGRAM_BOT_TOKEN","M1_TELEGRAM_CHAT_ID"],
   mr1:["MR1_TG_BOT_TOKEN","MR1_TG_CHAT_ID"],
   research:["RESEARCH_TG_BOT_TOKEN","RESEARCH_TG_CHAT_ID"]
 };
 Object.entries(groups).forEach(function([group,keys]){
  const e=document.querySelector('[data-status="'+group+'"]');
  if(!e)return;
  const count=keys.filter(k=>data.credentials[k]).length;
  e.textContent=count===keys.length?'已保存':count>0?'部分已保存':'未设置';
  e.className=count===keys.length?'connected':'';
 });
}
renderSettings = function(){
 if(!data)return;
 const active=document.activeElement;
 // Preserve credential fields during automatic status updates.
 const editing=active&&active.matches('.connect-input');
 if(!editing){
  el("settingModels").innerHTML=["m1","mr1","m3","m4"].map(control).join("");
  ["m1","mr1","m3","m4"].forEach(scheduleFields);
 }
 connectionStatus();
};
async function saveConnections(group){
 const form=document.querySelector('[data-connection="'+group+'"]');
 if(!form)return;
 const values={};
 form.querySelectorAll('[data-secret]').forEach(function(input){
  if(input.value.trim())values[input.getAttribute('data-secret')]=input.value.trim();
 });
 if(!Object.keys(values).length){toast("请填写现有连接资料",true);return}
 try{
  await post("/api/credentials-batch",{values:values});
  form.querySelectorAll('[data-secret]').forEach(input=>input.value="");
  toast("连接资料已保存在 Mac 钥匙串");
  await refresh(false);
  connectionStatus();
 }catch(error){
  toast("保存失败："+error.message,true);
 }
}

async function findChats(group){
 const form=document.querySelector('[data-connection="'+group+'"]');
 const resultBox=form?.querySelector('[data-chat-results="'+group+'"]');
 if(!resultBox)return;
 resultBox.textContent="正在查找…";
 try{
  const response=await fetch("/api/telegram-chats?group="+encodeURIComponent(group),{cache:"no-store"});
  const info=await response.json();
  if(!response.ok)throw Error(info.error||"暂时无法查找");
  resultBox.innerHTML='<div class="sub">'+esc(info.message||"")+'</div>';
  if(info.chats&&info.chats.length){
   const choices=document.createElement("div");
   choices.className="chat-choices";
   info.chats.forEach(function(chat){
    const btn=document.createElement("button");
    btn.className="chat-option";
    btn.type="button";
    btn.textContent=(chat.label||"聊天")+"（"+chat.id+"）";
    btn.onclick=function(){
     const field=form.querySelector('[data-secret$="CHAT_ID"]');
     if(field)field.value=chat.id;
     resultBox.innerHTML='<span class="sub">已选择。点击「保存」即可。</span>';
    };
    choices.appendChild(btn);
   });
   resultBox.appendChild(choices);
  }
 }catch(error){resultBox.textContent="查找失败："+error.message}
}

function openConnectionSetup(){
  tab("settings");
  const panel=document.getElementById("connections");
  if(panel){
    panel.open=true;
    panel.scrollIntoView({behavior:"smooth",block:"start"});
  }
}
function routeLocalAnchor(){
  if(window.location.hash==="#connections")openConnectionSetup();
}
window.addEventListener("hashchange",routeLocalAnchor);
routeLocalAnchor();

/* Show actual local step in Chinese without exposing raw terminal output. */
var _renderJobsBeforeProgress=renderRuns;
renderRuns=function(){
  _renderJobsBeforeProgress();
  if(!data||!Array.isArray(data.jobs))return;
  var cards=[...document.querySelectorAll("#runJobs .job")];
  data.jobs.slice(0,9).forEach(function(job,index){
    if(!cards[index])return;
    if(job.status!=="running"&&job.status!=="failed")return;
    fetch("/api/logs?id="+encodeURIComponent(job.id),{cache:"no-store"})
     .then(function(r){return r.json()})
     .then(function(log){
       if(!cards[index]?.isConnected)return;
       var text=log.log||"";
       var message=cards[index].querySelector(".jobmessage");
       if(!message)return;
       if(job.status==="running"){
         var steps={
           m1:["策略核对","扫描比赛"],
           mr1:["采集市场","计算模型","核算赛果","保存运行记录"],
           m3:["整理历史数据","采集赛程","保存赛程","核对赛事范围","模型预测","生成影子订单","核对模型状态","核算比分","保存账本","更新战绩"],
           m4:["联赛研究"]
         }[job.model]||[];
         var matches=[...text.matchAll(/Step (\d+)\/(\d+):/g)];
         if(matches.length){
           var last=matches[matches.length-1],index=Number(last[1])-1;
           message.textContent="正在"+(steps[index]||"执行")+" · 第"+last[1]+"/"+last[2]+"步";
         }else{
           message.textContent="正在启动模型…";
         }
       }else if(job.status==="failed"){
         if(text.includes("No module named 'm1_live_scan'"))
           message.textContent="本次失败：M1 本机模块路径错误；已修正启动路径。";
         else if(text.includes("notification claim requires a durable GitHub run identity"))
           message.textContent="本次失败：M1 沿用了 GitHub 运行身份校验；本机身份适配已修复。";
         else if(text.includes("IncompleteRead")||text.includes("TotalCorner 下载中断"))
           message.textContent="本次失败：TotalCorner 数据传输中断；已切换验证可用的下载方式。";
       }
     }).catch(function(){});
  });
};
