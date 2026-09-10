// A control, not a test file. An `enum` has runtime meaning, so Node's
// strip-only mode refuses the file BY NAME rather than erasing anything:
// `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`, plain and under this recorder alike.
// The old hook ran the consumer's `transpileModule` over the file and EMITTED
// an enum, so a program plain `node` will not load loaded under the recorder
// -- a recorder that changes what loads is changing the program.
enum Colour {
  Red = 1,
  Blue = 2,
}

console.log(Colour.Red);
