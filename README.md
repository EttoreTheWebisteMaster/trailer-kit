# trailer-kit (Made by Ettore)

Chunked HyperFrames trailers. One `film.py` per project builds every format.

```
kit/kit.py     Film, Chunk, Assets: photo/crop/words/cursor/dof/vignette, build, validate gate, cached chunk render, snapshot sheets
kit/mix.py     music offset + silence beat, synthesized SFX, loudnorm −16 LUFS / −1.5 dBTP, measure()
kit/vendor     gsap.min.js
projects/<p>/film.py   LOOK + scenes (chunks) + sound events
projects/<p>/assets    stills, fonts · audio/ track + beats json
LESSONS.md     read first
```

```
python3 projects/feeling/film.py 16x9 build              # write chunks, print warnings
python3 projects/feeling/film.py 16x9 snap 1.0,4.7,9.7 x # low-res review sheet
python3 projects/feeling/film.py 16x9 render             # validate → render changed chunks → concat → mix
python3 projects/feeling/film.py 9x16 render             # same scenes, vertical layout via L.pick()
```

Rules: each chunk is a standalone project (`build/<fmt>/NN_name`), cached by content hash, raw renders kept, so a fix re-renders only its chunk. Transitions live inside one chunk; chunks meet on hard or match cuts. Layout values go through `L.pick(h, v, p)`; time is film time.
