/* Shared visual editor for both Nest Lyric cards. */
class NestLyricEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({mode:'open'}); this.config={}; }
  setConfig(config) { this.config=structuredClone(config||{}); this.render(); }
  set hass(value) { const language=value?.language; const changed=language!==this._hass?.language; this._hass=value; if (!this.rendered||changed) this.render(); for (const e of this.shadowRoot.querySelectorAll('ha-entity-picker')) e.hass=value; }
  get display() { return this.config.type==='custom:nest-lyric-display'; }
  t(uk,en) { return String(this._hass?.language||'en').startsWith('uk')?uk:en; }
  emit() { this.dispatchEvent(new CustomEvent('config-changed',{detail:{config:structuredClone(this.config)},bubbles:true,composed:true})); }
  put(key,value,inner=false) {
    const target=inner?(this.config.lyrics||(this.config.lyrics={})):this.config;
    if (value===''||value===undefined) delete target[key]; else target[key]=value;
    if(this.display&&!inner&&value&&(key==='entity'||key==='zone_entity'))delete this.config[key==='entity'?'zone_entity':'entity'];
    this.emit();
  }
  section(title) { const d=document.createElement('section'); const h=document.createElement('h3'); h.textContent=title; d.append(h); this.shadowRoot.append(d); return d; }
  field(parent,label,key,{inner=false,kind='text',min,max,step,domains,placeholder,defaultValue,choices}={}) {
    const wrap=document.createElement('label'), caption=document.createElement('span');caption.textContent=label;wrap.append(caption);
    const values=inner?(this.config.lyrics||{}):this.config; let el;
    if (kind==='entity') {
      el=document.createElement('ha-entity-picker'); el.hass=this._hass; el.includeDomains=domains; el.value=values[key]||''; el.allowCustomEntity=false;
      el.addEventListener('value-changed',e=>{ if (e.detail.value!==(values[key]||'')) this.put(key,e.detail.value,inner); });
    } else if(kind==='select') {
      el=document.createElement('select'); for(const [val,text] of choices){const o=document.createElement('option');o.value=val;o.textContent=text;el.append(o)} el.value=values[key]??defaultValue??'';
      el.addEventListener('change',()=>this.put(key,el.value,inner));
    } else {
      el=document.createElement('input');el.type=kind; if(min!==undefined)el.min=min;if(max!==undefined)el.max=max;if(step!==undefined)el.step=step;if(placeholder)el.placeholder=placeholder;
      if(kind==='checkbox')el.checked=values[key]??defaultValue??false;else el.value=values[key]??defaultValue??'';
      el.addEventListener('change',()=>{if(kind==='checkbox')this.put(key,el.checked,inner);else if(kind==='number'&&el.value!==''){if(!el.checkValidity())return;this.put(key,Number(el.value),inner);}else this.put(key,el.value,inner)});
    }
    if(kind==='checkbox'){wrap.classList.add('check');wrap.insertBefore(el,caption);}else wrap.append(el);parent.append(wrap);
  }
  render() {
    this.rendered=true;this.shadowRoot.replaceChildren();const style=document.createElement('style');style.textContent=':host{display:block;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}section{border-bottom:1px solid var(--divider-color);padding:10px 0}h3{font-size:1rem;font-weight:600;margin:0}label{display:flex;flex-direction:column;gap:5px;margin:12px 0}input,select,button{box-sizing:border-box;padding:10px;border:1px solid var(--divider-color);border-radius:5px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit}label.check{flex-direction:row;align-items:center;gap:10px}input[type=checkbox]{width:20px;height:20px}fieldset{margin:12px 0;border:1px solid var(--divider-color);border-radius:5px}ha-entity-picker{width:100%}';this.shadowRoot.append(style);
    const source=this.section(this.t('Джерело','Source'));
    this.field(source,this.t('Плеєр','Media player'),'entity',{kind:'entity',domains:['media_player']});
    if(this.display){
      this.field(source,this.t('Cast-зона (сенсор стану)','Cast zone (status sensor)'),'zone_entity',{kind:'entity',domains:['sensor']});
      const hint=document.createElement('p');hint.textContent=this.t('Cast-зона має пріоритет над окремим плеєром.','Cast zone takes priority over a standalone player.');source.append(hint);
    }
    const inner=this.display;
    const styleGroup=this.section(this.t('Вигляд','Appearance'));
    if(this.display)this.field(styleGroup,this.t('Режим розміщення','Display layout'),'display_mode',{kind:'select',choices:[['auto',this.t('Авто','Auto')],['column',this.t('Колонка','Column')],['compact',this.t('Компактний','Compact')],['wide',this.t('Широкий','Wide')]] ,defaultValue:'auto'});
    this.field(styleGroup,this.t('Тема','Theme'),'theme',{kind:'select',choices:[['light',this.t('Світла','Light')],['dark',this.t('Чорна','Black')]],defaultValue:'light'});
    this.field(styleGroup,this.t('Мова інтерфейсу','Interface language'),'language',{inner,kind:'select',choices:[['',this.t('Як у Home Assistant','Home Assistant default')],['uk','Українська'],['en','English']]});
    this.field(styleGroup,this.t('Висота в режимі колонки','Column height'),'card_height',{placeholder:'320px'});
    this.field(styleGroup,this.t('Режим налагодження','Debug mode'),'show_mode',{inner,kind:'checkbox',defaultValue:true});
  }
}
customElements.define('nest-lyric-editor',NestLyricEditor);
