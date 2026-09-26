#!/bin/bash
# Полный конвейер Ми-8АМТ / Ми-171 «АлтайАвиа» из модели Mil Mi-8AMTSh (Sketchfab, CC BY 4.0):
#   livery_mi8.py (ливрея по фото бортов, 4096 px) → pack_mi8.py (без вооружения/ЭВУ, оси сайта, палитра шасси)
#   → gltf-transform dequantize + simplify → glb2js.py (site/models/<L>.js) → mi8_extras.py (окна, металлик)
#   → текстура site/models/<L>.jpg; .glb (meshopt) — запасной формат для обычного хостинга, сайтом не используется.
set -e
cd "$(dirname "$0")/../.."
SRC=build/import/mi8amtsh/scene.gltf
for L in ${@:-mi8amt mi171}; do
  python3 build/import/livery_mi8.py $L
  python3 build/import/pack_mi8.py "$SRC" build/import/${L}_texture.jpg build/import/${L}_full.glb
  npx -y @gltf-transform/cli@4 dequantize build/import/${L}_full.glb build/import/${L}_f.glb
  npx -y @gltf-transform/cli@4 simplify --ratio 0.1 --error 0.003 build/import/${L}_f.glb build/import/${L}_s.glb
  python3 build/import/glb2js.py build/import/${L}_s.glb site/models/${L}.js ${L}.jpg
  python3 build/import/mi8_extras.py $L
  python3 -c "from PIL import Image; Image.open('build/import/${L}_texture.jpg').save('site/models/${L}.jpg', quality=84, optimize=True, progressive=True)"
  npx -y @gltf-transform/cli@4 meshopt --level medium build/import/${L}_s.glb site/models/${L}.glb
  python3 build/import/make_tex2k.py $L          # текстура 2048 px для телефонов
  rm -f build/import/${L}_f.glb build/import/${L}_s.glb site/models/${L}.json
done
ls -la site/models/
