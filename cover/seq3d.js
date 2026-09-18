/* SEQUENCE — cube-to-snow-crystal glass chain (raymarched SDF, WebGL1).
   The distance field below was tuned against a CPU reference render; the
   constants are load-bearing, in particular the fold weights in stageDE:
   a fold applied at partial strength shatters the solid into dust, so the
   schedule is set up to land on exactly two fully-applied folds at m = 1. */
(function () {
  'use strict';

  var VERT = 'attribute vec2 aPos;void main(){gl_Position=vec4(aPos,0.0,1.0);}';

  var FRAG = [
'precision highp float;',
'uniform vec2  uRes;',
'uniform vec3  uCam;',
'uniform vec3  uTgt;',
'uniform vec2  uFov;',
'uniform int   uCount;',
'uniform vec3  uC0;',
'uniform vec3  uC1;',
'uniform vec3  uC2;',
'uniform vec3  uC3;',
'uniform float uMorphMode;',
'uniform vec2  uScaleRange;',
'uniform float uTwist;',
'uniform float uSpin;',
'uniform vec3  uColA;',
'uniform vec3  uColB;',
'uniform float uGlow;',
'uniform float uTheme;',
'uniform vec4  uOrphan;',
'uniform float uFuse;',
'uniform float uSteps;',
'',
'float gT;',
'',
'mat3 rotY(float a){float c=cos(a),s=sin(a);return mat3(c,0.0,-s, 0.0,1.0,0.0, s,0.0,c);}',
'mat3 rotX(float a){float c=cos(a),s=sin(a);return mat3(1.0,0.0,0.0, 0.0,c,s, 0.0,-s,c);}',
'mat3 rotZ(float a){float c=cos(a),s=sin(a);return mat3(c,s,0.0, -s,c,0.0, 0.0,0.0,1.0);}',
'',
'vec3 bez(float t){float u=1.0-t;return u*u*u*uC0+3.0*u*u*t*uC1+3.0*u*t*t*uC2+t*t*t*uC3;}',
'float smin(float a,float b,float k){float h=clamp(0.5+0.5*(b-a)/k,0.0,1.0);return mix(b,a,h)-k*h*(1.0-h);}',
'',
'float rbox(vec3 p,float b,float r){',
'  vec3 q=abs(p)-vec3(b-r);',
'  return length(max(q,0.0))+min(max(q.x,max(q.y,q.z)),0.0)-r;',
'}',
'',
/* The solid every scale of the fractal is built from.
     open  0 solid            -> 1 bored through by a thick gyroid channel
     soft  0 crisp cube edges -> 1 pillowed
     sharp 0 rounded          -> 1 faceted, with octahedral spikes */
'float baseSolid(vec3 p,float open,float soft,float sharp,float tw){',
'  float ct=cos(p.y*tw), st=sin(p.y*tw);',
'  p.xz=mat2(ct,st,-st,ct)*p.xz;',
'  float b=mix(1.0,1.05,open)*(1.0+0.16*sharp);',
'  float r=mix(0.06,0.62,soft)*(1.0-0.86*sharp)+0.03;',
'  float shell=rbox(p,b,r);',
'  float oct=(abs(p.x)+abs(p.y)+abs(p.z)-b*1.86)*0.57735;',
'  shell=min(shell,mix(1.0e4,oct,sharp));',
'  float f=mix(1.02,1.55,open);',
'  float g=sin(p.x*f)*cos(p.y*f)+sin(p.y*f)*cos(p.z*f)+sin(p.z*f)*cos(p.x*f);',
'  float thick=mix(1.75,0.82,open);',
'  return max(shell,(abs(g)-thick)/(f*1.75));',
'}',
'',
/* m = 0 : plain cube.  m = 1 : dendritic snow crystal (3D Vicsek, spiked cells). */
'float stageDE(vec3 p,float m){',
'  float s=1.0;',
'  for(int n=0;n<3;n++){',
'    float a=clamp(m*7.333-5.133-float(n)*1.15,0.0,1.0);',
'    if(a<=0.002) break;',
'    vec3 q=abs(p);',
'    if(q.x<q.y) q.xy=q.yx;',
'    if(q.x<q.z) q.xz=q.zx;',
'    if(q.y<q.z) q.yz=q.zy;',
'    q*=3.0;',
'    if(q.x>1.0) q.x-=2.0;',
'    p=mix(p,q,a);',
'    s*=mix(1.0,3.0,a);',
'  }',
'  float sharp=smoothstep(0.70,1.0,m);',
'  float open =smoothstep(0.0,0.50,m)*(1.0-0.62*sharp);',
'  float soft =smoothstep(0.0,0.38,m)*(1.0-0.30*sharp);',
'  float tw   =uTwist*smoothstep(0.05,0.60,m)*(1.0-0.55*sharp);',
'  return baseSolid(p,open,soft,sharp,tw)/s;',
'}',
'',
'float stageM(float t){ return (uMorphMode>0.5)?abs(2.0*t-1.0):t; }',
'',
'float map(vec3 p){',
'  float d=1e9;',
'  float N=max(float(uCount)-1.0,1.0);',
'  for(int i=0;i<10;i++){',
'    if(i>=uCount) break;',
'    float t=float(i)/N;',
'    float m=stageM(t);',
'    vec3 c=bez(t);',
'    float sc=mix(uScaleRange.x,uScaleRange.y,m);',
'    float bd=length(p-c)-sc*2.35;',
'    if(bd>0.25){ d=min(d,bd); continue; }',
'    mat3 R=rotY(uSpin*(t*2.3+float(i)*0.31))*rotX(uSpin*(t*1.25+float(i)*0.19))*rotZ(float(i)*0.26);',
'    float di=stageDE(R*(p-c)/sc,m)*sc;',
'    if(di<d) gT=t;',
'    d=smin(d,di,uFuse);',
'  }',
'  if(uOrphan.w>0.0){',
'    float bd=length(p-uOrphan.xyz)-uOrphan.w*2.35;',
'    if(bd>0.25){ d=min(d,bd); }',
'    else {',
'      float di=stageDE(rotY(0.62)*rotX(0.30)*(p-uOrphan.xyz)/uOrphan.w,0.0)*uOrphan.w;',
'      if(di<d) gT=0.0;',
'      d=min(d,di);',
'    }',
'  }',
'  return d;',
'}',
'',
'vec3 nrm(vec3 p){',
'  vec2 e=vec2(1.0,-1.0)*0.0016;',
'  return normalize(e.xyy*map(p+e.xyy)+e.yyx*map(p+e.yyx)+e.yxy*map(p+e.yxy)+e.xxx*map(p+e.xxx));',
'}',
'',
/* Lighting dome is bright even on the dark cover: the backdrop is drawn
   separately, so the glass reads as glass instead of chrome. */
'vec3 envMap(vec3 rd){',
'  float y=rd.y*0.5+0.5;',
'  vec3 base=(uTheme>0.5)',
'    ? mix(vec3(0.34,0.37,0.46),vec3(1.00,1.01,1.08),y)',
'    : mix(vec3(0.26,0.30,0.40),vec3(0.92,0.95,1.06),y);',
'  base+=pow(max(dot(rd,normalize(vec3(-0.50,0.78,-0.38))),0.0),26.0)*vec3(3.4,3.5,3.8);',
'  base+=pow(max(dot(rd,normalize(vec3(0.78,0.12,0.52))),0.0),14.0)*mix(uColA,uColB,0.55)*2.4;',
'  base+=pow(max(dot(rd,normalize(vec3(0.15,-0.88,0.26))),0.0),9.0)*uColA*0.70;',
'  return base;',
'}',
'',
'vec3 bg(vec2 uv){',
'  float r=clamp(length(uv*vec2(1.0,1.25))*1.15,0.0,1.0);',
'  return (uTheme>0.5)',
'    ? mix(vec3(0.985,0.985,0.995),vec3(0.880,0.890,0.930),r)',
'    : mix(vec3(0.045,0.052,0.080),vec3(0.006,0.008,0.016),r);',
'}',
'',
/* Halo from the analytic ray-to-object closest approach. Accumulating it
   along the march instead puts visible step-contour rings in the backdrop. */
'vec3 halo(vec3 ro,vec3 rd){',
'  vec3 h=vec3(0.0);',
'  float N=max(float(uCount)-1.0,1.0);',
'  for(int i=0;i<10;i++){',
'    if(i>=uCount) break;',
'    float t=float(i)/N;',
'    vec3 oc=bez(t)-ro;',
'    float proj=dot(oc,rd);',
'    if(proj<=0.0) continue;',
'    float sc=mix(uScaleRange.x,uScaleRange.y,stageM(t));',
'    float dd=max(sqrt(max(dot(oc,oc)-proj*proj,0.0))-sc*1.05,0.0);',
'    h+=mix(uColA,uColB,clamp(t,0.0,1.0))*(exp(-dd*4.4)*0.40+exp(-dd*1.7)*0.055);',
'  }',
'  if(uOrphan.w>0.0){',
'    vec3 oc=uOrphan.xyz-ro;',
'    float proj=dot(oc,rd);',
'    if(proj>0.0){',
'      float dd=max(sqrt(max(dot(oc,oc)-proj*proj,0.0))-uOrphan.w*1.05,0.0);',
'      h+=uColA*(exp(-dd*4.4)*0.40+exp(-dd*1.7)*0.055);',
'    }',
'  }',
'  return h;',
'}',
'',
'vec3 aces(vec3 x){return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0);}',
'',
'void main(){',
'  vec2 uv=(gl_FragCoord.xy-0.5*uRes)/uRes;',
'  vec3 fw=normalize(uTgt-uCam);',
'  vec3 rt=normalize(cross(fw,vec3(0.0,1.0,0.0)));',
'  vec3 up=cross(rt,fw);',
'  vec3 rd=normalize(fw+rt*(uv.x*uFov.x)+up*(uv.y*uFov.y));',
'  vec3 ro=uCam;',
'',
'  float ABS  =(uTheme>0.5)?1.60:1.10;',
'  float MILK =(uTheme>0.5)?0.13:0.22;',
'  float GLW  =((uTheme>0.5)?0.40:1.00)*uGlow;',
'  const float IOR=1.47;',
'  const float DISP=0.018;',
'',
'  float t=0.0; bool hit=false; float hitT=0.0; gT=0.0;',
'  for(int i=0;i<150;i++){',
'    if(float(i)>uSteps) break;',
'    float d=map(ro+rd*t);',
'    if(d<0.0016){ hit=true; hitT=gT; break; }',
'    t+=d*0.50;',
'    if(t>48.0) break;',
'  }',
'',
'  vec3 col;',
'  if(hit){',
'    vec3 p=ro+rd*t;',
'    vec3 n=nrm(p);',
'    vec3 tint=mix(uColA,uColB,clamp(hitT,0.0,1.0));',
'    float fres=0.035+0.965*pow(1.0-clamp(dot(-rd,n),0.0,1.0),5.0);',
'    vec3 refl=envMap(reflect(rd,n));',
'    vec3 refr=refl;',
'    vec3 rdIn=refract(rd,n,1.0/IOR);',
'    if(dot(rdIn,rdIn)>0.0001){',
'      vec3 ip=p-n*0.010;',
'      float it=0.0;',
'      for(int j=0;j<40;j++){',
'        float dd=-map(ip+rdIn*it);',
'        if(dd<0.0018) break;',
'        it+=max(dd*0.82,0.006);',
'        if(it>8.0) break;',
'      }',
'      vec3 ep=ip+rdIn*it;',
'      vec3 en=-nrm(ep);',
'      vec3 tir=reflect(rdIn,en);',
'      vec3 o1=refract(rdIn,en,IOR*(1.0-DISP));',
'      vec3 o2=refract(rdIn,en,IOR);',
'      vec3 o3=refract(rdIn,en,IOR*(1.0+DISP));',
'      vec3 e1=(dot(o1,o1)>0.0001)?envMap(o1):envMap(tir);',
'      vec3 e2=(dot(o2,o2)>0.0001)?envMap(o2):envMap(tir);',
'      vec3 e3=(dot(o3,o3)>0.0001)?envMap(o3):envMap(tir);',
'      refr=vec3(e1.r,e2.g,e3.b);',
'      refr=refr*exp(-ABS*it*(vec3(1.0)-tint))+tint*it*0.17;',
'      refr=mix(refr,tint*1.15,MILK);',
'    }',
'    col=mix(refr,refl,fres);',
'    col+=pow(max(dot(reflect(rd,n),normalize(vec3(-0.50,0.78,-0.38))),0.0),110.0)*2.8;',
'    col+=tint*pow(1.0-clamp(dot(-rd,n),0.0,1.0),3.0)*0.42;',
'    col+=halo(ro,rd)*GLW*0.30;',
'  } else {',
'    col=bg(uv)+halo(ro,rd)*GLW;',
'  }',
'  col=aces(col*1.02);',
'  float vig=1.0-0.20*pow(length(uv*vec2(1.05,1.25))*1.25,2.2);',
'  col*=clamp(vig,0.0,1.0);',
'  col+=(fract(sin(dot(gl_FragCoord.xy,vec2(12.9898,78.233)))*43758.5453)-0.5)/255.0;',
'  gl_FragColor=vec4(col,1.0);',
'}'
  ].join('\n');

  /* ---------- layout presets (world units, camera distance 17) ---------- */
  var LAYOUTS = {
    /* Option B — the whole sequence resolves inside the front cover,
       with the opening cube left alone on the back cover. */
    front: {
      c0: [0.95, -2.70, 0.35], c1: [2.10, -1.70, -0.90],
      c2: [3.60, 0.70, 0.85],  c3: [4.60, 2.15, -0.30],
      scale: [0.40, 0.88], morphMode: 0, orphan: [-3.05, -0.25, 0.0, 0.55], frameH: 8.2
    },
    /* Front cover on its own — portrait diagonal, no orphan. */
    portrait: {
      c0: [-1.55, -2.90, 0.40], c1: [-0.70, -1.80, -0.90],
      c2: [0.55, 0.90, 0.85],   c3: [1.50, 2.40, -0.30],
      scale: [0.40, 0.88], morphMode: 0, orphan: [0, 0, 0, 0], frameH: 8.2
    },
    /* Straight even row, for reading the morph stage by stage. */
    strip: {
      c0: [-5.40, 0, 0], c1: [-1.80, 0, 0], c2: [1.80, 0, 0], c3: [5.40, 0, 0],
      scale: [0.44, 0.62], morphMode: 0, orphan: [0, 0, 0, 0], frameH: 3.6
    }
  };

  function hex2rgb(h) {
    h = String(h || '').replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    if (isNaN(n)) return [1, 1, 1];
    return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  }

  function compile(gl, type, src) {
    var s = gl.createShader(type);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(s) || 'shader compile failed');
    }
    return s;
  }

  function mount(canvas, options) {
    var opts = {};
    var gl = null, prog = null, U = {}, raf = 0, tiles = 0, dragging = false, disposed = false;
    var lastX = 0, lastY = 0, spinRaf = 0;
    var TILES = 4;

    try {
      gl = canvas.getContext('webgl', {
        antialias: false, preserveDrawingBuffer: true,
        alpha: false, powerPreference: 'high-performance'
      });
    } catch (e) { gl = null; }
    if (!gl) { canvas.setAttribute('data-seq-error', '1'); return null; }

    try {
      prog = gl.createProgram();
      gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VERT));
      gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, FRAG));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
        throw new Error(gl.getProgramInfoLog(prog) || 'link failed');
      }
    } catch (e) {
      canvas.setAttribute('data-seq-error', '1');
      return null;
    }

    gl.useProgram(prog);
    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(prog, 'aPos');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    ['uRes', 'uCam', 'uTgt', 'uFov', 'uCount', 'uC0', 'uC1', 'uC2', 'uC3', 'uMorphMode',
     'uScaleRange', 'uTwist', 'uSpin', 'uColA', 'uColB', 'uGlow', 'uTheme', 'uOrphan',
     'uFuse', 'uSteps'
    ].forEach(function (k) { U[k] = gl.getUniformLocation(prog, k); });

    function sizeBuffer(quality) {
      var cssW = canvas.clientWidth || parseInt(canvas.getAttribute('width'), 10) || 800;
      var cssH = canvas.clientHeight || parseInt(canvas.getAttribute('height'), 10) || 600;
      var maxW = quality === 'low' ? 420 : 960;
      var s = Math.min(1, maxW / cssW);
      var w = Math.max(64, Math.round(cssW * s));
      var h = Math.max(64, Math.round(cssH * s));
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      return [w, h];
    }

    function setUniforms(size, quality) {
      var L = LAYOUTS[opts.layout] || LAYOUTS.front;
      var aspect = size[0] / size[1];
      var dist = 17.0;
      var yaw = (opts.yaw || 0) * Math.PI / 180;
      var pit = (opts.pitch || 0) * Math.PI / 180;
      var cam = [
        dist * Math.sin(yaw) * Math.cos(pit),
        dist * Math.sin(pit),
        dist * Math.cos(yaw) * Math.cos(pit)
      ];
      var fH = L.frameH * (opts.zoom || 1);
      gl.uniform2f(U.uRes, size[0], size[1]);
      gl.uniform3f(U.uCam, cam[0], cam[1], cam[2]);
      gl.uniform3f(U.uTgt, 0, 0, 0);
      gl.uniform2f(U.uFov, fH * aspect / dist, fH / dist);
      gl.uniform1i(U.uCount, Math.max(2, Math.min(10, opts.stages | 0)));
      gl.uniform3fv(U.uC0, L.c0); gl.uniform3fv(U.uC1, L.c1);
      gl.uniform3fv(U.uC2, L.c2); gl.uniform3fv(U.uC3, L.c3);
      gl.uniform1f(U.uMorphMode, L.morphMode);
      gl.uniform2fv(U.uScaleRange, L.scale);
      gl.uniform1f(U.uTwist, opts.twist);
      gl.uniform1f(U.uSpin, opts.spin);
      gl.uniform3fv(U.uColA, hex2rgb(opts.accentA));
      gl.uniform3fv(U.uColB, hex2rgb(opts.accentB));
      gl.uniform1f(U.uGlow, opts.glow);
      gl.uniform1f(U.uTheme, opts.theme === 'light' ? 1.0 : 0.0);
      gl.uniform4fv(U.uOrphan, L.orphan);
      gl.uniform1f(U.uFuse, Math.max(0.005, opts.fuse));
      gl.uniform1f(U.uSteps, quality === 'low' ? 72.0 : 142.0);
    }

    function drawTile(size, i, n) {
      var band = Math.ceil(size[1] / n);
      var y = i * band;
      gl.enable(gl.SCISSOR_TEST);
      gl.scissor(0, y, size[0], Math.min(band, size[1] - y));
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.disable(gl.SCISSOR_TEST);
    }

    function render(quality) {
      if (disposed || gl.isContextLost()) return;
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      var size = sizeBuffer(quality);
      gl.viewport(0, 0, size[0], size[1]);
      gl.useProgram(prog);
      setUniforms(size, quality);
      if (quality === 'low') { gl.drawArrays(gl.TRIANGLES, 0, 3); return; }
      tiles = 0;
      var step = function () {
        if (disposed || gl.isContextLost()) return;
        drawTile(size, tiles, TILES);
        tiles++;
        if (tiles < TILES) raf = requestAnimationFrame(step); else raf = 0;
      };
      raf = requestAnimationFrame(step);
    }

    function onDown(e) {
      dragging = true; lastX = e.clientX; lastY = e.clientY;
      if (canvas.setPointerCapture && e.pointerId != null) {
        try { canvas.setPointerCapture(e.pointerId); } catch (err) {}
      }
      e.preventDefault();
    }
    function onMove(e) {
      if (!dragging) return;
      var dx = e.clientX - lastX, dy = e.clientY - lastY;
      lastX = e.clientX; lastY = e.clientY;
      opts.yaw = Math.max(-75, Math.min(75, (opts.yaw || 0) + dx * 0.22));
      opts.pitch = Math.max(-55, Math.min(55, (opts.pitch || 0) - dy * 0.22));
      render('low');
    }
    function onUp() { if (!dragging) return; dragging = false; render('high'); }

    canvas.addEventListener('pointerdown', onDown);
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    canvas.addEventListener('pointercancel', onUp);

    function loopSpin() {
      if (disposed) return;
      opts.yaw = ((opts.yaw || 0) + 0.3 + 180) % 360 - 180;
      render('low');
      spinRaf = requestAnimationFrame(loopSpin);
    }

    var api = {
      update: function (next) {
        Object.keys(next || {}).forEach(function (k) { opts[k] = next[k]; });
        if (opts.autoSpin && !spinRaf) { spinRaf = requestAnimationFrame(loopSpin); return; }
        if (!opts.autoSpin && spinRaf) { cancelAnimationFrame(spinRaf); spinRaf = 0; }
        if (!opts.autoSpin) render('high');
      },
      render: render,
      destroy: function () {
        disposed = true;
        if (raf) cancelAnimationFrame(raf);
        if (spinRaf) cancelAnimationFrame(spinRaf);
        canvas.removeEventListener('pointerdown', onDown);
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
        canvas.removeEventListener('pointercancel', onUp);
      }
    };

    api.update(options || {});
    return api;
  }

  window.SEQ3D = { mount: mount, layouts: LAYOUTS };
})();
