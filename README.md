# Force static type hints at import time

This runs mypy on all imports, and currently just dumps the text, but
that shows the concept.

Properly hooking both path and file imports might requir something
more, and raising proper import errors when files don't pass is also
left to do.

However, conceptually it sort of works, and simply importing it in a
software can toggle the flag on to force strict typing more.

To use it, add  "import typeforce.enforcing"  to the modules of the initial
code, and watch your code explode when you have a badly typed module.

Also note, that imports will not just be slow, they will be very slow.


[![asciicast](https://asciinema.org/a/4DbpNJvuvspyQGzt6VMlbd6MD.svg)](https://asciinema.org/a/4DbpNJvuvspyQGzt6VMlbd6MD)
