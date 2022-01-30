POC: Force static type hints via import

This runs mypy on all imports, and currently just dumps the text, but
that shows the concept.

Properly hooking both path and file imports might requir something
more, and raising proper import errors when files don't pass is also
left to do.

However, conceptually it sort of works, and simply importing it in a
software can toggle the flag on to force strict typing more.

If I ever get around to it, I might clean it up, but now it's 2 AM and
I've finished my trappist for the night, so we leave it here.
