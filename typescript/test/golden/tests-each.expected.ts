import * as __srt from "RT";const __sfile=__srt.file("src/tests-each.ts","/w/src/tests-each.ts",[["<anonymous>",3,"coroutine"],["<anonymous>",7,"function"],["<anonymous>",14,"function"],["<anonymous>",18,"function"],["<anonymous>.<anonymous>",19,"function"]],"0091ad1a43c3e53a6e5ec6f02e1d7035bfd9d39a1e25cc5a192d3e767501fefe");import { describe, expect, it, test } from "vitest";

it.concurrent(...__srt.task(("subtracts"), async () => {const __sf=__srt.call(__sfile,0);try{
  expect(__srt.r(__sf,await __srt.y(__sf,(sub(2, 1)),0))).toBe(1);
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},1));

test.each([1, 2])(...__srt.task(("doubles %i"), (n: number) => {const __sf=__srt.call(__sfile,1);try{
  expect(n * 2).toBe(n + n);
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},3));

test.each`
  a    | b
  ${1} | ${2}
`(...__srt.task(("adds $a"), ({ a, b }: { a: number; b: number }) => {const __sf=__srt.call(__sfile,2);try{
  expect(a + b).toBe(3);
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},3));

describe.each([["a"], ["b"]])(...__srt.suite(("suite %s"), (letter: string) => {const __sf=__srt.call(__sfile,3);try{
  it(...__srt.task(("is a letter"), () => {const __sf=__srt.call(__sfile,4);try{
    expect(letter.length).toBe(1);
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}},1));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}));
