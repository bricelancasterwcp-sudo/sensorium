import * as __srt from "RT";const __sfile=__srt.file("src/not-a-task.ts","/w/src/not-a-task.ts",[["describe",3,"function"]],"2aed90d81c7d841e76c9f563cb6039734756ea669613f9da8e05d6326b509856");// A local `describe` helper, and a test whose callback is not written inline:
// neither is a task boundary, and neither is rewritten.
function describe(label: string, formula: string, value: number): string {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(`${label}: ${formula} = ${value}`));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}

const summary = describe("attack", "1d20", 12);

test("shared", sharedCase);

it.each(table)("shared %s", sharedCase);
