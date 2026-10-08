// Render MIL-STD-2525 symbols from a SIDC to a monochrome SVG, using milsymbol.
//
// milsymbol (https://github.com/spatialillusions/milsymbol, MIT) draws the
// standard's own geometry: the frame for the affiliation and battle dimension,
// and the function glyph.  Monochrome so the engine marker colour tints it.
//
// usage: node tools/milsymbol_render.mjs <manifest.json>
//   manifest: [ { "sidc": "SFGPUCI-------", "out": "/abs/out.svg" }, ... ]
import fs from "node:fs";
import path from "node:path";

const ENTRY =
  process.env.MILSYMBOL_ENTRY ||
  "/tmp/opencode/milsym/node_modules/milsymbol/index.js";

const mod = await import(ENTRY);
const ms = mod.default ?? mod;

const manifest = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
for (const job of manifest) {
  const symbol = new ms.Symbol(job.sidc, {
    size: job.size || 256,
    monoColor: "#FFFFFF",
    infoFields: false,
  });
  fs.mkdirSync(path.dirname(job.out), { recursive: true });
  fs.writeFileSync(job.out, symbol.asSVG());
}
console.log(`milsymbol: rendered ${manifest.length} svg`);
