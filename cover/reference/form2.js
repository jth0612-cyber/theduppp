// SEQUENCE object, v2. Structure read off the reference art:
//   a standalone glass cube; ONE continuous band that twists and splits into
//   two braiding strands, widening at each split; and an angular crystal
//   cluster grown onto the far end of that band.
const clamp=(x,a,b)=>x<a?a:(x>b?b:x);
const mix=(a,b,t)=>a+(b-a)*t;
const sstep=(e0,e1,x)=>{const t=clamp((x-e0)/(e1-e0),0,1);return t*t*(3-2*t);};
const smin=(a,b,k)=>{const h=clamp(0.5+0.5*(b-a)/k,0,1);return mix(b,a,h)-k*h*(1-h);};

function rbox3(x,y,z,bx,by,bz,r){
  const qx=Math.abs(x)-(bx-r),qy=Math.abs(y)-(by-r),qz=Math.abs(z)-(bz-r);
  const mx=Math.max(qx,0),my=Math.max(qy,0),mz=Math.max(qz,0);
  return Math.sqrt(mx*mx+my*my+mz*mz)+Math.min(Math.max(qx,Math.max(qy,qz)),0)-r;
}
function rrect(qx,qy,hx,hy,r){
  r=Math.min(r,Math.min(hx,hy)*0.95);
  const dx=Math.abs(qx)-(hx-r),dy=Math.abs(qy)-(hy-r);
  return Math.hypot(Math.max(dx,0),Math.max(dy,0))+Math.min(Math.max(dx,dy),0)-r;
}

// Kaleidoscopic IFS with a rotation inside the fold. The rotation is what
// takes the lattice off the world axes and gives facets at many angles —
// without it the result reads as a stack of boxes, not a crystal.
function rotAxis(a){
  const c=Math.cos(a),s=Math.sin(a),t=1-c,k=1/Math.sqrt(3);
  return [[t*k*k+c,   t*k*k-s*k, t*k*k+s*k],
          [t*k*k+s*k, t*k*k+c,   t*k*k-s*k],
          [t*k*k-s*k, t*k*k+s*k, t*k*k+c  ]];
}
function crystalDE(x,y,z,P){
  const M=P.M; let s=1;
  for(let i=0;i<3;i++){
    let ax=Math.abs(x),ay=Math.abs(y),az=Math.abs(z);
    if(ax<ay){const t=ax;ax=ay;ay=t;}
    if(ax<az){const t=ax;ax=az;az=t;}
    if(ay<az){const t=ay;ay=az;az=t;}
    const nx=M[0][0]*ax+M[0][1]*ay+M[0][2]*az;
    const ny=M[1][0]*ax+M[1][1]*ay+M[1][2]*az;
    const nz=M[2][0]*ax+M[2][1]*ay+M[2][2]*az;
    x=P.cScale*nx-(P.cScale-1); y=P.cScale*ny-(P.cScale-1); z=P.cScale*nz-(P.cScale-1);
    s*=P.cScale;
  }
  return rbox3(x,y,z,P.cBase,P.cBase,P.cBase,0.03)/s;
}
function headDE(x,y,z,P){
  const dx=(x-P.headX)/P.cSize, dy=(y-P.headY)/P.cSize, dz=(z-P.headZ)/P.cSize;
  const c=Math.cos(P.headRot),s=Math.sin(P.headRot);
  return crystalDE(c*dx-s*dz, dy, s*dx+c*dz, P)*P.cSize;
}

// The band. Runs along x over [-L, L]; u is the position along it.
// NOPEN evenly spaced splits, each inside a widened section.
function bandDE(x,y,z,P){
  const L=P.L;
  const u=clamp((x+L)/(2*L),0,1);
  const yy=y-P.bend*Math.sin(u*Math.PI);

  const w=Math.abs(Math.sin(u*Math.PI*P.nOpen));     // 0 at the waists, 1 mid-split
  const grow=mix(0.86,1.0,sstep(0.0,0.6,u));
  const hw=mix(P.hwMin,P.hwMax,w)*grow;
  const hh=mix(P.hhMin,P.hhMax,w)*grow;

  const th=P.twist*x+P.twistPhase;
  const ca=Math.cos(th),sa=Math.sin(th);
  const qy=ca*yy+sa*z, qz=-sa*yy+ca*z;

  let d=rrect(qy,qz,hw,hh,Math.min(hw,hh)*0.85);
  const sw=hw*P.slotW*w;
  if(sw>0.004) d=Math.max(d,-rrect(qy,qz,sw,hh*2.4,sw*0.6+0.01));

  const ex=Math.abs(x)-L;
  return Math.min(Math.max(d,ex),0)+Math.hypot(Math.max(d,0),Math.max(ex,0));
}

// The cube carries its own rotation about z as well, so that once the whole
// object is tilted onto the cover diagonal it still reads as a cube in
// three-quarter view rather than as a diamond.
function cubeDE(x,y,z,P){
  let dx=x-P.cubeX, dy=y-P.cubeY, dz=z-P.cubeZ;
  const cz=Math.cos(P.cubeRotZ),sz=Math.sin(P.cubeRotZ);
  const x1=cz*dx-sz*dy, y1=sz*dx+cz*dy;
  const cy=Math.cos(P.cubeRot),sy=Math.sin(P.cubeRot);
  const x2=cy*x1-sy*dz, z2=sy*x1+cy*dz;
  return rbox3(x2/P.cubeS, y1/P.cubeS, z2/P.cubeS, 1,1,1, 0.05)*P.cubeS;
}

function objDE(x,y,z,P){
  return Math.min(smin(bandDE(x,y,z,P), headDE(x,y,z,P), P.weld), cubeDE(x,y,z,P));
}
function objT(x,P){ return clamp((x-P.cubeX)/(P.headX+0.6-P.cubeX),0,1); }

const PRESET={
  L:2.30, bend:0.18, nOpen:3,
  hwMin:0.42,hwMax:0.78,hhMin:0.38,hhMax:0.54,
  twist:0.90,twistPhase:0.35,slotW:0.66,
  weld:0.16,
  headX:2.35, headY:0.16, headZ:0.0, headRot:0.55,
  cSize:0.60, cScale:2.20, cBase:1.26, M:rotAxis(0.45),
  cubeX:-3.20, cubeY:-0.42, cubeZ:0.10, cubeS:0.56, cubeRot:0.42, cubeRotZ:-0.86
};
module.exports={clamp,mix,sstep,smin,rbox3,rrect,rotAxis,objDE,objT,bandDE,headDE,cubeDE,crystalDE,PRESET};
