import * as __srt from "RT";const __sfile=__srt.file("src/options-object.test.ts","/w/src/options-object.test.ts",[["<anonymous>",3,"function"],["<anonymous>.<anonymous>",4,"function"],["<anonymous>",11,"function"],["<anonymous>",15,"function"]],"32deb14aac954cc4f6cdbb0c8d2eb8dd13da683460e7d4f3dc7909348664586f");import { describe, expect, test } from "vitest";

describe(...__srt.suite(("options"), () => {const __sf=__srt.call(__sfile,0);try{
  test(...__srt.task(("times out"), () => {const __sf=__srt.call(__sfile,1);try{
    expect(1).toBe(1);
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},1, { timeout: 100 }), 5000);
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}, { concurrent: true }), 1000);

test("multi-line options are left alone", {
  timeout: 100,
}, () => {const __sf=__srt.call(__sfile,2);try{
  expect(2).toBe(2);
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}});

test("a concise body with options is left alone", { timeout: 1 }, () => {const __sf=__srt.call(__sfile,3);try{return __srt.ret(__sf,(expect(3).toBe(3)))}catch(__se){__srt.thr(__sf,__se);throw __se}});
