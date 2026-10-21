"""Reproducible source-dependent RGBA XOR deltas for reviewed raster artwork.

The repository stores differences, not complete source or generated textures.
Resizing is an explicit asset-import operation, never runtime font substitution.
"""
from __future__ import annotations
import base64
import hashlib
import io
import json
from pathlib import Path
import zlib
from PIL import Image


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capture(original, edited, *, resource, prompt, regions=None):
    if original.mode != 'RGBA' or edited.mode != 'RGBA' or original.size != edited.size:
        raise ValueError('Art import must already have matching RGBA dimensions')
    a,b=original.tobytes(),edited.tobytes()
    return dict(schema=1,format='source-rgba-xor-zlib-v1',resource=resource,
                size=list(original.size),source_pixels_sha256=sha(a),output_pixels_sha256=sha(b),
                xor=base64.b64encode(zlib.compress(bytes(x^y for x,y in zip(a,b)),9)).decode('ascii'),
                reviewed_regions=regions or [[0,0,*original.size]],
                workflow='imagegen artwork edit, reviewed import; no runtime pixel-font overlay',
                prompt=prompt)


def apply(original, patch):
    if patch.get('schema')!=1 or patch.get('format')!='source-rgba-xor-zlib-v1':
        raise ValueError('Unsupported art delta format')
    original=original.convert('RGBA')
    if list(original.size)!=patch['size'] or sha(original.tobytes())!=patch['source_pixels_sha256']:
        raise ValueError('Artwork source pixels mismatch')
    raw=original.tobytes(); decoder=zlib.decompressobj()
    delta=decoder.decompress(base64.b64decode(patch['xor'],validate=True),len(raw)+1)
    if len(delta)!=len(raw) or not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
        raise ValueError('Invalid art delta length')
    pixels=bytes(x^y for x,y in zip(raw,delta))
    if sha(pixels)!=patch['output_pixels_sha256']:
        raise ValueError('Artwork result hash mismatch')
    return Image.frombytes('RGBA',original.size,pixels)


def png(image):
    out=io.BytesIO();image.save(out,format='PNG',compress_level=9)
    return out.getvalue()
