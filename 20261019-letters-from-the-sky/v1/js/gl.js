// Minimal WebGL2 helpers: fullscreen-triangle programs, float render targets.
export const VS = `#version 300 es
in vec2 p; out vec2 uv; void main(){ uv = p*.5+.5; gl_Position = vec4(p,0,1); }`;

export function createGL(canvas, opts = {}) {
  const gl = canvas.getContext('webgl2', Object.assign({ antialias: false, alpha: false, premultipliedAlpha: false, preserveDrawingBuffer: false }, opts));
  if (!gl) throw new Error('WebGL2 is required');
  if (!gl.getExtension('EXT_color_buffer_float')) throw new Error('EXT_color_buffer_float is required');
  gl.getExtension('OES_texture_float_linear');
  const vb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vb);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.__vao = vao;
  return gl;
}

function shader(gl, type, src) {
  const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(s);
    const lines = src.split('\n').map((l, i) => (i + 1) + ': ' + l).join('\n');
    throw new Error(log + '\n' + lines);
  }
  return s;
}

export function program(gl, fs, vs = VS) {
  const p = gl.createProgram();
  gl.attachShader(p, shader(gl, gl.VERTEX_SHADER, vs)); gl.attachShader(p, shader(gl, gl.FRAGMENT_SHADER, fs));
  gl.bindAttribLocation(p, 0, 'p'); gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
  const u = {}; const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) { const a = gl.getActiveUniform(p, i); u[a.name.replace(/\[0\]$/, '')] = gl.getUniformLocation(p, a.name); }
  return { p, u };
}

export function target(gl, w, h, { internal = gl.RGBA16F, format = gl.RGBA, type = gl.HALF_FLOAT, filter = gl.LINEAR, wrap = gl.CLAMP_TO_EDGE } = {}) {
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texImage2D(gl.TEXTURE_2D, 0, internal, w, h, 0, format, type, null);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap);
  const f = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, f);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
  return { t, f, w, h };
}

// Run a fullscreen pass. tex: {name: texture}, uni: {name: number|array}
export function pass(gl, prog, dst, tex = {}, uni = {}, vp) {
  gl.useProgram(prog.p);
  gl.bindFramebuffer(gl.FRAMEBUFFER, dst ? dst.f : null);
  if (vp) gl.viewport(vp[0], vp[1], vp[2], vp[3]);
  else gl.viewport(0, 0, dst ? dst.w : gl.drawingBufferWidth, dst ? dst.h : gl.drawingBufferHeight);
  let unit = 0;
  for (const k in tex) {
    if (prog.u[k] == null) continue;
    gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, tex[k].t || tex[k]); gl.uniform1i(prog.u[k], unit); unit++;
  }
  for (const k in uni) {
    const loc = prog.u[k]; if (loc == null) continue; const v = uni[k];
    if (typeof v === 'number') gl.uniform1f(loc, v);
    else if (v.length === 2) gl.uniform2fv(loc, v); else if (v.length === 3) gl.uniform3fv(loc, v);
    else if (v.length === 4) gl.uniform4fv(loc, v); else if (v.length === 9) gl.uniformMatrix3fv(loc, false, v); else gl.uniform1fv(loc, v);
  }
  gl.drawArrays(gl.TRIANGLES, 0, 3);
}
