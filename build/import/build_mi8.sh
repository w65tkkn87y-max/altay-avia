#!/bin/bash
# Полный конвейер Ми-8АМТ / Ми-171 из модели Sketchfab (после запекания текстур в браузере, см. README):
#   bake (site/_bake.html → img/3d/_bake_<livery>.png) → compose_texture → pack_mi8 → gltf-transform dequantize + simplify
#   → glb2js (компактная модель site/models/<L>.js + текстура site/models/<L>.jpg — то, что использует сайт)
#   → meshopt .glb (запасной формат для обычного хостинга, сайтом не используется)
set -e
cd "$(dirname "$0")/../.."
SRC=build/import/mi8amtsh/scene.gltf
ORIG=build/import/mi8amtsh/textures/wire_140088225_baseColor.png
for L in mi8amt mi171; do
  if [ -f site/img/3d/_bake_$L.png ]; then python3 build/import/compose_texture.py site/img/3d/_bake_$L.png "$ORIG" build/import/${L}_texture.jpg 2048; else echo "bake for $L not found — using existing build/import/${L}_texture.jpg"; fi
  python3 build/import/pack_mi8.py "$SRC" build/import/${L}_texture.jpg build/import/${L}_full.glb
  npx -y @gltf-transform/cli@4 dequantize build/import/${L}_full.glb build/import/${L}_f.glb
  npx -y @gltf-transform/cli@4 simplify --ratio 0.1 --error 0.003 build/import/${L}_f.glb build/import/${L}_s.glb
  python3 build/import/glb2js.py build/import/${L}_s.glb site/models/${L}.js ${L}.jpg
  cp build/import/${L}_texture.jpg site/models/${L}.jpg
  npx -y @gltf-transform/cli@4 meshopt --level medium build/import/${L}_s.glb site/models/${L}.glb
  rm -f build/import/${L}_f.glb build/import/${L}_s.glb site/models/${L}.json
done
ls -la site/models/
