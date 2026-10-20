import json,numpy as np,soundfile as sf
from chatterbox.tts import ChatterboxTTS
PH=[["Your Instagram feed loads in under a second...","but the server is thousands of kilometres away.","So how?"],
["One word.","Caching."],
["Here's the slow way.","Every time you open the app, it asks the database.","Again. And again.","Every single time."],
["Now imagine keeping a copy...","right next to you.","First visit? Slow.","Second visit? Instant!"],
["But wait...","can you spot the problem?"],
["You change your profile picture.","But your friends...","still see the old one."],
["That's stale data.","The cache is lying to you."],
["So smart apps give every copy an expiry timer.","For example, ten minutes.","Then it refreshes."],
["And when something really changes?","Delete the copy.","Fetch the fresh one."],
["Fast when it can be.","Fresh when it has to be."],
["Would you pick speed, or freshness?","Comment below.","And follow for more!"]]
def trim(w,sr):
    i=np.where(np.abs(w)>0.01)[0];return w[max(i[0]-int(.01*sr),0):i[-1]+int(.05*sr)]
m=ChatterboxTTS.from_pretrained(device="cpu");sr=m.sr;out=[];t=0;tim=[]
for li,phs in enumerate(PH):
    for pi,p in enumerate(phs):
        w=trim(m.generate(p,audio_prompt_path="orp/zac.wav",exaggeration=0.6,cfg_weight=0.3).squeeze(0).numpy(),sr)
        g=0.3 if pi<len(phs)-1 else 0.55
        if p.endswith("..."): g=0.45
        if li==4 and pi==1: g=0.9
        tim.append({"li":li,"show":p,"start":round(t,3),"end":round(t+len(w)/sr,3)});out+=[w,np.zeros(int(g*sr))];t+=len(w)/sr+g
        print("ok",li,pi,flush=True)
sf.write("cache/raw.wav",np.concatenate(out),sr);json.dump(tim,open("cache/tim.json","w"),indent=1);print("done",round(t,1),flush=True)
