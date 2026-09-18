// The shipping SDF, in JS. One continuous formula; transliterated 1:1 into GLSL.
const clamp=(x,a,b)=> x<a?a:(x>b?b:x);
const mix=(a,b,t)=> a+(b-a)*t;
const sstep=(e0,e1,x)=>{const t=clamp((x-e0)/(e1-e0),0,1); return t*t*(3-2*t);};

function rbox(x,y,z,b,r){
  const qx=Math.abs(x)-(b-r), qy=Math.abs(y)-(b-r), qz=Math.abs(z)-(b-r);
  const mx=Math.max(qx,0),my=Math.max(qy,0),mz=Math.max(qz,0);
  return Math.sqrt(mx*mx+my*my+mz*mz)+Math.min(Math.max(qx,Math.max(qy,qz)),0)-r;
}

// The solid every scale of the fractal is built from.
function baseSolid(x,y,z,open,soft,sharp,twistAmt){
  const c=Math.cos(y*twistAmt), s=Math.sin(y*twistAmt);
  const X=c*x-s*z, Z=s*x+c*z; x=X; z=Z;

  const b=mix(1.0,1.05,open)*(1.0+0.16*sharp);
  const r=mix(0.06,0.62,soft)*(1.0-0.86*sharp)+0.03;
  let shell=rbox(x,y,z,b,r);
  const oct=(Math.abs(x)+Math.abs(y)+Math.abs(z)-b*1.86)*0.57735;
  shell=Math.min(shell, mix(1e4,oct,sharp));

  const f=mix(1.02,1.55,open);
  const g=Math.sin(x*f)*Math.cos(y*f)+Math.sin(y*f)*Math.cos(z*f)+Math.sin(z*f)*Math.cos(x*f);
  const thick=mix(1.75,0.82,open);
  return Math.max(shell,(Math.abs(g)-thick)/(f*1.75));
}

// m: 0 = plain cube ... 1 = dendritic snow crystal.
// Fold weights are tuned so that at m=1 exactly two iterations are FULLY on
// (a partially-applied fold shatters the solid into dust).
function stageDE(x,y,z,m,twist){
  let s=1.0;
  for(let n=0;n<3;n++){
    const a=clamp(m*7.333-5.133-n*1.15,0,1);
    if(a<=0.002) break;
    let ax=Math.abs(x),ay=Math.abs(y),az=Math.abs(z);
    if(ax<ay){const t=ax;ax=ay;ay=t;}
    if(ax<az){const t=ax;ax=az;az=t;}
    if(ay<az){const t=ay;ay=az;az=t;}
    ax*=3;ay*=3;az*=3;
    if(ax>1.0) ax-=2.0;
    x=mix(x,ax,a); y=mix(y,ay,a); z=mix(z,az,a);
    s*=mix(1,3,a);
  }
  const sharp=sstep(0.70,1.0,m);
  const open=sstep(0.0,0.50,m)*(1.0-0.62*sharp);
  const soft=sstep(0.0,0.38,m)*(1.0-0.30*sharp);
  const tw=twist*sstep(0.05,0.60,m)*(1.0-0.55*sharp);
  return baseSolid(x,y,z,open,soft,sharp,tw)/s;
}
module.exports={clamp,mix,sstep,rbox,baseSolid,stageDE};
