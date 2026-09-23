import argparse, os, tempfile, requests, torch, torchaudio
from chatterbox.tts import ChatterboxTTS
p=argparse.ArgumentParser();p.add_argument('--job-id',required=True);p.add_argument('--text',required=True);p.add_argument('--voice-url',required=True);p.add_argument('--callback-url',required=True);p.add_argument('--callback-token',required=True);a=p.parse_args()
try:
    with tempfile.TemporaryDirectory() as d:
        ref=os.path.join(d,'reference'); out=os.path.join(d,'output.wav')
        r=requests.get(a.voice_url,timeout=60);r.raise_for_status();open(ref,'wb').write(r.content)
        device='cuda' if torch.cuda.is_available() else 'cpu'
        model=ChatterboxTTS.from_pretrained(device=device)
        wav=model.generate(a.text,audio_prompt_path=ref)
        torchaudio.save(out,wav,model.sr)
        with open(out,'rb') as f: requests.post(a.callback_url,headers={'X-Echo-Token':a.callback_token},files={'audio':('echo.wav',f,'audio/wav')},timeout=120).raise_for_status()
except Exception as e:
    try: requests.post(a.callback_url,headers={'X-Echo-Token':a.callback_token},json={'error':str(e)[:1000]},timeout=30)
    finally: raise
