/* SEQUENCE — cover object: glass cube, twisted split band, crystal cluster.
   Raymarched SDF, WebGL1. The field mirrors reference/form2.js, which is the
   CPU renderer the shape was developed against; change one, change the other.
   No bloom or halo anywhere: the object is lit, never emissive. */
(function () {
  'use strict';

  var VERT = 'attribute vec2 aPos;void main(){gl_Position=vec4(aPos,0.0,1.0);}';

  var FRAG = [
'precision highp float;',
'uniform vec2  uRes;',
'uniform vec3  uCam;',
'uniform vec3  uTgt;',
'uniform vec2  uFov;',
'uniform vec2  uTilt;',      /* az, ay — how the object lies on the cover */
'uniform float uScale;',
'uniform float uL;',
'uniform float uBend;',
'uniform float uNOpen;',
'uniform vec2  uHW;',
'uniform vec2  uHH;',
'uniform float uThick;',
'uniform float uTwist;',
'uniform float uTwistPhase;',
'uniform float uSlotW;',
'uniform float uWeld;',
'uniform vec3  uHead;',
'uniform float uHeadRot;',
'uniform float uCSize;',
'uniform float uCScale;',
'uniform float uCBase;',
'uniform float uCRot;',
'uniform vec4  uCube;',      /* xyz position, w half-size */
'uniform vec2  uCubeRot;',   /* about z, about y */
'uniform vec4  uEcho;',      /* the lone cube on the back cover; w<=0 = off */
'uniform vec3  uColA;',
'uniform vec3  uColB;',
'uniform vec3  uColC;',
'uniform float uTheme;',
'uniform float uSteps;',
'',
'#define PI 3.14159265',
'float gT;',
'mat3  gCM;',
'',
'float smin(float a,float b,float k){float h=clamp(0.5+0.5*(b-a)/k,0.0,1.0);return mix(b,a,h)-k*h*(1.0-h);}',
'',
'float rbox3(vec3 p,vec3 b,float r){',
'  vec3 q=abs(p)-(b-r);',
'  return length(max(q,0.0))+min(max(q.x,max(q.y,q.z)),0.0)-r;',
'}',
'float rrect(vec2 p,vec2 h,float r){',
'  r=min(r,min(h.x,h.y)*0.95);',
'  vec2 d=abs(p)-(h-r);',
'  return length(max(d,0.0))+min(max(d.x,d.y),0.0)-r;',
'}',
'',
/* Kaleidoscopic IFS with a rotation inside the fold. The rotation is what
   takes the lattice off the world axes and gives facets at many angles —
   without it the result reads as a stack of boxes, not a crystal. */
'float crystalDE(vec3 p){',
'  float s=1.0;',
'  for(int i=0;i<3;i++){',
'    vec3 q=abs(p);',
'    if(q.x<q.y) q.xy=q.yx;',
'    if(q.x<q.z) q.xz=q.zx;',
'    if(q.y<q.z) q.yz=q.zy;',
'    q=gCM*q;',
'    p=uCScale*q-vec3(uCScale-1.0);',
'    s*=uCScale;',
'  }',
'  return rbox3(p,vec3(uCBase),0.03)/s;',
'}',
'',
/* The band: a rounded rectangular section swept along x, twisting, with a
   through-slot that splits it into two braiding strands. uNOpen splits, each
   sitting inside a widened section. */
'float bandDE(vec3 p){',
'  float u=clamp((p.x+uL)/(2.0*uL),0.0,1.0);',
'  float yy=p.y-uBend*sin(u*PI);',
'  float w=abs(sin(u*PI*uNOpen));',
'  float grow=mix(0.86,1.0,smoothstep(0.0,0.6,u))*uThick;',
'  float hw=mix(uHW.x,uHW.y,w)*grow;',
'  float hh=mix(uHH.x,uHH.y,w)*grow;',
'  float th=uTwist*p.x+uTwistPhase;',
'  float ct=cos(th), st=sin(th);',
'  vec2 q=vec2(ct*yy+st*p.z, -st*yy+ct*p.z);',
'  float d=rrect(q,vec2(hw,hh),min(hw,hh)*0.85);',
'  float sw=hw*uSlotW*w;',
'  if(sw>0.004) d=max(d,-rrect(q,vec2(sw,hh*2.4),sw*0.6+0.01));',
'  float ex=abs(p.x)-uL;',
'  return min(max(d,ex),0.0)+length(max(vec2(d,ex),0.0));',
'}',
'',
'float headDE(vec3 p){',
'  vec3 d=(p-uHead)/uCSize;',
'  float c=cos(uHeadRot), s=sin(uHeadRot);',
'  return crystalDE(vec3(c*d.x-s*d.z, d.y, s*d.x+c*d.z))*uCSize;',
'}',
'',
/* The cube carries its own z rotation so that once the whole object is tilted
   onto the cover diagonal it still reads as a cube in three-quarter view. */
'float cubeAt(vec3 p,vec4 C,vec2 rot){',
'  vec3 d=p-C.xyz;',
'  float cz=cos(rot.x), sz=sin(rot.x);',
'  vec2 a=vec2(cz*d.x-sz*d.y, sz*d.x+cz*d.y);',
'  float cy=cos(rot.y), sy=sin(rot.y);',
'  return rbox3(vec3(cy*a.x-sy*d.z, a.y, sy*a.x+cy*d.z)/C.w, vec3(1.0), 0.05)*C.w;',
'}',
'',
'float objDE(vec3 p){',
'  return min(smin(bandDE(p),headDE(p),uWeld), cubeAt(p,uCube,uCubeRot));',
'}',
'',
'float map(vec3 p){',
'  float cz=cos(uTilt.x), sz=sin(uTilt.x), cy=cos(uTilt.y), sy=sin(uTilt.y);',
'  float x1=cy*p.x-sy*p.z, z1=sy*p.x+cy*p.z;',
'  float x2=cz*x1+sz*p.y,  y2=-sz*x1+cz*p.y;',
'  vec3 q=vec3(x2,y2,z1)/uScale;',
'  gT=clamp((q.x-uCube.x)/(uHead.x+0.6-uCube.x),0.0,1.0);',
'  float bs=(length(q-vec3(-0.3,0.0,0.0))-4.3)*uScale;',
'  float d=(bs>0.35)?bs:objDE(q)*uScale;',
'  if(uEcho.w>0.0){',
'    float e=cubeAt(p,uEcho,vec2(0.0,0.42));',
'    if(e<d){ d=e; gT=0.0; }',
'  }',
'  return d;',
'}',
'',
'vec3 nrm(vec3 p){',
'  vec2 e=vec2(1.0,-1.0)*0.0018;',
'  return normalize(e.xyy*map(p+e.xyy)+e.yyx*map(p+e.yyx)+e.yxy*map(p+e.yxy)+e.xxx*map(p+e.xxx));',
'}',
'',
/* cyan through most of the band, violet at the head, teal only on the tip */
'vec3 tintAt(float t){',
'  if(t<0.52) return mix(uColA,uColB,t/0.52);',
'  if(t<0.86) return uColB;',
'  return mix(uColB,uColC,clamp((t-0.86)/0.16,0.0,1.0));',
'}',
'',
/* The lighting dome stays bright on the dark cover too — the backdrop is drawn
   separately. Sharing them makes the glass read as chrome. */
'vec3 envMap(vec3 rd){',
'  float y=rd.y*0.5+0.5;',
'  vec3 base=(uTheme>0.5)',
'    ? mix(vec3(0.40,0.43,0.50),vec3(1.00,1.02,1.08),y)',
'    : mix(vec3(0.30,0.34,0.44),vec3(0.94,0.97,1.06),y);',
'  base+=pow(max(dot(rd,normalize(vec3(-0.46,0.80,-0.36))),0.0),20.0)*vec3(2.8,2.85,3.05);',
'  base+=pow(max(dot(rd,normalize(vec3(0.74,0.10,0.56))),0.0),12.0)*mix(uColA,uColB,0.5)*1.5;',
'  base+=pow(max(dot(rd,normalize(vec3(0.12,-0.90,0.22))),0.0),8.0)*uColA*0.45;',
'  return base;',
'}',
'',
'vec3 bg(vec2 uv){',
'  float r=clamp(length(uv*vec2(1.0,1.25))*1.2,0.0,1.0);',
'  return (uTheme>0.5)',
'    ? mix(vec3(0.985,0.987,0.995),vec3(0.930,0.938,0.960),r)',
'    : mix(vec3(0.043,0.055,0.078),vec3(0.008,0.012,0.020),r);',
'}',
'',
'vec3 aces(vec3 x){return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0);}',
'',
'void main(){',
'  {',
'    float a=uCRot, c=cos(a), s=sin(a), t=1.0-c, k=0.57735027;',
'    float tk=t*k*k, sk=s*k;',
'    gCM=mat3(tk+c, tk+sk, tk-sk,  tk-sk, tk+c, tk+sk,  tk+sk, tk-sk, tk+c);',
'  }',
'  vec2 uv=(gl_FragCoord.xy-0.5*uRes)/uRes;',
'  vec3 fw=normalize(uTgt-uCam);',
'  vec3 rt=normalize(cross(fw,vec3(0.0,1.0,0.0)));',
'  vec3 up=cross(rt,fw);',
'  vec3 rd=normalize(fw+rt*(uv.x*uFov.x)+up*(uv.y*uFov.y));',
'  vec3 ro=uCam;',
'',
'  float ABSb=(uTheme>0.5)?2.10:1.70;',
'  float MILK=(uTheme>0.5)?0.08:0.10;',
'  const float IOR=1.46;',
'  const float DISP=0.016;',
'',
'  float t=0.0; bool hit=false; float hitT=0.0; gT=0.0;',
'  for(int i=0;i<190;i++){',
'    if(float(i)>uSteps) break;',
'    float d=map(ro+rd*t);',
'    if(d<0.0016){ hit=true; hitT=gT; break; }',
'    t+=d*0.42;',
'    if(t>46.0) break;',
'  }',
'',
'  vec3 col;',
'  if(hit){',
'    vec3 p=ro+rd*t;',
'    vec3 n=nrm(p);',
'    vec3 tc=tintAt(clamp(hitT,0.0,1.0));',
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
'        it+=max(dd*0.80,0.006);',
'        if(it>9.0) break;',
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
'      refr=refr*exp(-ABSb*it*(vec3(1.0)-tc))+tc*it*0.14;',
'      refr=mix(refr,tc*1.10,MILK);',
'    }',
'    col=mix(refr,refl,fres);',
'    col+=pow(max(dot(reflect(rd,n),normalize(vec3(-0.46,0.80,-0.36))),0.0),42.0)*0.85;',
'    col+=tc*pow(1.0-clamp(dot(-rd,n),0.0,1.0),3.0)*0.50;',
'  } else {',
'    col=bg(uv);',
'  }',
'  col=aces(col);',
'  float vg=(uTheme>0.5)?0.08:0.16;',
'  col*=clamp(1.0-vg*pow(length(uv*vec2(1.05,1.25))*1.25,2.2),0.0,1.0);',
'  col+=(fract(sin(dot(gl_FragCoord.xy,vec2(12.9898,78.233)))*43758.5453)-0.5)/255.0;',
'  gl_FragColor=vec4(col,1.0);',
'}'
  ].join('\n');

  /* ---------- how the object sits on each board ---------- */
  var VIEWS = {
    /* front cover on its own, and option B's spread: the object resolves inside
       the front cover, with a lone cube left on the back */
    portrait: { az: 0.86, ay: -0.34, scale: 0.70, tgt: [0, 0, 0], frameH: 8.2, yaw: -4, pitch: 4, echo: [0, 0, 0, 0] },
    spread:   { az: 0.86, ay: -0.34, scale: 0.70, tgt: [-3.25, 0, 0], frameH: 8.2, yaw: -4, pitch: 4, echo: [0, 0, 0, 0] },
    /* the whole form laid out flat, for reading the structure */
    strip:    { az: 0.0, ay: -0.30, scale: 0.95, tgt: [0, 0, 0], frameH: 3.05, yaw: 0, pitch: 6, echo: [0, 0, 0, 0] }
  };

  var SHAPE = {
    L: 2.30, bend: 0.18,
    hw: [0.42, 0.78], hh: [0.38, 0.54],
    twistPhase: 0.35, weld: 0.16,
    head: [2.35, 0.16, 0.0], headRot: 0.55,
    cube: [-3.20, -0.42, 0.10, 0.56], cubeRot: [0, 0.42]
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

    ['uRes', 'uCam', 'uTgt', 'uFov', 'uTilt', 'uScale', 'uL', 'uBend', 'uNOpen', 'uHW', 'uHH',
     'uThick', 'uTwist', 'uTwistPhase', 'uSlotW', 'uWeld', 'uHead', 'uHeadRot', 'uCSize',
     'uCScale', 'uCBase', 'uCRot', 'uCube', 'uCubeRot', 'uEcho', 'uColA', 'uColB', 'uColC',
     'uTheme', 'uSteps'
    ].forEach(function (k) { U[k] = gl.getUniformLocation(prog, k); });

    function sizeBuffer(quality) {
      var cssW = canvas.clientWidth || parseInt(canvas.getAttribute('width'), 10) || 800;
      var cssH = canvas.clientHeight || parseInt(canvas.getAttribute('height'), 10) || 600;
      var maxW = quality === 'low' ? 420 : 940;
      var s = Math.min(1, maxW / cssW);
      var w = Math.max(64, Math.round(cssW * s));
      var h = Math.max(64, Math.round(cssH * s));
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
      return [w, h];
    }

    function setUniforms(size, quality) {
      var V = VIEWS[opts.view] || VIEWS.portrait;
      var aspect = size[0] / size[1];
      var dist = 19.0;
      var yaw = (opts.yaw || 0) * Math.PI / 180;
      var pit = (opts.pitch || 0) * Math.PI / 180;
      var T = V.tgt;
      var cam = [
        T[0] + dist * Math.sin(yaw) * Math.cos(pit),
        T[1] + dist * Math.sin(pit),
        T[2] + dist * Math.cos(yaw) * Math.cos(pit)
      ];
      var fH = V.frameH * (opts.zoom || 1);
      gl.uniform2f(U.uRes, size[0], size[1]);
      gl.uniform3f(U.uCam, cam[0], cam[1], cam[2]);
      gl.uniform3f(U.uTgt, T[0], T[1], T[2]);
      gl.uniform2f(U.uFov, fH * aspect / dist, fH / dist);
      gl.uniform2f(U.uTilt, V.az * (opts.tilt != null ? opts.tilt : 1), V.ay);
      gl.uniform1f(U.uScale, V.scale);
      gl.uniform1f(U.uL, SHAPE.L);
      gl.uniform1f(U.uBend, SHAPE.bend);
      gl.uniform1f(U.uNOpen, opts.splits);
      gl.uniform2fv(U.uHW, SHAPE.hw);
      gl.uniform2fv(U.uHH, SHAPE.hh);
      gl.uniform1f(U.uThick, opts.thick);
      gl.uniform1f(U.uTwist, opts.twist);
      gl.uniform1f(U.uTwistPhase, SHAPE.twistPhase);
      gl.uniform1f(U.uSlotW, opts.slotW);
      gl.uniform1f(U.uWeld, SHAPE.weld);
      gl.uniform3fv(U.uHead, SHAPE.head);
      gl.uniform1f(U.uHeadRot, SHAPE.headRot);
      gl.uniform1f(U.uCSize, opts.crystalSize);
      gl.uniform1f(U.uCScale, opts.crystalScale);
      gl.uniform1f(U.uCBase, opts.crystalBase);
      gl.uniform1f(U.uCRot, opts.crystalRot);
      gl.uniform4fv(U.uCube, SHAPE.cube);
      gl.uniform2fv(U.uCubeRot, [-V.az, SHAPE.cubeRot[1]]);
      gl.uniform4fv(U.uEcho, V.echo);
      gl.uniform3fv(U.uColA, hex2rgb(opts.accentA));
      gl.uniform3fv(U.uColB, hex2rgb(opts.accentB));
      gl.uniform3fv(U.uColC, hex2rgb(opts.accentC));
      gl.uniform1f(U.uTheme, opts.theme === 'light' ? 1.0 : 0.0);
      gl.uniform1f(U.uSteps, quality === 'low' ? 86.0 : 182.0);
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
      opts.yaw = Math.max(-70, Math.min(70, (opts.yaw || 0) + dx * 0.2));
      opts.pitch = Math.max(-50, Math.min(50, (opts.pitch || 0) - dy * 0.2));
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

  window.SEQ3D = { mount: mount, views: VIEWS, shape: SHAPE };
})();
