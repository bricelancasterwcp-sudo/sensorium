import * as __srt from "RT";const __sfile=__srt.file("src/focus-catch.ts","/w/src/focus-catch.ts",[["guarded",2,"function"]],"9fcc7dd25c8290357be75f4e0fe1cb8976239be146589c994e5c9c4ba2e6bdf5");// focus: guarded
export function guarded(): number {const __sf=__srt.call(__sfile,0,[]);try{
  let count = 0;__srt.line(__sf,3,["count",count]);
  try {
    throw __srt.raise(__sf,(new Error('x')),5);
  } catch (e) {__srt.handled(__sf,e,6,"catch");__srt.line(__sf,6,["e",e]);
    count += 1;__srt.line(__sf,7,["count",count]);
  };__srt.line(__sf,4,[],["e"]);
  return __srt.ret(__sf,(count));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
