import * as __srt from "RT";const __sfile=__srt.file("src/overloads.ts","/w/src/overloads.ts",[["pick",3,"function"],["Shape.describeArea",12,"function"]],"50149cf7ea5bebd032878402bbf7e3a8fc65b058e4b68ccf7de799a189dc03f6");export function pick(value: string): string;
export function pick(value: number): number;
export function pick(value: string | number): string | number {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(value));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

declare function ambient(value: string): void;

export abstract class Shape {
  abstract area(): number;

  describeArea(): string {const __sf=__srt.call(__sfile,1);try{
    return __srt.ret(__sf,(String(this.area())));
  ;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
}
