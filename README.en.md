# landxml2tri

`landxml2tri` is a Python tool that converts triangles from a LandXML TIN surface into a plain text format (one triangle per line), using `Pnts` and `Faces` directly.

It does not interpolate or rebuild geometry. Instead, it restores each triangle by directly resolving point IDs listed in `Faces`.

## Features

- Works with Python 3 and mostly the standard library.
- Supports LandXML files with XML namespaces.
- Lets you select a target surface when multiple surfaces exist.
- Correctly restores triangles even when point IDs are non-sequential.
- Skips invalid faces with warnings and reports totals at the end.

## Input and Output Format

Input: LandXML file  
Output: plain text file with one triangle per line

Each output line contains 9 values:

```text
x1 y1 z1 x2 y2 z2 x3 y3 z3
```

## Usage

```bash
python landxml_to_tin_txt.py input.xml output.txt
python landxml_to_tin_txt.py input.xml output.txt --surface "Existing Ground"
python landxml_to_tin_txt.py input.xml output.txt --coord-order xyz
python landxml_to_tin_txt.py input.xml output.txt --precision 3
```

## Options

- `--surface`: Specify a target name when multiple TIN surfaces exist.
- `--coord-order`: Interpret `P` element values as `xyz` or `yxz`. Output is always written as `x y z`.
- `--precision`: Number of decimal places for output formatting. Default is 3.

## Behavior

- Only TIN surfaces that contain `Surface / Definition / Pnts / Faces` are processed.
- If no surface name is specified and exactly one TIN surface exists, it is selected automatically.
- If no surface name is specified and multiple TIN surfaces exist, the tool prints candidates and exits.
- If an `F` element is empty, is not a triangle, has duplicate vertices, or references undefined point IDs, it is skipped with a warning.
- At the end, the tool reports:
  - Number of loaded points
  - Number of loaded faces
  - Number of exported triangles
  - Number of skipped invalid faces

## Sample Output

```text
1.000 2.000 3.000 4.000 5.000 6.000 7.000 8.000 9.000
10.000 11.000 12.000 13.000 14.000 15.000 16.000 17.000 18.000
```

## Tests

```bash
pytest
python -m unittest discover -s tests -v
```

`tests/test_landxml_to_tin_txt.py` verifies conversion from sample XML, handling of multiple surfaces, invalid-face counting, and the `--coord-order` and `--precision` options.

## Included Files

- `landxml_to_tin_txt.py`: main CLI script
- `samples/sample_landxml.xml`: small sample LandXML
- `tests/test_landxml_to_tin_txt.py`: minimal automated tests
- `pytest.ini`: pytest configuration

## License

MIT License
