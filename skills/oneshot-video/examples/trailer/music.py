import numpy as np, soundfile as sf, sys
SR=48000; BPM=120; B=60/BPM; T=32.0; N=int(SR*T)
L=np.zeros(N); R=np.zeros(N)
rng=np.random.default_rng(7)
def add(sig,t,gl=1.0,gr=None):
    i=int(t*SR); j=min(N,i+len(sig)); 
    if i>=N: return
    L[i:j]+=sig[:j-i]*gl; R[i:j]+=sig[:j-i]*(gl if gr is None else gr)
def kick():
    n=int(0.45*SR); t=np.arange(n)/SR
    f=45+110*np.exp(-t*28); ph=2*np.pi*np.cumsum(f)/SR
    return np.sin(ph)*np.exp(-t*7)*0.9
def clap():
    n=int(0.25*SR); t=np.arange(n)/SR; x=rng.standard_normal(n)
    from scipy.signal import butter,sosfilt
    x=sosfilt(butter(2,[900,4000],'bandpass',fs=SR,output='sos'),x)
    env=np.exp(-t*22)*(1+0.6*np.exp(-((t-0.012)/0.004)**2))
    return x*env*0.5
def hat(open_=False):
    n=int((0.18 if open_ else 0.05)*SR); t=np.arange(n)/SR
    from scipy.signal import butter,sosfilt
    x=sosfilt(butter(4,7000,'highpass',fs=SR,output='sos'),rng.standard_normal(n))
    return x*np.exp(-t*(14 if open_ else 70))*0.22
def saw(freq,dur,cut):
    from scipy.signal import butter,sosfilt
    n=int(dur*SR); t=np.arange(n)/SR
    x=sum(((t*freq*d)%1*2-1) for d in (0.997,1.0,1.003))/3
    x=sosfilt(butter(2,cut,'lowpass',fs=SR,output='sos'),x)
    a=np.minimum(1,t/0.01); r=np.minimum(1,(dur-t)/0.05)
    return x*a*r
notes={'A':55.0,'F':43.65,'C':65.41,'G':49.0}
chords={'A':[220,261.63,329.63],'F':[174.61,220,261.63],'C':[261.63,329.63,392],'G':[196,246.94,293.66]}
prog=['A','F','C','G']
for bar in range(16):
    t0=bar*2*B*2/2  # 2 s per bar
    t0=bar*2.0
    ch=prog[bar%4]
    full = 2<=bar<=11 or bar>=13
    build = bar==12
    # pad
    if bar<13 or bar>=13:
        pad=sum(saw(f,2.0,1200 if bar>=2 else 700) for f in chords[ch])/3*0.10
        add(pad,t0,1.0,0.9)
    for b in range(4):
        tb=t0+b*B
        if full and not (bar>=13 and bar>14): add(kick(),tb)
        if full and b in (1,3): add(clap(),tb,0.8,1.0)
        for e in (0,0.5):
            if bar>=1: add(hat(e==0.5 and b==3),tb+e*B,0.7 if e else 0.5,0.5 if e else 0.7)
        if full:
            add(saw(notes[ch]*(2 if b%2 else 1),B*0.45,500)*0.35,tb+0.25*B)
    if build:
        for k in range(16):
            add(clap()*(0.3+0.7*k/16),t0+k*B/4)
        n=int(2.0*SR); t=np.arange(n)/SR
        from scipy.signal import butter,sosfilt
        x=sosfilt(butter(2,[400,6000],'bandpass',fs=SR,output='sos'),rng.standard_normal(n))*(t/2)**2*0.35
        add(x,t0)
# impact at 26.0
n=int(2.5*SR); t=np.arange(n)/SR
boom=np.sin(2*np.pi*np.cumsum(40+80*np.exp(-t*12))/SR)*np.exp(-t*2.2)
add(boom*1.0,26.0); add(clap()*1.2,26.0)
# fade tail after 30
fade=np.ones(N); i=int(30.5*SR); fade[i:]=np.linspace(1,0,N-i)
mix=np.stack([L*fade,R*fade],1); mix/=np.abs(mix).max()/0.89
sf.write(sys.argv[1],mix,SR,subtype='PCM_24')
