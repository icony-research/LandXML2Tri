"""Tests for the LandXML to triangle text converter."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import shutil

from landxml_to_tin_txt import (
    extract_points_and_faces,
    main,
    parse_landxml_surfaces,
    select_surface,
    write_triangle_txt,
)


SAMPLE_PATH = Path(__file__).resolve().parents[1] / "samples" / "sample_landxml.xml"
WORK_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test_tmp"


class LandxmlToTinTxtTests(unittest.TestCase):
    """Coverage for LandXML TIN export behavior."""

    def setUp(self) -> None:
        """Prepare a writable temp directory inside the workspace."""

        WORK_TMP_ROOT.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        """Clean up workspace-local temporary files."""

        if WORK_TMP_ROOT.exists():
            shutil.rmtree(WORK_TMP_ROOT)

    def _case_dir(self, name: str) -> Path:
        """Return an isolated temporary directory for the current test."""

        path = WORK_TMP_ROOT / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_parse_and_select_surface(self) -> None:
        """Selecting by surface name should work when multiple surfaces exist."""

        surfaces = parse_landxml_surfaces(SAMPLE_PATH)

        self.assertEqual([surface.name for surface in surfaces], ["Existing Ground", "Design"])
        selected = select_surface(surfaces, "Existing Ground")
        self.assertEqual(selected.name, "Existing Ground")

    def test_select_surface_requires_name_when_multiple(self) -> None:
        """An explicit surface name is required when multiple TIN surfaces exist."""

        surfaces = parse_landxml_surfaces(SAMPLE_PATH)

        with self.assertRaisesRegex(ValueError, "Multiple TIN surfaces were found"):
            select_surface(surfaces, None)

    def test_extract_and_write_triangles(self) -> None:
        """Valid triangles should be written without interpolation."""

        surface = select_surface(parse_landxml_surfaces(SAMPLE_PATH), "Existing Ground")
        points, faces = extract_points_and_faces(surface, coord_order="xyz")

        output_path = self._case_dir("extract_and_write") / "triangles.txt"
        written, issues = write_triangle_txt(output_path, faces, points)

        self.assertEqual(len(points), 4)
        self.assertEqual(len(faces), 6)
        self.assertEqual(written, 2)
        self.assertEqual(len(issues), 4)
        self.assertEqual(
            output_path.read_text(encoding="utf-8").splitlines(),
            [
                "1.000 2.000 3.000 4.000 5.000 6.000 7.000 8.000 9.000",
                "4.000 5.000 6.000 7.000 8.000 9.000 10.000 11.000 12.000",
            ],
        )

    def test_coord_order_and_precision(self) -> None:
        """Coordinate order and precision options should affect output formatting only."""

        surface = select_surface(parse_landxml_surfaces(SAMPLE_PATH), "Design")
        points, faces = extract_points_and_faces(surface, coord_order="yxz")

        output_path = self._case_dir("coord_order") / "design.txt"
        written, issues = write_triangle_txt(output_path, faces, points, precision=2)

        self.assertEqual(written, 1)
        self.assertEqual(issues, [])
        self.assertEqual(
            output_path.read_text(encoding="utf-8").strip(),
            "0.00 0.00 0.00 0.00 1.00 0.00 1.00 0.00 0.00",
        )

    def test_main_generates_summary_and_warnings(self) -> None:
        """CLI main should complete and report statistics plus warnings."""

        output_path = self._case_dir("main_cli") / "cli_output.txt"
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = main(
                [
                    str(SAMPLE_PATH),
                    str(output_path),
                    "--surface",
                    "Existing Ground",
                    "--precision",
                    "1",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("Read points: 4", stdout_buffer.getvalue())
        self.assertIn("Read faces: 6", stdout_buffer.getvalue())
        self.assertIn("Written triangles: 2", stdout_buffer.getvalue())
        self.assertIn("Skipped invalid faces: 4", stdout_buffer.getvalue())
        self.assertIn("Warning: skipped face", stderr_buffer.getvalue())
        self.assertEqual(len(output_path.read_text(encoding="utf-8").splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
