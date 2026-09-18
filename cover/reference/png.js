const zlib = require('zlib');
let T = null;
function crcTable(){ if(T) return T; T=new Int32Array(256);
  for(let n=0;n<256;n++){ let c=n; for(let k=0;k<8;k++) c = (c&1)? (0xEDB88320 ^ (c>>>1)) : (c>>>1); T[n]=c; }
  return T; }
function crc32(buf){ const t=crcTable(); let c=0xFFFFFFFF;
  for(let i=0;i<buf.length;i++) c = t[(c ^ buf[i]) & 0xFF] ^ (c>>>8);
  return (c ^ 0xFFFFFFFF)>>>0; }
function chunk(type, data){
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0);
  const td = Buffer.concat([Buffer.from(type,'ascii'), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td), 0);
  return Buffer.concat([len, td, crc]);
}
function writePNG(file, w, h, rgb){
  const stride = w*3;
  const raw = Buffer.alloc((stride+1)*h);
  for(let y=0;y<h;y++){ raw[y*(stride+1)] = 0;
    for(let i=0;i<stride;i++) raw[y*(stride+1)+1+i] = rgb[y*stride+i]; }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w,0); ihdr.writeUInt32BE(h,4);
  ihdr[8]=8; ihdr[9]=2; ihdr[10]=0; ihdr[11]=0; ihdr[12]=0;
  const png = Buffer.concat([
    Buffer.from([0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A]),
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw, {level:6})),
    chunk('IEND', Buffer.alloc(0))
  ]);
  require('fs').writeFileSync(file, png);
}
module.exports = { writePNG };
