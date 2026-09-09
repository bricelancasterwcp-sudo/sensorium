import * as __srt from "RT";const __sfile=__srt.file("src/qualnames.ts","/w/src/qualnames.ts",[["ns.fn",2,"function"],["outer",5,"function"],["outer.inner",6,"function"],["onClick",11,"function"],["onBlur",12,"function"],["Store.reset",15,"function"],["legacy",16,"function"],["default",17,"function"],["<anonymous>",19,"function"],["<anonymous>",21,"function"],["default",25,"function"]],"33125a24898b85f222da5b6f333ab56a2ee5ccab28130688e0fb576d013520a6");namespace ns {
  export function fn(): void {const __sf=__srt.call(__sfile,0);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
}

function outer(): void {const __sf=__srt.call(__sfile,1);try{
  function inner(): void {const __sf=__srt.call(__sfile,2);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
  inner();
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

const handlers = {
  onClick: function () {const __sf=__srt.call(__sfile,3);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},
  onBlur() {const __sf=__srt.call(__sfile,4);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},
};

Store.reset = function () {const __sf=__srt.call(__sfile,5);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}};
module.exports.legacy = function () {const __sf=__srt.call(__sfile,6);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}};
module.exports = function () {const __sf=__srt.call(__sfile,7);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}};

const doubled = [1, 2].map((n) => {const __sf=__srt.call(__sfile,8);try{return __srt.ret(__sf,(n * 2))}catch(__se){__srt.thr(__sf,__se);throw __se}});

(function () {const __sf=__srt.call(__sfile,9);try{
  outer();
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}})();

export default (value: string) => {const __sf=__srt.call(__sfile,10);try{return __srt.ret(__sf,(value))}catch(__se){__srt.thr(__sf,__se);throw __se}};
