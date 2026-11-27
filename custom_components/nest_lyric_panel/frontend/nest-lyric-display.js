import './nest-lyric-panel.js?v=0.9.0b1';
const DisplayMode=Object.freeze({AUTO:'auto',COLUMN:'column',COMPACT:'compact',WIDE:'wide'});
const resolveDisplayMode=(mode,width)=>mode!==DisplayMode.AUTO?mode:width<600?DisplayMode.COLUMN:width<=1124?DisplayMode.COMPACT:DisplayMode.WIDE;
class NestLyricDisplay extends HTMLElement {
  static getStubConfig(){return {entity:'media_player.example'};}
  static getConfigElement(){return document.createElement('nest-lyric-editor');}
  constructor(){super();this.attachShadow({mode:'open'});this.player='';this.timelinePlayer='';this.currentImage='';this.timer=null;this.fitFrame=0;this.fitKey='';this.fitObserver=null;this.resizePanel=()=>{this.updateLayout();const stage=this.shadowRoot.querySelector('.stage');if(!stage)return;if(this.layoutMode===DisplayMode.COLUMN){stage.style.height=this.cardHeight();return;}const top=Math.max(0,this.getBoundingClientRect().top);const height=Math.max(180,Math.floor(window.innerHeight-top-4));stage.style.height=height+'px';stage.style.setProperty('--nest-available-height',height+'px');this.scheduleFit();};}
  connectedCallback(){if(typeof ResizeObserver!=='undefined'){this.layoutObserver=new ResizeObserver(()=>this.resizePanel());this.layoutObserver.observe(this);}window.addEventListener('resize',this.resizePanel);requestAnimationFrame(this.resizePanel);this.timer=setInterval(()=>this.updateProgress(),1000);if(typeof ResizeObserver!=='undefined'){this.fitObserver=new ResizeObserver(()=>this.scheduleFit());const p=this.shadowRoot.querySelector('.now-playing');if(p)this.fitObserver.observe(p);}}
  disconnectedCallback(){this.layoutObserver?.disconnect();this.layoutObserver=null;window.removeEventListener('resize',this.resizePanel);clearInterval(this.timer);this.timer=null;if(this.fitObserver)this.fitObserver.disconnect();if(this.fitFrame)cancelAnimationFrame(this.fitFrame);}
  setConfig(config){this.player='';this.timelinePlayer='';this.currentImage='';this.fitKey='';if(!config.entity&&!config.zone_entity&&(!config.room_selector||!config.rooms))throw Error('Configure entity or room_selector and rooms');this.config=config;this.layoutMode=null;this.shadowRoot.innerHTML=`<style>
    :host{display:block;height:100%;font-family:Roboto,'Arial',sans-serif;color:#191b20}
    .stage{box-sizing:border-box;display:grid;grid-template-columns:minmax(210px,34%) minmax(0,1fr);gap:6px;height:100%;min-height:0;padding:4px;background:#f7f8fa}
    .cover{display:flex;flex-direction:column;justify-content:flex-start;align-items:center;min-width:0;min-height:0;gap:4px}
    .art{display:block;flex:0 0 auto;width:min(100%,max(0px,calc(var(--nest-available-height, 100vh) - 200px)));aspect-ratio:1;object-fit:cover;border-radius:10px;box-shadow:0 4px 16px #0002;background:#e8eaed}
    .details{width:100%;min-width:0}.lyrics-body{flex:1;min-height:0}.lyrics-body>nest-lyric-panel-card{display:block;height:100%}.progress{margin:0;color:#5f6368;font-size:14px;font-weight:500}.progress-track{width:100%;height:5px;margin:3px 0 5px;overflow:hidden;border-radius:8px;background:#dfe2e6}.progress-fill{height:100%;width:var(--progress,0%);border-radius:inherit;background:#5f6368}.progress-times{display:flex;justify-content:space-between;gap:8px;line-height:1.25}.progress-times span{white-space:nowrap}
    .controls{display:flex;justify-content:center;align-items:center;gap:10px;margin-top:6px}.controls button{display:grid;place-items:center;border:0;border-radius:50%;width:44px;flex:0 1 44px;min-width:0;aspect-ratio:1;background:#e9edf1;color:#202124;cursor:pointer;padding:0}.controls button[data-command="volume_down"],.controls button[data-command="volume_up"]{background:#d3e3fd;color:#174ea6}.controls button[data-command="media_previous_track"],.controls button[data-command="media_next_track"]{background:#f3e9d5;color:#795525}.controls button.play{width:52px;flex-basis:52px;background:#1db954;color:#fff}.controls button:disabled{opacity:.35;cursor:default}.controls ha-icon{--mdc-icon-size:25px}.controls button.play ha-icon{--mdc-icon-size:29px}
    .now-playing{box-sizing:border-box;width:100%;flex:1 1 0;min-height:0;display:flex;flex-direction:column;gap:2px;padding:5px 8px;background:transparent;border:0;border-radius:0;box-shadow:none;overflow:hidden}.name-box{display:flex;align-items:center;justify-content:center;flex:1 1 0;min-height:0;min-width:0;overflow-y:auto}.name-text{display:block;width:100%;text-align:center;overflow-wrap:anywhere;white-space:normal;line-height:1.05;color:#202124;font-weight:700}.name-box.performer .name-text{color:#5f6368;font-weight:500}
    .line-empty{display:none}.lyrics{display:flex;flex-direction:column;min-height:0;min-width:0;background:#fff;border:1px solid #e8eaed;border-radius:12px;box-shadow:0 2px 10px #0000000d;overflow:hidden;padding:6px 5px}
    .stage[data-layout=compact]{grid-template-columns:minmax(130px,34%) minmax(0,1fr);gap:5px;padding:5px}.stage[data-layout=compact] .art{border-radius:7px}.stage[data-layout=compact] .lyrics{border-radius:8px;padding:3px}.stage[data-layout=column]{display:block;padding:0;background:transparent}.stage[data-layout=column] .cover{display:none}.stage[data-layout=column] .lyrics{box-sizing:border-box;height:100%;background:#fff;border:var(--ha-card-border-width,0) solid var(--divider-color);border-radius:var(--ha-card-border-radius,12px);box-shadow:var(--ha-card-box-shadow,none);padding:3px;--nlp-text:#101114;--nlp-secondary:#34373b}
    .stage[data-theme=dark]{background:#000;color:#fff}.stage[data-theme=dark] .lyrics{background:#000;border-color:#383838;--nlp-text:#fff;--nlp-secondary:#bcbcbc}.stage[data-theme=dark] .name-text{color:#fff}.stage[data-theme=dark] .name-box.performer .name-text,.stage[data-theme=dark] .progress{color:#bcbcbc}.stage[data-theme=dark] .progress-track{background:#333}.stage[data-theme=dark] .progress-fill{background:#ddd}</style><div class="stage"><div class="cover"><img class="art" alt="Обкладинка альбому"><div class="details"><div class="progress"><div class="progress-track" role="progressbar" aria-label="Позиція треку" aria-valuemin="0" aria-valuemax="100"><div class="progress-fill"></div></div><div class="progress-times"><span class="elapsed">—:—</span><span class="duration">—:—</span></div></div><div class="controls"><button type="button" data-command="volume_down" aria-label="Тихіше"><ha-icon icon="mdi:volume-minus"></ha-icon></button><button type="button" data-command="media_previous_track" aria-label="Попередній трек"><ha-icon icon="mdi:skip-previous"></ha-icon></button><button type="button" class="play" data-command="media_play_pause" aria-label="Відтворити"><ha-icon icon="mdi:play"></ha-icon></button><button type="button" data-command="media_next_track" aria-label="Наступний трек"><ha-icon icon="mdi:skip-next"></ha-icon></button><button type="button" data-command="volume_up" aria-label="Гучніше"><ha-icon icon="mdi:volume-plus"></ha-icon></button></div></div><div class="now-playing"><div class="name-box song"><span class="name-text"></span></div><div class="name-box performer"><span class="name-text"></span></div></div></div><div class="lyrics"><div class="lyrics-body"></div></div></div>`;this.shadowRoot.querySelector('.stage').dataset.theme=this.config.theme==='dark'?'dark':'light';if(this.fitObserver)this.fitObserver.observe(this.shadowRoot.querySelector('.now-playing'));requestAnimationFrame(this.resizePanel);this.shadowRoot.querySelectorAll('.controls button').forEach(button=>button.addEventListener('click',()=>{if(!this._hass||!this.player||button.disabled)return;this._hass.callService('media_player',button.dataset.command,{entity_id:this.player}).catch(e=>console.error('Nest Hub controls:',e));}));this.update();}
  cardHeight(){return /^(?:[1-9][0-9]{0,3})(?:px|%|vh)$/.test(String(this.config?.card_height||''))?this.config.card_height:'320px';}
  updateLayout(){const stage=this.shadowRoot.querySelector('.stage');if(!stage||!this.config)return;const selected=Object.values(DisplayMode).includes(this.config.display_mode)?this.config.display_mode:DisplayMode.AUTO;const width=this.getBoundingClientRect().width;if(selected===DisplayMode.AUTO&&!width)return;const mode=resolveDisplayMode(selected,width);if(mode===this.layoutMode)return;this.layoutMode=mode;stage.dataset.layout=mode;if(this.lyric){this.lyric.setConfig({...this.lyric.config,display_mode:mode});this.lyric.hass=this._hass;}}
  set hass(h){this._hass=h;this.update();}
  update(){if(!this._hass||!this.shadowRoot.querySelector('.stage'))return;const h=this._hass;const player=this.resolvePlayer(h);if(!player){this.player='';this.timelinePlayer='';this.shadowRoot.querySelector('.lyrics-body').replaceChildren();this.updateNames('','');return;}const timelinePlayer=this.resolveTimelinePlayer(h,player);const a=h.states[timelinePlayer]?.attributes||{};
    this.player=player;if(this.timelinePlayer!==timelinePlayer){this.timelinePlayer=timelinePlayer;const box=this.shadowRoot.querySelector('.lyrics-body');box.replaceChildren();const lyric=document.createElement('nest-lyric-panel-card');lyric.setConfig({sync_offset:0,...(this.config.lyrics||{}),display_mode:this.layoutMode||DisplayMode.COMPACT,theme:this.config.theme||'light',entity:timelinePlayer,card_height:'100%'});box.append(lyric);this.lyric=lyric;this.updateLayout();}
    this.lyric.hass=h;this.updateProgress();this.updateControls();this.updateNames(a.media_title,a.media_artist);
    const img=this.shadowRoot.querySelector('.art');const fallback=h.states[player]?.attributes||{};const sameTrack=a.media_title&&a.media_artist&&a.media_title===fallback.media_title&&a.media_artist===fallback.media_artist;const image=a.entity_picture_local||a.entity_picture||(sameTrack&&(fallback.entity_picture_local||fallback.entity_picture))||'';if(image!==this.currentImage){this.currentImage=image;if(image)img.src=image.startsWith('/')&&typeof h.hassUrl==='function'?h.hassUrl(image):image;else img.removeAttribute('src');}img.style.visibility=image?'visible':'hidden';
  }
  resolvePlayer(h){
    if(this.config.zone_entity){
      const active=h.states[this.config.zone_entity]?.attributes?.active_player||'';
      const app=String(h.states[active]?.attributes?.app_name||'').toLowerCase();
      if(app.includes('youtube')){
        const room=Object.values(this.config.rooms||{}).find(r=>r.cast===active);
        if(room?.physical)return room.physical;
      }
      return active;
    }
    if(this.config.entity)return this.config.entity;
    const selected=h.states[this.config.room_selector]?.state;
    const room=this.config.rooms?.[selected];if(!room)return '';
    const primary=room.music_assistant||room.entity;
    const physical=room.physical||primary;
    const cast=room.cast||physical;
    const app=String(h.states[cast]?.attributes?.app_name||'').toLowerCase();
    const castActive=['playing','paused','buffering'].includes(h.states[cast]?.state);
    const physicalActive=['playing','paused','buffering'].includes(h.states[physical]?.state);
    const youtubeActive=castActive&&app.includes('youtube');
    const youtubeSelected=this.config.source_selector&&h.states[this.config.source_selector]?.state===(this.config.youtube_source||'YouTube');
    return (youtubeActive||(youtubeSelected&&!app&&physicalActive))?physical:primary;
  }
  resolveTimelinePlayer(h,player){
    if(this.config.zone_entity)return h.states[this.config.zone_entity]?.attributes?.active_player||player;
    if(this.config.entity)return player;
    const room=this.config.rooms?.[h.states[this.config.room_selector]?.state];
    const cast=room?.cast||room?.physical||room?.music_assistant||room?.entity;
    const state=h.states[cast];const app=String(state?.attributes?.app_name||'').toLowerCase();
    return ['playing','paused','buffering'].includes(state?.state)&&app.includes('youtube')?cast:player;
  }
  updateNames(title,artist){const track=title||'',performer=artist||'';const key=JSON.stringify([track,performer]);if(key===this.fitKey)return;this.fitKey=key;for(const [selector,value] of [['.name-box.song',track],['.name-box.performer',performer]]){const box=this.shadowRoot.querySelector(selector);box.hidden=!value;box.style.display=value?'flex':'none';box.querySelector('.name-text').textContent=value;}this.fitNames();this.scheduleFit();}
  scheduleFit(){if(this.fitFrame)cancelAnimationFrame(this.fitFrame);this.fitFrame=requestAnimationFrame(()=>{this.fitFrame=0;this.fitNames();});}
  fitNames(){for(const box of this.shadowRoot.querySelectorAll('.name-box')){if(box.style.display==='none'||box.clientWidth<1||box.clientHeight<1)continue;const label=box.querySelector('.name-text');let lo=10,hi=96,best=10;while(lo<=hi){const size=Math.floor((lo+hi)/2);label.style.fontSize=size+'px';if(label.scrollHeight<=box.clientHeight+1&&label.scrollWidth<=box.clientWidth+1){best=size;lo=size+1;}else hi=size-1;}label.style.fontSize=best+'px';}}
  updateControls(){const state=this._hass?.states[this.player],bits=Number(state?.attributes?.supported_features)||0;const active=state&& !['unavailable','unknown'].includes(state.state);for(const button of this.shadowRoot.querySelectorAll('.controls button')){const command=button.dataset.command;let required=command==='volume_down'||command==='volume_up'?1028:command==='media_previous_track'?16:command==='media_next_track'?32:state?.state==='playing'?1:16384;button.disabled=!active||!(bits&required);if(command==='media_play_pause'){const playing=state?.state==='playing';button.setAttribute('aria-label',playing?'Пауза':'Відтворити');button.querySelector('ha-icon').setAttribute('icon',playing?'mdi:pause':'mdi:play');}}}
  formatTime(n){n=Math.floor(n);const h=Math.floor(n/3600),m=Math.floor((n%3600)/60),sec=String(n%60).padStart(2,'0');return h?h+':'+String(m).padStart(2,'0')+':'+sec:m+':'+sec;}
  updateProgress(){
    if(!this._hass||!this.timelinePlayer)return;
    const box=this.shadowRoot.querySelector('.progress');if(!box)return;
    const state=this._hass.states[this.timelinePlayer],a=state?.attributes||{},duration=Number(a.media_duration);
    if(!Number.isFinite(duration)||duration<=0){box.style.display='none';return;}
    box.style.display='';
    const raw=a.media_position,known=raw!==undefined&&raw!==null&&raw!==''&&Number.isFinite(Number(raw));
    let pos=known?Number(raw):0;
    if(known&&state.state==='playing'&&a.media_position_updated_at){const t=Date.parse(a.media_position_updated_at);if(Number.isFinite(t))pos+=Math.max(0,(Date.now()-t)/1000);}
    pos=Math.max(0,Math.min(duration,pos));
    const track=box.querySelector('.progress-track'),percentage=known?pos/duration*100:0;
    track.style.setProperty('--progress',percentage+'%');
    if(known)track.setAttribute('aria-valuenow',String(Math.round(percentage)));else track.removeAttribute('aria-valuenow');
    box.querySelector('.elapsed').textContent=known?this.formatTime(pos):'—:—';
    box.querySelector('.duration').textContent=this.formatTime(duration);
  }
  getCardSize(){return 4;}
}
customElements.define('nest-lyric-display',NestLyricDisplay);
window.customCards=window.customCards||[];window.customCards.push({type:'nest-lyric-display',name:'Nest Lyric Display',description:'Now playing, controls and lyrics for Nest Hub or TV'});
