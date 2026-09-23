import json, os, secrets, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_from_directory
import requests

ROOT=Path(__file__).parent
JOBS=ROOT/'data/jobs'; AUDIO=ROOT/'data/audio'; VOICES=ROOT/'data/voices'
for p in (JOBS,AUDIO,VOICES): p.mkdir(parents=True,exist_ok=True)
app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=20*1024*1024

def save_job(j):
    (JOBS/f"{j['id']}.json").write_text(json.dumps(j,indent=2),encoding='utf-8')
def load_job(i):
    p=JOBS/f'{i}.json'
    return json.loads(p.read_text()) if p.exists() else None

def dispatch(job):
    token=os.getenv('GITHUB_TOKEN'); repo=os.getenv('GITHUB_REPOSITORY'); branch=os.getenv('GITHUB_BRANCH','main')
    if not token or not repo: return False, 'GITHUB_TOKEN/GITHUB_REPOSITORY not configured'
    url=f'https://api.github.com/repos/{repo}/actions/workflows/tts.yml/dispatches'
    r=requests.post(url,headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},json={'ref':branch,'inputs':{'job_id':job['id'],'text':job['text'],'voice_url':job['voice_url'],'callback_url':job['callback_url'],'callback_token':os.getenv('CALLBACK_TOKEN','')}},timeout=20)
    return r.status_code==204, ('' if r.status_code==204 else f'GitHub {r.status_code}: {r.text[:300]}')

@app.get('/')
def home(): return render_template('index.html')
@app.get('/health')
def health(): return {'ok':True,'service':'Echo Voice'}

@app.post('/api/voices')
def voice():
    f=request.files.get('voice')
    if not f or not f.filename: return jsonify(error='Choose a reference recording.'),400
    ext=Path(f.filename).suffix.lower() or '.wav'
    if ext not in {'.wav','.mp3','.m4a','.ogg','.webm','.aac'}: return jsonify(error='Unsupported audio type.'),400
    vid=secrets.token_hex(10); path=VOICES/f'{vid}{ext}'; f.save(path)
    base=request.host_url.rstrip('/')
    return {'id':vid,'url':f'{base}/api/voices/{path.name}','name':f.filename}
@app.get('/api/voices/<name>')
def get_voice(name): return send_from_directory(VOICES,name,as_attachment=False)

@app.post('/api/jobs')
def create_job():
    d=request.get_json(silent=True) or {}; text=(d.get('text') or '').strip(); voice_url=(d.get('voice_url') or '').strip()
    if not text: return jsonify(error='Enter some text.'),400
    if len(text)>1800: return jsonify(error='Keep V1 generations under 1,800 characters.'),400
    if not voice_url: return jsonify(error='Upload a reference voice first.'),400
    jid=secrets.token_hex(8); base=request.host_url.rstrip('/')
    job={'id':jid,'text':text,'voice_url':voice_url,'status':'queued','created_at':datetime.now(timezone.utc).isoformat(),'audio_url':None,'error':None,'callback_url':f'{base}/api/jobs/{jid}/complete'}
    save_job(job); ok,err=dispatch(job)
    if not ok: job['status']='failed'; job['error']=err; save_job(job); return jsonify(job),503
    return jsonify(job),202
@app.get('/api/jobs/<jid>')
def job(jid):
    j=load_job(jid); return (jsonify(j),200) if j else (jsonify(error='Not found'),404)
@app.post('/api/jobs/<jid>/complete')
def complete(jid):
    if request.headers.get('X-Echo-Token','') != os.getenv('CALLBACK_TOKEN',''): return jsonify(error='Unauthorized'),401
    j=load_job(jid)
    if not j: return jsonify(error='Not found'),404
    if 'audio' in request.files:
        f=request.files['audio']; name=f'{jid}.wav'; f.save(AUDIO/name); j['audio_url']=f'/api/audio/{name}'; j['status']='done'; j['error']=None
    else:
        d=request.get_json(silent=True) or {}; j['status']='failed'; j['error']=d.get('error','Generation failed')
    save_job(j); return {'ok':True}
@app.get('/api/audio/<name>')
def audio(name): return send_from_directory(AUDIO,name,as_attachment=False)

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')))
