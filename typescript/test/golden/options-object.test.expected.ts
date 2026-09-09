import * as __srt from "RT";const __sfile=__srt.file("src/options-object.test.ts","/w/src/options-object.test.ts",[["<anonymous>",3,"function"],["<anonymous>.<anonymous>",4,"function"],["<anonymous>",11,"function"],["<anonymous>",15,"function"]],"015417a0d17ba2c8753b60d9ea15ae66c2cdf185042cce1ef69324d06f798f22");import { describe, expect, test } from "vitest";

describe(...__srt.suite(("options"), { concurrent: true }, () => {const __sf=__srt.call(__sfile,0);try{
  test(...__srt.task(("times out"), { timeout: 100 }, () => {const __sf=__srt.call(__sfile,1);try{
    expect(1).toBe(1);
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},1), 5000);
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}), 1000);

test(...__srt.task(("options across lines"), {
  timeout: 100,
}, () => {const __sf=__srt.call(__sfile,2);try{
  expect(2).toBe(2);
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},1));

test(...__srt.task(("a concise body with options"), { timeout: 1 }, () => {const __sf=__srt.call(__sfile,3);try{return __srt.ret(__sf,(expect(3).toBe(3)))}catch(__se){__srt.thr(__sf,__se);throw __se}},1));
