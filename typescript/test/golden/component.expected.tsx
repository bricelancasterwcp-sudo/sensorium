import * as __srt from "RT";const __sfile=__srt.file("src/component.tsx","/w/src/component.tsx",[["Badge",3,"function"],["Badge.<anonymous>",4,"function"],["Badge.<anonymous>",9,"function"]],"45b7ee0e48a36fa605d386204523416d0799fd95e7501880e8a2a59d32d63407");import { useCallback } from "react";

export function Badge({ items }: { items: string[] }) {const __sf=__srt.call(__sfile,0);try{
  const onClick = useCallback(() => {const __sf=__srt.call(__sfile,1);try{
    report("click");
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}, []);
  return __srt.ret(__sf,((
    <ul onClick={onClick}>
      {items.map((item) => {const __sf=__srt.call(__sfile,2);try{return __srt.ret(__sf,((
        <li key={item}>{item}</li>
      )))}catch(__se){__srt.thr(__sf,__se);throw __se}})}
    </ul>
  )));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
