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
    this.emit();
  }
  section(title) { const d=document.createElement('details'); d.open=true; const s=document.createElement('summary');s.textContent=title;d.append(s);this.shadowRoot.append(d);return d; }
  field(parent,label,key,{inner=false,kind='text',min,max,step,domains,placeholder,defaultValue,choices}={}) {
    const wrap=document.createElement('label'), caption=document.createElement('span');caption.textContent=label;wrap.append(caption);
    const values=inner?(this.config.lyrics||{}):this.config; let el;
    if (kind==='entity') {
      el=document.createElement('ha-entity-picker'); el.hass=this._hass; el.includeDomains=domains; el.value=values[key]||''; el.allowCustomEntity=false;
      el.addEventListener('value-changed',e=>{ if (e.detail.value!==(values[key]||'')) this.put(key,e.detail.value,inner); });
    } else if(kind==='select') {
      el=document.createElement('select'); for(const [val,text] of choices){const o=document.createElement('option');o.value=val;o.textContent=text;el.append(o)} el.value=values[key]??'';
      el.addEventListener('change',()=>this.put(key,el.value,inner));
    } else {
      el=document.createElement('input');el.type=kind; if(min!==undefined)el.min=min;if(max!==undefined)el.max=max;if(step!==undefined)el.step=step;if(placeholder)el.placeholder=placeholder;
      if(kind==='checkbox')el.checked=values[key]??defaultValue??false;else el.value=values[key]??'';
      el.addEventListener('change',()=>{if(kind==='checkbox')this.put(key,el.checked,inner);else if(kind==='number'&&el.value!==''){if(!el.checkValidity())return;this.put(key,Number(el.value),inner);}else this.put(key,el.value,inner)});
    }
    wrap.append(el);parent.append(wrap);
  }
  roomEditor(parent) {
    const rooms=this.config.rooms||{};
    for(const [name,room] of Object.entries(rooms)) {
      const group=document.createElement('fieldset'), legend=document.createElement('legend');legend.textContent=name;group.append(legend);
      for(const [key,uk,en] of [['music_assistant','Music Assistant','Music Assistant'],['entity','Основний плеєр (альтернатива)','Primary player (alternative)'],['physical','Фізична колонка','Physical speaker'],['cast','Cast-плеєр','Cast player']]){
        const l=document.createElement('label'),s=document.createElement('span'),e=document.createElement('ha-entity-picker');s.textContent=this.t(uk,en);e.hass=this._hass;e.includeDomains=['media_player'];e.value=room[key]||'';
        e.addEventListener('value-changed',ev=>{const v=ev.detail.value;if(v===(this.config.rooms?.[name]?.[key]||''))return;const out={...(this.config.rooms[name]||{})};if(v)out[key]=v;else delete out[key];this.config.rooms={...this.config.rooms,[name]:out};this.emit()}); l.append(s,e);group.append(l);
      }
      const del=document.createElement('button');del.type='button';del.textContent=this.t('Видалити кімнату','Remove room');del.addEventListener('click',()=>{this.config.rooms={...this.config.rooms};delete this.config.rooms[name];this.emit();this.render()});group.append(del);parent.append(group);
    }
    const name=document.createElement('input');name.placeholder=this.t('Назва кімнати як у перемикачі','Room name as in selector');const add=document.createElement('button');add.type='button';add.textContent=this.t('Додати кімнату','Add room');add.addEventListener('click',()=>{const n=name.value.trim();if(!n||this.config.rooms?.[n])return;this.config.rooms={...(this.config.rooms||{}),[n]:{}};this.emit();this.render()});parent.append(name,add);
  }
  render() {
    this.rendered=true;this.shadowRoot.replaceChildren();const style=document.createElement('style');style.textContent=':host{display:block;color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}details{border-bottom:1px solid var(--divider-color);padding:10px 0}summary{font-weight:600;cursor:pointer}label{display:flex;flex-direction:column;gap:5px;margin:12px 0}input,select,button{box-sizing:border-box;padding:10px;border:1px solid var(--divider-color);border-radius:5px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit}input[type=checkbox]{width:20px;height:20px}fieldset{margin:12px 0;border:1px solid var(--divider-color);border-radius:5px}ha-entity-picker{width:100%}';this.shadowRoot.append(style);
    const source=this.section(this.t('Джерело','Source'));
    this.field(source,this.t('Плеєр','Media player'),'entity',{kind:'entity',domains:['media_player']});
    if(this.display){
      this.field(source,this.t('Перемикач кімнати','Room selector'),'room_selector',{kind:'entity',domains:['input_select','select']});
      this.field(source,this.t('Перемикач джерела','Source selector'),'source_selector',{kind:'entity',domains:['input_select','select']});
      this.field(source,this.t('Назва джерела YouTube','YouTube source name'),'youtube_source',{placeholder:'YouTube'});
      const hint=document.createElement('p');hint.textContent=this.t('Для вибору кімнат залиште поле «Плеєр» порожнім.','Leave Media player empty to use room selection.');source.append(hint);
      this.roomEditor(source);
    }
    const inner=this.display, lyr=this.section(this.t('Лірика та синхронізація','Lyrics and synchronization'));
    this.field(lyr,this.t('Розмір тексту, px','Text size, px'),'font_size',{inner,kind:'number',min:12,max:48,step:1});
    this.field(lyr,this.t('Розмір перекладу, px','Translation size, px'),'translation_font_size',{inner,kind:'number',min:10,max:40,step:1});
    this.field(lyr,this.t('Зміщення синхронізації, с','Synchronization offset, s'),'sync_offset',{inner,kind:'number',step:0.1});
    this.field(lyr,this.t('Показувати режим','Show mode'),'show_mode',{inner,kind:'checkbox',defaultValue:true});
    this.field(lyr,this.t('Підганяти текст до ширини','Fit text to width'),'fit_synced',{inner,kind:'checkbox',defaultValue:this.display});
    const styleGroup=this.section(this.t('Вигляд','Appearance'));
    this.field(styleGroup,this.t('Мова інтерфейсу','Interface language'),'language',{inner,kind:'select',choices:[['',this.t('Як у Home Assistant','Home Assistant default')],['uk','Українська'],['en','English']]});
    this.field(styleGroup,this.t('Стиль Nest','Nest style'),'nest_style',{inner,kind:'checkbox',defaultValue:this.display});
    if(!this.display)this.field(styleGroup,this.t('Висота картки','Card height'),'card_height',{placeholder:'320px'});
  }
}
customElements.define('nest-lyric-editor',NestLyricEditor);
