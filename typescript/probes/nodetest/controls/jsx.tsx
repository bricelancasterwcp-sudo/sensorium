// A control, not a test file. `.tsx` and `.jsx` throw
// `ERR_UNKNOWN_FILE_EXTENSION` inside `nextLoad`, before any `load` hook
// runs, so this file never reaches the recorder at all: it is outside NODE's
// scope under `node --test`, not an exclusion of ours. The recorder does not
// make it loadable -- H2.
const x = <div />;

console.log(typeof x);
