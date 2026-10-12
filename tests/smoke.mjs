import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
const root=dirname(dirname(fileURLToPath(import.meta.url)));
const js=readFileSync(join(root,'app.js'),'utf8');
const prefix=js.slice(0,js.indexOf("const root=$('#app')"));
const ctx=vm.createContext({console,Array,Math,Intl,Date});
vm.runInContext(prefix,ctx,{timeout:5000});
for(const [fn,text] of [['homePage','Docker'],['servicesPage','OpenCode'],['monitoringPage','CPU'],['storagePage','Хранилище'],['networkPage','Tailscale'],['agentsPage','OpenCode'],['settingsPage','Настройки']]){
  const html=vm.runInContext(fn+'()',ctx,{timeout:5000});
  assert.equal(typeof html,'string');
  assert(html.includes(text),`${fn} missing ${text}`);
}
const home=vm.runInContext('homePage()',ctx);
assert.equal((home.match(/class="glass feature"/g)||[]).length,7);
assert(home.includes('film-neon.svg'));
assert(home.includes('photo-lake.svg'));
assert(home.includes('data-greeting'));
for(const name of ['film-neon','film-voyage','film-dunes','photo-aurora','photo-lake','photo-forest','aurora-landscape']) assert(existsSync(join(root,'assets',name+'.svg')),name+' asset missing');
for(const name of ['styles.css','liquid-glass.css','glass-refraction.css','glass-v05.css']) assert(existsSync(join(root,name)),name+' css missing');
console.log('PASS 7 pages, 7 tiles, local assets, dynamic greeting and CSS layers');
