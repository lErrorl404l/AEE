#!/bin/sh
# AEE docker test entrypoint.
# The arma3server wrapper misparses an empty ARMA3_SERVER__CDLC; unset it.
unset ARMA3_SERVER__CDLC
# Symlink every mod in server/mods into the game dir so the server resolves
# them, then hand over to the arma3server wrapper (which reads config.toml).
for m in /arma3/server/mods/@*; do
    [ -e "$m" ] || continue
    base=$(basename "$m")
    ln -sfn "$m" "/arma3/server/$base"
done
exec /usr/local/bin/arma3server
