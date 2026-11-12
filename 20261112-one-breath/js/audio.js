// Sound, all synthesised: room tone, breath, the swish of a stirring finger, and the pop.
// Nothing plays until the first press, as browsers require.

export class Sound {
  constructor() { this.ctx = null; }

  start() {
    if (this.ctx) { this.ctx.resume(); return; }
    const ctx = (this.ctx = new (window.AudioContext || window.webkitAudioContext)());
    this.out = ctx.createGain();
    this.out.gain.value = 0.9;
    this.out.connect(ctx.destination);
    this.noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const d = this.noise.getChannelData(0);
    let b = 0;
    for (let i = 0; i < d.length; i++) { b = 0.97 * b + 0.03 * (Math.random() * 2 - 1); d[i] = b * 4; }

    // room tone: a quiet low hush
    this.room = this.loopNoise(220, 0.5, 0.05);
    // breath and swish, both silent until used
    this.breath = this.loopNoise(900, 0.8, 0);
    this.swish = this.loopNoise(2400, 1.2, 0);

    // a slow, glassy chord that brightens as the film thins
    this.pad = ctx.createGain();
    this.pad.gain.value = 0;
    this.padTone = ctx.createBiquadFilter();
    this.padTone.type = 'lowpass';
    this.padTone.frequency.value = 600;
    this.pad.connect(this.padTone).connect(this.out);
    for (const [f, g] of [[196, 0.5], [293.7, 0.35], [440, 0.22], [587.3, 0.12]]) {
      const o = ctx.createOscillator(), og = ctx.createGain();
      o.type = 'sine'; o.frequency.value = f; o.detune.value = (Math.random() - 0.5) * 8;
      og.gain.value = g;
      o.connect(og).connect(this.pad);
      o.start();
    }
  }

  loopNoise(freq, q, gain) {
    const ctx = this.ctx;
    const src = ctx.createBufferSource();
    src.buffer = this.noise; src.loop = true;
    const f = ctx.createBiquadFilter();
    f.type = 'bandpass'; f.frequency.value = freq; f.Q.value = q;
    const g = ctx.createGain(); g.gain.value = gain;
    src.connect(f).connect(g).connect(this.out);
    src.start();
    return { g, f };
  }

  set(node, v, tc = 0.08) {
    if (this.ctx) node.setTargetAtTime(v, this.ctx.currentTime, tc);
  }

  blowing(level) { if (this.ctx) { this.set(this.breath.g.gain, level * 0.35); this.set(this.breath.f.frequency, 700 + level * 500); } }
  stirring(speed) { if (this.ctx) this.set(this.swish.g.gain, Math.min(0.12, speed * 0.6), 0.05); }
  // alive: 0..1 bubble presence; thin: 0..1 how far it has thinned
  mood(alive, thin) {
    if (!this.ctx) return;
    this.set(this.pad.gain, alive * 0.045, 0.8);
    this.set(this.padTone.frequency, 500 + thin * 2600, 1.5);
  }

  // The pop as heard in slow motion: a soft low tear, then droplets ticking.
  pop(slow) {
    if (!this.ctx) return;
    const ctx = this.ctx, t = ctx.currentTime;
    const src = ctx.createBufferSource(); src.buffer = this.noise;
    src.playbackRate.value = slow ? 0.35 : 1;
    const f = ctx.createBiquadFilter(); f.type = 'lowpass';
    f.frequency.setValueAtTime(slow ? 1800 : 6000, t);
    f.frequency.exponentialRampToValueAtTime(120, t + (slow ? 1.6 : 0.15));
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(0.9, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.001, t + (slow ? 1.8 : 0.2));
    src.connect(f).connect(g).connect(this.out);
    src.start(t); src.stop(t + 2);
    this.set(this.pad.gain, 0, 0.3);
  }

  drip(pan) {
    if (!this.ctx) return;
    const ctx = this.ctx, t = ctx.currentTime;
    const o = ctx.createOscillator(), g = ctx.createGain(), p = ctx.createStereoPanner();
    o.type = 'sine';
    o.frequency.setValueAtTime(1800 + Math.random() * 2400, t);
    o.frequency.exponentialRampToValueAtTime(600, t + 0.08);
    g.gain.setValueAtTime(0.03 + Math.random() * 0.03, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.12);
    p.pan.value = Math.max(-1, Math.min(1, pan));
    o.connect(g).connect(p).connect(this.out);
    o.start(t); o.stop(t + 0.15);
  }
}
