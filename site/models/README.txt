Импортированные 3D-модели вертолётов в компактном формате сайта:
  <key>.js   — геометрия (base64: int16 позиции, int8 нормали, uint16 UV), подключается как <script src>
  <key>.jpg  — текстура ливреи (грузится как обычная картинка)
Ключи: as350 (Eurocopter AS350), mi8amt (Ми-8АМТ), mi171 (Ми-171).
Ми-8АМТ/Ми-171 создаёт build/import/build_mi8.sh (ливрея livery_mi8.py → pack_mi8.py → glb2js.py → mi8_extras.py) из несжатого .glb (метры, нос по +X, верх по +Y, y=0 — земля;
узлы MainRotor/TailRotor — группы винтов). После добавления/удаления файла выполните python3 build/build.py.
.glb рядом — запасной формат (meshopt) для обычного хостинга, сайтом не используется.
AS350 создаёт build/import/pack_as350.py прямо из модели FlightGear (AC3D, build/import/as350src) —
атлас 4096×2048, ливрея RA-04062 (livery_as350.py), флаги m:'glass' (стекло) и side:'front' (односторонние грани).
Флаги формата: m:'glass' (прозрачное стекло), m:'window' (тонированное стекло окон), side:'front' (односторонние грани), mat:{metalness,roughness}.
Фон 3D — сцена «Карасук» в site/scene/ (build/terrain/build_karasuk.py).
