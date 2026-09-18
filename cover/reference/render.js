const { writePNG } = require('./png.js');
const { stageDE, mix, clamp } = require('./form.js');

const LAYOUTS = {
  front:    { C:[[0.95,-2.70,0.35],[2.10,-1.70,-0.90],[3.60,0.70,0.85],[4.60,2.15,-0.30]], scale:[0.40,0.88], orphan:[-3.05,-0.25,0.0,0.55], frameH:8.2, stages:6, yaw:-6,  pitch:6, fuse:0.15, spin:1 },
  portrait: { C:[[-1.55,-2.90,0.40],[-0.70,-1.80,-0.90],[0.55,0.90,0.85],[1.50,2.40,-0.30]], scale:[0.40,0.88], orphan:[0,0,0,0], frameH:8.2, stages:6, yaw:-10, pitch:8, fuse:0.15, spin:1 },
  strip:    { C:[[-5.40,0,0],[-1.80,0,0],[1.80,0,0],[5.40,0,0]], scale:[0.44,0.62], orphan:[0,0,0,0], frameH:3.6, stages:7, yaw:0, pitch:0, fuse:0.02, spin:0.35 }
};
const NAME=process.argv[2], W=+process.argv[3], H=+process.argv[4], LIGHT=process.argv[5]==='light', OUT=process.argv[6];
const L=LAYOUTS[NAME];
const TWIST=1.0, FUSE=L.fuse, STAGES=L.stages;
const COLA=[0.40,0.93,0.87], COLB=[0.72,0.57,0.99];
const dist=17, frameH=L.frameH, yaw=L.yaw*Math.PI/180, pitch=L.pitch*Math.PI/180;
const ABS=LIGHT?1.60:1.10, GLOW=LIGHT?0.40:1.0, MILK=LIGHT?0.13:0.22, IOR=1.47, DISP=0.018;

const norm=v=>{const l=Math.hypot(v[0],v[1],v[2]);return [v[0]/l,v[1]/l,v[2]/l];};
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cam=[dist*Math.sin(yaw)*Math.cos(pitch), dist*Math.sin(pitch), dist*Math.cos(yaw)*Math.cos(pitch)];
const fw=norm([-cam[0],-cam[1],-cam[2]]), rt=norm(cross(fw,[0,1,0])), up=cross(rt,fw);
const bez=t=>{const u=1-t;return [0,1,2].map(i=>u*u*u*L.C[0][i]+3*u*u*t*L.C[1][i]+3*u*t*t*L.C[2][i]+t*t*t*L.C[3][i]);};
const smin=(a,b,k)=>{const h=clamp(0.5+0.5*(b-a)/k,0,1);return mix(b,a,h)-k*h*(1-h);};
function rotv(p,ry,rx,rz){let [x,y,z]=p;let c,s,t;
  c=Math.cos(rz);s=Math.sin(rz);t=c*x+s*y;y=-s*x+c*y;x=t;
  c=Math.cos(rx);s=Math.sin(rx);t=c*y+s*z;z=-s*y+c*z;y=t;
  c=Math.cos(ry);s=Math.sin(ry);t=c*x-s*z;z=s*x+c*z;x=t;return [x,y,z];}
const OBJ=[];
for(let i=0;i<STAGES;i++){const t=i/(STAGES-1);
  OBJ.push({t,m:t,c:bez(t),sc:mix(L.scale[0],L.scale[1],t),ry:L.spin*(t*2.3+i*0.31),rx:L.spin*(t*1.25+i*0.19),rz:i*0.26});}
const ORPH=L.orphan[3]>0?{c:[L.orphan[0],L.orphan[1],L.orphan[2]],sc:L.orphan[3]}:null;
let gT=0;
function map(x,y,z){
  let d=1e9;
  for(const o of OBJ){
    const bd=Math.hypot(x-o.c[0],y-o.c[1],z-o.c[2])-o.sc*2.35;
    if(bd>0.25){if(bd<d)d=bd;continue;}
    const q=rotv([(x-o.c[0])/o.sc,(y-o.c[1])/o.sc,(z-o.c[2])/o.sc],o.ry,o.rx,o.rz);
    const di=stageDE(q[0],q[1],q[2],o.m,TWIST)*o.sc;
    if(di<d)gT=o.t; d=smin(d,di,FUSE);
  }
  if(ORPH){
    const bd=Math.hypot(x-ORPH.c[0],y-ORPH.c[1],z-ORPH.c[2])-ORPH.sc*2.35;
    if(bd>0.25){if(bd<d)d=bd;}
    else{const q=rotv([(x-ORPH.c[0])/ORPH.sc,(y-ORPH.c[1])/ORPH.sc,(z-ORPH.c[2])/ORPH.sc],0.62,0.30,0);
      const di=stageDE(q[0],q[1],q[2],0,TWIST)*ORPH.sc; if(di<d){gT=0;d=di;}}
  }
  return d;
}
function nrm(p){const e=0.0016;return norm([map(p[0]+e,p[1],p[2])-map(p[0]-e,p[1],p[2]),
  map(p[0],p[1]+e,p[2])-map(p[0],p[1]-e,p[2]),map(p[0],p[1],p[2]+e)-map(p[0],p[1],p[2]-e)]);}
const KEY=norm([-0.50,0.78,-0.38]),RIM=norm([0.78,0.12,0.52]),FILL=norm([0.15,-0.88,0.26]);
function env(rd){const yy=rd[1]*0.5+0.5;
  const base=LIGHT?[mix(0.34,1.00,yy),mix(0.37,1.01,yy),mix(0.46,1.08,yy)]
                  :[mix(0.26,0.92,yy),mix(0.30,0.95,yy),mix(0.40,1.06,yy)];
  const k=Math.pow(Math.max(dot(rd,KEY),0),26),r=Math.pow(Math.max(dot(rd,RIM),0),14),f=Math.pow(Math.max(dot(rd,FILL),0),9);
  for(let i=0;i<3;i++)base[i]+=k*[3.4,3.5,3.8][i]+r*mix(COLA[i],COLB[i],0.55)*2.4+f*COLA[i]*0.7;
  return base;}
function refract(I,N,eta){const d=dot(N,I),k=1-eta*eta*(1-d*d);if(k<0)return null;
  const f=eta*d+Math.sqrt(k);return [eta*I[0]-f*N[0],eta*I[1]-f*N[1],eta*I[2]-f*N[2]];}
const reflect=(I,N)=>{const d=2*dot(I,N);return [I[0]-d*N[0],I[1]-d*N[1],I[2]-d*N[2]];};
const aces=x=>clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0,1);
const buf=Buffer.alloc(W*H*3);
const ALL=ORPH?OBJ.concat([{t:0,c:ORPH.c,sc:ORPH.sc}]):OBJ;
for(let py=0;py<H;py++){
  for(let px=0;px<W;px++){
    const u=(px+0.5)/W-0.5, v=0.5-(py+0.5)/H, fy=frameH/dist, fx=fy*(W/H);
    const rd=norm([fw[0]+rt[0]*u*fx+up[0]*v*fy,fw[1]+rt[1]*u*fx+up[1]*v*fy,fw[2]+rt[2]*u*fx+up[2]*v*fy]);
    let t=0,hit=false,hitT=0; gT=0;
    for(let i=0;i<150;i++){const d=map(cam[0]+rd[0]*t,cam[1]+rd[1]*t,cam[2]+rd[2]*t);
      if(d<0.0016){hit=true;hitT=gT;break;} t+=d*0.50; if(t>48)break;}
    const glow=[0,0,0];
    for(const o of ALL){
      const ox=o.c[0]-cam[0],oy=o.c[1]-cam[1],oz=o.c[2]-cam[2];
      const proj=ox*rd[0]+oy*rd[1]+oz*rd[2]; if(proj<=0)continue;
      const dd=Math.max(Math.sqrt(Math.max(ox*ox+oy*oy+oz*oz-proj*proj,0))-o.sc*1.05,0);
      const h=Math.exp(-dd*4.4)*0.40+Math.exp(-dd*1.7)*0.055;
      for(let c=0;c<3;c++)glow[c]+=mix(COLA[c],COLB[c],clamp(o.t,0,1))*h;
    }
    if(hit)for(let c=0;c<3;c++)glow[c]*=0.30;
    let col;
    if(hit){
      const p=[cam[0]+rd[0]*t,cam[1]+rd[1]*t,cam[2]+rd[2]*t], n=nrm(p);
      const tint=[0,1,2].map(c=>mix(COLA[c],COLB[c],clamp(hitT,0,1)));
      const fres=0.035+0.965*Math.pow(1-clamp(-dot(rd,n),0,1),5);
      const refl=env(reflect(rd,n)); let refr=refl;
      const rdIn=refract(rd,n,1/IOR);
      if(rdIn){
        const ip=[p[0]-n[0]*0.010,p[1]-n[1]*0.010,p[2]-n[2]*0.010]; let it=0;
        for(let j=0;j<40;j++){const dd=-map(ip[0]+rdIn[0]*it,ip[1]+rdIn[1]*it,ip[2]+rdIn[2]*it);
          if(dd<0.0018)break; it+=Math.max(dd*0.82,0.006); if(it>8)break;}
        const ep=[ip[0]+rdIn[0]*it,ip[1]+rdIn[1]*it,ip[2]+rdIn[2]*it];
        const en=nrm(ep).map(q=>-q), tir=reflect(rdIn,en);
        const o=[refract(rdIn,en,IOR*(1-DISP)),refract(rdIn,en,IOR),refract(rdIn,en,IOR*(1+DISP))];
        const e=o.map(d2=>d2?env(d2):env(tir));
        refr=[e[0][0],e[1][1],e[2][2]];
        for(let c=0;c<3;c++)refr[c]=mix(refr[c]*Math.exp(-ABS*it*(1-tint[c]))+tint[c]*it*0.17, tint[c]*1.15, MILK);
      }
      col=[0,1,2].map(c=>mix(refr[c],refl[c],fres));
      const sp=Math.pow(Math.max(dot(reflect(rd,n),KEY),0),110)*2.8;
      const rm=Math.pow(1-clamp(-dot(rd,n),0,1),3)*0.42;
      for(let c=0;c<3;c++)col[c]+=sp+tint[c]*rm;
    } else {
      const r=clamp(Math.hypot(u,v*1.25)*1.15,0,1);
      col=LIGHT?[mix(0.985,0.880,r),mix(0.985,0.890,r),mix(0.995,0.930,r)]
               :[mix(0.045,0.006,r),mix(0.052,0.008,r),mix(0.080,0.016,r)];
    }
    for(let c=0;c<3;c++)col[c]+=glow[c]*GLOW;
    const vig=clamp(1-0.20*Math.pow(Math.hypot(u*1.05,v*1.25)*1.25,2.2),0,1);
    const o=(py*W+px)*3;
    for(let c=0;c<3;c++)buf[o+c]=Math.round(255*aces(col[c]*1.02)*vig);
  }
  if(py%150===0)console.error(OUT,'row',py);
}
writePNG(OUT,W,H,buf);
console.log('wrote',OUT);
