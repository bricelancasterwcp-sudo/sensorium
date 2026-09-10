import * as __srt from "RT";const __sfile=__srt.file("src/then-onrejected.ts","/w/src/then-onrejected.ts",[["both",1,"function"],["both.<anonymous>",3,"function"],["both.<anonymous>",4,"function"],["onlyFulfilled",8,"function"],["onlyFulfilled.<anonymous>",9,"function"]],"083d1c4780ec6ada215fed58531701c5f38136a8daf08e42d1ea1a37de049de1");export function both(): Promise<string> {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(risky().then(
    (value) => {const __sf=__srt.call(__sfile,1);try{return __srt.ret(__sf,(String(value)))}catch(__se){__srt.thr(__sf,__se);throw __se}},
    __srt.catchCb(__sf,2,"catch_callback_escaped",((err) => {const __sf=__srt.call(__sfile,2);try{return __srt.ret(__sf,(String(err)))}catch(__se){__srt.thr(__sf,__se);throw __se}})),
  )));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

export function onlyFulfilled(): Promise<string> {const __sf=__srt.call(__sfile,3);try{
  return __srt.ret(__sf,(risky().then((value) => {const __sf=__srt.call(__sfile,4);try{return __srt.ret(__sf,(String(value)))}catch(__se){__srt.thr(__sf,__se);throw __se}})));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
