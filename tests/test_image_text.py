"""Synthetic bitmap recipe tests: no proprietary game resources or installed fonts."""
import copy
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from image_text import build_images, erase_ink


class Archive:
    def __init__(self, raw):
        self.raw = raw
    def read(self, name):
        if name != "TEXTURES/EN/LABEL.PNG":
            raise KeyError(name)
        return self.raw


def font_fixture(path):
    fb = FontBuilder(1000, isTTF=True)
    glyphs = [".notdef", "A", "B", "uni4E2D"]
    fb.setupGlyphOrder(glyphs)
    fb.setupCharacterMap({65: "A", 66: "B", 0x4E2D: "uni4E2D"})
    outlines = {}
    for name in glyphs:
        pen = TTGlyphPen(None)
        pen.moveTo((100, 0)); pen.lineTo((600, 0)); pen.lineTo((600, 700)); pen.lineTo((100, 700)); pen.closePath()
        outlines[name] = pen.glyph()
    fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics({g: (800, 0) for g in glyphs})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName":"Synthetic Fixture", "styleName":"Regular"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost(); fb.setupMaxp(); fb.save(path)


class ImageTextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.font = Path(self.tmp.name) / "fixture.ttf"
        font_fixture(self.font)
        im = Image.new("RGBA", (64, 32), (20, 30, 40, 255))
        im.putpixel((2,2), (255,0,0,255))
        stream = io.BytesIO(); im.save(stream, format="PNG")
        self.raw = stream.getvalue(); self.zar = Archive(self.raw)
        self.config = {"images":[{"resource":"TEXTURES/EN/LABEL.PNG", "source_sha256": hashlib.sha256(self.raw).hexdigest(),
            "size":[64,32], "labels":[{"source":"AB", "target":"中", "box":[20,10,44,26]}]}]}

    def test_deterministic_and_preserves_every_pixel_outside_regions(self):
        a, report = build_images(self.zar, self.config, self.font)
        b, _ = build_images(self.zar, self.config, self.font)
        self.assertEqual(a,b)
        result = Image.open(io.BytesIO(next(iter(a.values())))).convert("RGBA")
        original = Image.open(io.BytesIO(self.raw)).convert("RGBA")
        self.assertEqual(result.size, original.size)
        for y in range(32):
            for x in range(64):
                if not (20 <= x < 44 and 10 <= y < 26):
                    self.assertEqual(result.getpixel((x,y)), original.getpixel((x,y)))
        self.assertTrue(report["images"][0]["outside_regions_unchanged"])

    def test_unknown_source_hash_rejected(self):
        self.config["images"][0]["source_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError,"identity"):
            build_images(self.zar,self.config,self.font)

    def test_unknown_dimensions_rejected(self):
        self.config["images"][0]["size"] = [65,32]
        with self.assertRaisesRegex(ValueError,"dimensions"):
            build_images(self.zar,self.config,self.font)

    def test_missing_glyph_rejected_instead_of_tofu(self):
        self.config["images"][0]["labels"][0]["target"] = "文"
        with self.assertRaisesRegex(ValueError,r"U\+6587"):
            build_images(self.zar,self.config,self.font)

    def test_overflow_rejected(self):
        self.config["images"][0]["labels"][0]["target"] = "中"*9
        with self.assertRaisesRegex(ValueError,"overflow"):
            build_images(self.zar,self.config,self.font)

    def test_out_of_bounds_rejected(self):
        self.config["images"][0]["labels"][0]["box"] = [-1,0,20,20]
        with self.assertRaisesRegex(ValueError,"outside"):
            build_images(self.zar,self.config,self.font)

    def test_clear_regions_bounded_and_icons_preserved(self):
        self.config["images"][0]["clear_regions"] = [{"box":[20,0,44,9]}]
        out, _ = build_images(self.zar,self.config,self.font)
        im = Image.open(io.BytesIO(next(iter(out.values()))))
        self.assertEqual(im.getpixel((2,2)), (255,0,0,255))
        self.assertEqual(im.getpixel((21,1)), (0,0,0,0))

    def test_clear_region_outside_rejected(self):
        self.config["images"][0]["clear_regions"] = [{"box":[20,0,65,9]}]
        with self.assertRaisesRegex(ValueError,"outside"):
            build_images(self.zar,self.config,self.font)

    def test_ink_infill_preserves_non_ink_grain(self):
        im=Image.new("RGBA",(32,24),(32,3,2,255))
        for y in range(24):
            for x in range(32): im.putpixel((x,y),(20+x+y,3,2,255))
        original=im.copy()
        for x in range(12,17): im.putpixel((x,12),(240,230,225,255))
        changed=erase_ink(im,{"box":[8,8,23,18],"ink":"light","threshold":{"min_green":38}})
        self.assertGreater(changed,0)
        self.assertLess(im.getpixel((14,12))[1],38)
        for y in range(24):
            for x in range(32):
                if not (11 <= x <= 17 and 11 <= y <= 13):
                    self.assertEqual(im.getpixel((x,y)),original.getpixel((x,y)))

    def test_ink_infill_rejects_unknown_bounds(self):
        with self.assertRaisesRegex(ValueError,"outside"):
            erase_ink(Image.new("RGBA",(8,8)),{"box":[0,0,10,8],"ink":"light"})

    def test_repository_ui_targets_obey_punctuation_rule(self):
        import json
        config=json.loads((Path(__file__).resolve().parents[1]/"locales/zh-CN/image-text.json").read_text("utf-8"))
        for recipe in config["images"]:
            for label in recipe["labels"]:
                self.assertFalse(label["target"].endswith("。"))


if __name__ == "__main__":
    unittest.main()
