import * as __srt from "RT";const __sfile=__srt.file("src/identifier-callback.test.ts","/w/src/identifier-callback.test.ts",[["sharedCase",3,"function"],["<anonymous>",5,"function"]],"927cab42678482d0017adc4dcfce47a015dfc9b4d6b30824ef33f1c1416bcb74");import { describe, it, test } from "vitest";

const sharedCase = () => {const __sf=__srt.call(__sfile,0);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}};

describe(...__srt.suite(("shared"), () => {const __sf=__srt.call(__sfile,1);try{
  test(...__srt.task(("identifier callback"), sharedCase,1));

  it.each(table)(...__srt.task(("row %s"), sharedCase,3));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}));
