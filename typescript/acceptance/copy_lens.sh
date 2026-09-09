# Sourced, not run: `copy_lens <src> <dst>` -- a throwaway copy of a consumer
# tree for a control that edits source.
#
# `rsync -a --exclude node_modules` plus a SYMLINK to the original's
# `node_modules`. The dependencies are half a gigabyte and are not what any
# control changes; a hard-linked copy would be worse than a symlink, because
# a tool that truncates a cached file in place would write THROUGH the link
# into the original.
copy_lens() {
  local src="$1" dst="$2"
  rm -rf "$dst"
  mkdir -p "$dst"
  rsync -a --exclude node_modules --exclude 'dist' --exclude '.pytest_cache' \
        --exclude 'e2e-shots' "$src"/ "$dst"/ || return 1
  ln -s "$src/node_modules" "$dst/node_modules" || return 1
}
