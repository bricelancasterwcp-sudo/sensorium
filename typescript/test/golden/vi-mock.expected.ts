import * as __srt from "RT";const __sfile=__srt.file("src/vi-mock.ts","/w/src/vi-mock.ts",[["useSeed",11,"function"]],"f9aa156c6e234ac5d878590935c12910ecf9d18d49fd31aa25d3cbcecac59baa");import { vi } from "vitest";

vi.mock("./api", () => ({
  fetchUser: vi.fn(() => Promise.resolve({ id: 1 })),
}));

const seed = vi.hoisted(() => {
  return 7;
});

export function useSeed(): number {const __sf=__srt.call(__sfile,0);try{
  return __srt.ret(__sf,(seed));
;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
