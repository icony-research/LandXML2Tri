"""Convert LandXML TIN surfaces into one-triangle-per-line text."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


PointId = str
PointValues = Tuple[str, str, str]
TriangleFace = Tuple[PointId, PointId, PointId]


@dataclass(frozen=True)
class SurfaceData:
    """Represents a TIN surface found in a LandXML document."""

    name: str
    surface_element: ET.Element
    namespace: str


@dataclass(frozen=True)
class FaceIssue:
    """Represents an invalid face and the reason it was skipped."""

    face_text: str
    reason: str


def _extract_namespace(tag: str) -> str:
    """Return the XML namespace from a tag, or an empty string."""

    if tag.startswith("{") and "}" in tag:
        return tag[1 : tag.index("}")]
    return ""


def _ns_tag(namespace: str, local_name: str) -> str:
    """Build a namespace-aware element tag."""

    return f"{{{namespace}}}{local_name}" if namespace else local_name


def parse_landxml_surfaces(path: Path) -> List[SurfaceData]:
    """Parse a LandXML file and return all TIN surfaces."""

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise ValueError(f"Failed to parse XML '{path}': {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read input file '{path}': {exc}") from exc

    root = tree.getroot()
    namespace = _extract_namespace(root.tag)
    surfaces: List[SurfaceData] = []

    for surface in root.iter(_ns_tag(namespace, "Surface")):
        definition = surface.find(_ns_tag(namespace, "Definition"))
        if definition is None:
            continue

        surf_type = (definition.get("surfType") or definition.get("surfaceType") or "").strip()
        if surf_type and surf_type.lower() != "tin":
            continue

        if definition.find(_ns_tag(namespace, "Pnts")) is None:
            continue
        if definition.find(_ns_tag(namespace, "Faces")) is None:
            continue

        name = (surface.get("name") or "").strip() or "<unnamed>"
        surfaces.append(SurfaceData(name=name, surface_element=surface, namespace=namespace))

    return surfaces


def select_surface(surfaces: Sequence[SurfaceData], surface_name: Optional[str]) -> SurfaceData:
    """Select the requested surface or infer it when unambiguous."""

    if not surfaces:
        raise ValueError("No TIN surface with Definition/Pnts/Faces was found in the input file.")

    if surface_name:
        for surface in surfaces:
            if surface.name == surface_name:
                return surface
        names = ", ".join(surface.name for surface in surfaces)
        raise ValueError(
            f"Surface '{surface_name}' was not found. Available TIN surfaces: {names}"
        )

    if len(surfaces) == 1:
        return surfaces[0]

    names = "\n".join(f"  - {surface.name}" for surface in surfaces)
    raise ValueError(
        "Multiple TIN surfaces were found. Specify one with --surface.\n"
        f"Available surfaces:\n{names}"
    )


def _reorder_coordinates(values: Sequence[str], coord_order: str) -> PointValues:
    """Normalize raw coordinate strings into XYZ order."""

    if len(values) != 3:
        raise ValueError(f"Point must contain exactly 3 coordinates, got {len(values)} values.")

    if coord_order == "xyz":
        return values[0], values[1], values[2]
    if coord_order == "yxz":
        return values[1], values[0], values[2]
    raise ValueError(f"Unsupported coord_order '{coord_order}'. Expected 'xyz' or 'yxz'.")


def extract_points_and_faces(
    surface: SurfaceData, coord_order: str
) -> Tuple[Dict[PointId, PointValues], List[List[str]]]:
    """Extract points and raw face ID lists from a TIN surface."""

    definition = surface.surface_element.find(_ns_tag(surface.namespace, "Definition"))
    if definition is None:
        raise ValueError(f"Surface '{surface.name}' is missing a Definition element.")

    points_container = definition.find(_ns_tag(surface.namespace, "Pnts"))
    faces_container = definition.find(_ns_tag(surface.namespace, "Faces"))
    if points_container is None or faces_container is None:
        raise ValueError(
            f"Surface '{surface.name}' is missing required Pnts or Faces elements."
        )

    points: Dict[PointId, PointValues] = {}
    for point in points_container.findall(_ns_tag(surface.namespace, "P")):
        point_id = (point.get("id") or point.get("name") or "").strip()
        if not point_id:
            raise ValueError(f"Surface '{surface.name}' contains a P element without an id.")

        raw_text = (point.text or "").strip()
        values = raw_text.split()
        if len(values) != 3:
            raise ValueError(
                f"Surface '{surface.name}' point id '{point_id}' does not contain 3 coordinates: "
                f"'{raw_text}'"
            )

        points[point_id] = _reorder_coordinates(values, coord_order)

    faces: List[List[str]] = []
    for face in faces_container.findall(_ns_tag(surface.namespace, "F")):
        raw_text = (face.text or "").strip()
        face_ids = raw_text.split() if raw_text else []
        faces.append(face_ids)

    return points, faces


def validate_face(face_ids: Sequence[str], points_dict: Dict[PointId, PointValues]) -> Optional[str]:
    """Validate a face and return an error reason when invalid."""

    if len(face_ids) != 3:
        return f"expected 3 point ids but found {len(face_ids)}"

    if len(set(face_ids)) != 3:
        return "contains duplicate point ids"

    missing_ids = [point_id for point_id in face_ids if point_id not in points_dict]
    if missing_ids:
        return f"references missing point ids: {', '.join(missing_ids)}"

    return None


def _format_value(value: str, precision: Optional[int]) -> str:
    """Format a coordinate value for output."""

    if precision is None:
        precision = 3
    return f"{float(value):.{precision}f}"


def write_triangle_txt(
    path: Path,
    faces: Iterable[Sequence[str]],
    points_dict: Dict[PointId, PointValues],
    precision: Optional[int] = None,
) -> Tuple[int, List[FaceIssue]]:
    """Write valid triangles to a text file and return statistics."""

    written = 0
    issues: List[FaceIssue] = []

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for face_ids in faces:
            reason = validate_face(face_ids, points_dict)
            face_text = " ".join(face_ids)
            if reason is not None:
                issues.append(FaceIssue(face_text=face_text, reason=reason))
                continue

            coordinates: List[str] = []
            for point_id in face_ids:
                point_values = points_dict[point_id]
                coordinates.extend(_format_value(value, precision) for value in point_values)

            handle.write(" ".join(coordinates) + "\n")
            written += 1

    return written, issues


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Convert a LandXML TIN surface into one triangle per text line."
    )
    parser.add_argument("input", type=Path, help="Input LandXML file path.")
    parser.add_argument("output", type=Path, help="Output txt file path.")
    parser.add_argument(
        "--surface",
        help="Name of the TIN surface to export when multiple surfaces exist.",
    )
    parser.add_argument(
        "--coord-order",
        choices=("xyz", "yxz"),
        default="xyz",
        help="Interpretation of P element values before normalizing to XYZ output.",
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=3,
        help="Decimal precision for output values. Defaults to 3.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.precision is not None and args.precision < 0:
        parser.error("--precision must be 0 or greater.")

    try:
        print(f"Reading LandXML: {args.input}")
        surfaces = parse_landxml_surfaces(args.input)
        print(f"Found {len(surfaces)} TIN surface(s).")
        if surfaces:
            print("Available surfaces:")
            for surface in surfaces:
                print(f"  - {surface.name}")

        selected_surface = select_surface(surfaces, args.surface)
        print(f"Using surface: {selected_surface.name}")

        points_dict, raw_faces = extract_points_and_faces(selected_surface, args.coord_order)
        print(f"Loaded {len(points_dict)} point(s).")
        print(f"Loaded {len(raw_faces)} face(s).")

        triangles_written, issues = write_triangle_txt(
            args.output, raw_faces, points_dict, precision=args.precision
        )

        for issue in issues:
            face_label = issue.face_text if issue.face_text else "<empty>"
            print(f"Warning: skipped face '{face_label}': {issue.reason}", file=sys.stderr)

        print(f"Wrote {triangles_written} triangle(s) to {args.output}")
        print("Summary:")
        print(f"  Read points: {len(points_dict)}")
        print(f"  Read faces: {len(raw_faces)}")
        print(f"  Written triangles: {triangles_written}")
        print(f"  Skipped invalid faces: {len(issues)}")
        return 0
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
