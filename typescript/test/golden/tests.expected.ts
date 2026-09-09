import * as __srt from "RT";const __sfile=__srt.file("src/tests.ts","/w/src/tests.ts",[["<anonymous>",3,"function"],["<anonymous>.<anonymous>",4,"function"],["<anonymous>.<anonymous>",10,"function"],["<anonymous>.<anonymous>",12,"function"],["<anonymous>",15,"function"]],"5e4ed0d13cc30d1a83a009c7e3235887e13c5d10a6efebbc044c6115a26a5a0b");import { describe, expect, it, suite, test } from "vitest";

describe(...__srt.suite(("math"), () => {const __sf=__srt.call(__sfile,0);try{
  test(...__srt.task(("adds"), () => {const __sf=__srt.call(__sfile,1);try{
    expect(1 + 1).toBe(2);
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},1));

  test.todo("multiplies");

  test(...__srt.task(("retries"), () => {const __sf=__srt.call(__sfile,2);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},1), { retry: 2 });

  test(...__srt.task((name), () => {const __sf=__srt.call(__sfile,3);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},0));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}));

suite(...__srt.suite(("edges"), () => {const __sf=__srt.call(__sfile,4);try{;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}));
