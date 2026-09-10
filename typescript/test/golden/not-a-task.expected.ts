import * as __srt from "RT";const __sfile=__srt.file("src/not-a-task.ts","/w/src/not-a-task.ts",[["describe",3,"function"],["<anonymous>",9,"function"]],"41957bd71c05501b8e775e0a6a03cca8a1e5be0d272b90569f4a6234b858b75b");// Ordinary source: `describe` here is the consumer's own helper, and nothing in
// this file is a task, whatever shape the second argument takes.
function describe(label: string, formula: string, value: number): string {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(`${label}: ${formula} = ${value}`));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

const summary = describe("attack", "1d20", 12);

const mapped = describe("x", () => {const __sf=__srt.call(__sfile,1);try{return __srt.ret(__sf,(1))}catch(__se){__srt.thr(__sf,__se);throw __se}}, 2);

test("shared", sharedCase);

it.each(table)("shared %s", sharedCase);
