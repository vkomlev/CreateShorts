import tempfile
import unittest
from pathlib import Path

import reframe


class SrtTests(unittest.TestCase):
    def test_parse_slice_and_normalize_srt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.srt"
            source.write_text(
                "1\n0:00:09,500 --> 0:00:11,000\nB\n\n"
                "2\n0:00:12,300 --> 0:00:15,100\nA\n\n"
                "3\n0:00:17,000 --> 0:00:19,500\nC\n\n"
                "4\n0:00:20,000 --> 0:00:22,000\nD\n",
                encoding="utf-8",
            )
            cues = reframe.parse_srt(source)
            sliced = reframe.slice_srt(cues, 10.0, 18.0)
            self.assertEqual(
                sliced,
                [
                    reframe.Cue(0, 1.0, "B"),
                    reframe.Cue(2.3000000000000007, 5.1, "A"),
                    reframe.Cue(7.0, 8.0, "C"),
                ],
            )
            output = Path(temp_dir) / "sliced.srt"
            reframe.write_srt(output, sliced)
            self.assertIn("00:00:00,000 --> 00:00:01,000", output.read_text(encoding="utf-8"))
            self.assertIn("00:00:02,300 --> 00:00:05,100", output.read_text(encoding="utf-8"))

    def test_escape_subtitles_path_escapes_drive_colon(self) -> None:
        escaped = reframe.escape_subtitles_path(r"C:\temp\segment.srt")
        self.assertIn(r"C\:/temp/segment.srt", escaped)

    def test_slice_srt_can_return_no_cues(self) -> None:
        self.assertEqual(reframe.slice_srt([reframe.Cue(1, 2, "before")], 3, 4), [])

    def test_parse_segments_accepts_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "segments.txt"
            source.write_text("0-1,letterbox\n", encoding="utf-8-sig")
            self.assertEqual(reframe.parse_segments(str(source)), [reframe.Segment(0, 1, "letterbox", None)])


class FilterTests(unittest.TestCase):
    def test_subtitles_follow_reframe_filter(self) -> None:
        segment = reframe.Segment(0, 8, "letterbox", None)
        filter_complex = reframe.build_filter(segment, r"C:\temp\segment.srt")
        self.assertIn(
            "overlay=(W-w)/2:(H-h)/2,setsar=1,trim=duration=8,setpts=PTS-STARTPTS[v];[v]subtitles=",
            filter_complex,
        )
        self.assertIn("MarginV=105", filter_complex)
        self.assertTrue(filter_complex.endswith("[vout]"))


if __name__ == "__main__":
    unittest.main()
