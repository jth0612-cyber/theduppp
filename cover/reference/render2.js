const { writePNG } = require('./png.js');
const F = require('./form2.js');
const { clamp, mix } = F;
const P = Object.assign({}, F.PRESET);

const NAME=process.argv[2], W=+process.argv[3], H=+process.argv[4], LIGHT=process.argv[5]==='light', OUT=process.argv[6];

// placement of the object on the cover
const VIEWS = {
  portrait: { az: 0.86, ay: -0.34, scale: 0.70, tgt:[0,0,0],       frameH: 8.2, yaw:-4, pitch:4 },
  spread:   { az: 0.86, ay: -0.34, scale: 0.70, tgt:[-3.25,0,0],   frameH: 8.2, yaw:-4, pitch:4 },
  strip:    { az: 0.00, ay: -0.30, scale: 0.95, tgt:[0,0,0],       frameH: 2.6, yaw:0,  pitch:6 }
};
const V=VIEWS[NAME];
P.cubeRotZ = -V.az;   // keep the cube reading as a cube once the object is tilted

const norm=v=>{const l=Math.hypot(v[0],v[1],v[2]);return [v[0]/l,v[1]/l,v[2]/l];};
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];

// world -> object local: undo rotZ(az) then rotY(ay)
const CZ=Math.cos(V.az),SZ=Math.sin(V.az),CY=Math.cos(V.ay),SY=Math.sin(V.ay);
function toLocal(x,y,z){
  const x1=CY*x-SY*z, z1=SY*x+CY*z;            // rotY(-ay)
  const x2=CZ*x1+SZ*y, y2=-SZ*x1+CZ*y;         // rotZ(-az)
  return [x2/V.scale, y2/V.scale, z1/V.scale];
}
let gT=0;
const ECHO=V.echo&&V.echo[3]>0?V.echo:null;
function map(x,y,z){
  const q=toLocal(x,y,z);
  gT=F.objT(q[0],P);
  let d=F.objDE(q[0],q[1],q[2],P)*V.scale;
  if(ECHO){
    const EP=Object.assign({},P,{cubeX:ECHO[0],cubeY:ECHO[1],cubeZ:ECHO[2],cubeS:ECHO[3],cubeRotZ:0,cubeRot:0.42});
    const e=F.cubeDE(x,y,z,EP);
    if(e<d){d=e;gT=0;}
  }
  return d;
}
function nrm(p){const e=0.0018;return norm([map(p[0]+e,p[1],p[2])-map(p[0]-e,p[1],p[2]),
  map(p[0],p[1]+e,p[2])-map(p[0],p[1]-e,p[2]),map(p[0],p[1],p[2]+e)-map(p[0],p[1],p[2]-e)]);}

// cyan -> lavender -> teal, as in the reference art
const C0=[0.33,0.92,0.88], C1=[0.74,0.55,0.99], C2=[0.32,0.90,0.80];
// cyan through most of the band, violet at the head, teal only on the tip
function tint(t){
  if(t<0.52) return [0,1,2].map(i=>mix(C0[i],C1[i],t/0.52));
  if(t<0.86) return C1.slice();
  return [0,1,2].map(i=>mix(C1[i],C2[i],clamp((t-0.86)/0.16,0,1)));
}

const dist=19, frameH=V.frameH;
const yaw=V.yaw*Math.PI/180, pitch=V.pitch*Math.PI/180;
const T=V.tgt;
const cam=[T[0]+dist*Math.sin(yaw)*Math.cos(pitch), T[1]+dist*Math.sin(pitch), T[2]+dist*Math.cos(yaw)*Math.cos(pitch)];
const fw=norm([T[0]-cam[0],T[1]-cam[1],T[2]-cam[2]]), rt=norm(cross(fw,[0,1,0])), up=cross(rt,fw);

const KEY=norm([-0.46,0.80,-0.36]), RIM=norm([0.74,0.10,0.56]), FILL=norm([0.12,-0.90,0.22]);
function env(rd){
  const yy=rd[1]*0.5+0.5;
  const base = LIGHT ? [mix(0.40,1.00,yy),mix(0.43,1.02,yy),mix(0.50,1.08,yy)]
                     : [mix(0.30,0.94,yy),mix(0.34,0.97,yy),mix(0.44,1.06,yy)];
  const k=Math.pow(Math.max(dot(rd,KEY),0),20), r=Math.pow(Math.max(dot(rd,RIM),0),12), f=Math.pow(Math.max(dot(rd,FILL),0),8);
  for(let i=0;i<3;i++) base[i]+=k*[2.8,2.85,3.05][i]+r*mix(C0[i],C1[i],0.5)*1.5+f*C0[i]*0.45;
  return base;
}
function refract(I,N,eta){const d=dot(N,I),k=1-eta*eta*(1-d*d);if(k<0)return null;
  const f=eta*d+Math.sqrt(k);return [eta*I[0]-f*N[0],eta*I[1]-f*N[1],eta*I[2]-f*N[2]];}
const reflect=(I,N)=>{const d=2*dot(I,N);return [I[0]-d*N[0],I[1]-d*N[1],I[2]-d*N[2]];};
const aces=x=>clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0,1);
const IOR=1.46, DISP=0.016, ABS=LIGHT?2.10:1.70, MILK=LIGHT?0.08:0.10;

const buf=Buffer.alloc(W*H*3);
for(let py=0;py<H;py++){
  for(let px=0;px<W;px++){
    const u=(px+0.5)/W-0.5, v=0.5-(py+0.5)/H, fy=frameH/dist, fx=fy*(W/H);
    const rd=norm([fw[0]+rt[0]*u*fx+up[0]*v*fy, fw[1]+rt[1]*u*fx+up[1]*v*fy, fw[2]+rt[2]*u*fx+up[2]*v*fy]);
    let t=0,hit=false,hitT=0; gT=0;
    for(let i=0;i<190;i++){
      const d=map(cam[0]+rd[0]*t,cam[1]+rd[1]*t,cam[2]+rd[2]*t);
      if(d<0.0016){hit=true;hitT=gT;break;}
      t+=d*0.42; if(t>46)break;
    }
    let col;
    if(hit){
      const p=[cam[0]+rd[0]*t,cam[1]+rd[1]*t,cam[2]+rd[2]*t], n=nrm(p);
      const tc=tint(clamp(hitT,0,1));
      const fres=0.035+0.965*Math.pow(1-clamp(-dot(rd,n),0,1),5);
      const refl=env(reflect(rd,n)); let refr=refl;
      const rdIn=refract(rd,n,1/IOR);
      if(rdIn){
        const ip=[p[0]-n[0]*0.010,p[1]-n[1]*0.010,p[2]-n[2]*0.010]; let it=0;
        for(let j=0;j<40;j++){
          const dd=-map(ip[0]+rdIn[0]*it,ip[1]+rdIn[1]*it,ip[2]+rdIn[2]*it);
          if(dd<0.0018)break; it+=Math.max(dd*0.80,0.006); if(it>9)break;
        }
        const ep=[ip[0]+rdIn[0]*it,ip[1]+rdIn[1]*it,ip[2]+rdIn[2]*it];
        const en=nrm(ep).map(q=>-q), tir=reflect(rdIn,en);
        const o=[refract(rdIn,en,IOR*(1-DISP)),refract(rdIn,en,IOR),refract(rdIn,en,IOR*(1+DISP))];
        const e=o.map(d2=>d2?env(d2):env(tir));
        refr=[e[0][0],e[1][1],e[2][2]];
        for(let c=0;c<3;c++) refr[c]=mix(refr[c]*Math.exp(-ABS*it*(1-tc[c]))+tc[c]*it*0.14, tc[c]*1.10, MILK);
      }
      col=[0,1,2].map(c=>mix(refr[c],refl[c],fres));
      const sp=Math.pow(Math.max(dot(reflect(rd,n),KEY),0),42)*0.85;   // soft, not a sparkle
      const rm=Math.pow(1-clamp(-dot(rd,n),0,1),3)*0.50;
      for(let c=0;c<3;c++) col[c]+=sp+tc[c]*rm;
    } else {
      const r=clamp(Math.hypot(u,v*1.25)*1.2,0,1);
      col = LIGHT ? [mix(0.980,0.885,r),mix(0.982,0.895,r),mix(0.992,0.930,r)]
                  : [mix(0.043,0.008,r),mix(0.055,0.012,r),mix(0.078,0.020,r)];
    }
    const vig=clamp(1-0.16*Math.pow(Math.hypot(u*1.05,v*1.25)*1.25,2.2),0,1);
    const o=(py*W+px)*3;
    for(let c=0;c<3;c++) buf[o+c]=Math.round(255*aces(col[c])*vig);
  }
  if(py%200===0)console.error(OUT,py);
}
writePNG(OUT,W,H,buf);
console.log('wrote',OUT);
