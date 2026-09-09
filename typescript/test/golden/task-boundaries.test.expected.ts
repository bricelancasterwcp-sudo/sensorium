import * as __srt from "RT";const __sfile=__srt.file("src/task-boundaries.test.ts","/w/src/task-boundaries.test.ts",[["<anonymous>",3,"function"],["<anonymous>",5,"function"],["register",7,"coroutine"],["<anonymous>",11,"function"],["<anonymous>",13,"function"],["registerTwo",15,"coroutine"]],"50b88fd4fd98d9fe54e2c643002c90dd413d58f4633c287ce3e703b5d27674a4");import { test } from "vitest";

test(...__srt.task((() => {const __sf=__srt.call(__sfile,0);try{return __srt.ret(__sf,("c"))}catch(__se){__srt.thr(__sf,__se);throw __se}}), { timeout: 1 }, fn2,0));

test(...__srt.task(("d"), { timeout: 1 }, flag ? base : () => {const __sf=__srt.call(__sfile,1);try{return __srt.ret(__sf,(go()))}catch(__se){__srt.thr(__sf,__se);throw __se}},1));

async function register(): Promise<void> {const __sf=__srt.call(__sfile,2);try{
  test(...__srt.task(("e"), { timeout: 1 }, __srt.r(__sf,await __srt.y(__sf,(mk()),0)),1));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

test(...__srt.task((() => {const __sf=__srt.call(__sfile,3);try{return __srt.ret(__sf,("f1"))}catch(__se){__srt.thr(__sf,__se);throw __se}}), fn2,0));

test(...__srt.task(("f2"), flag ? base : () => {const __sf=__srt.call(__sfile,4);try{return __srt.ret(__sf,(go()))}catch(__se){__srt.thr(__sf,__se);throw __se}},1));

async function registerTwo(): Promise<void> {const __sf=__srt.call(__sfile,5);try{
  test(...__srt.task(("f3"), __srt.r(__sf,await __srt.y(__sf,(mk()),0)),1));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
