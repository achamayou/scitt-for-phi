import sys
import cbor2


def strip_uhdr(file_path: str) -> None:
    with open(file_path, "rb") as f:
        data = cbor2.load(f)
    assert data.tag == 18, "Expected COSE (tag 18)"

    data.value[1] = {}

    output_file_path = f"{file_path}.empty_uhdr"
    with open(output_file_path, "wb") as f:
        cbor2.dump(data, f)

    print(f"COSE with empty unprotected header written to {output_file_path}")


def main():
    """
    A CLI script that takes a path to a file,
    decodes it as COSE, replaces the unprotected header
    with an empty map, and writes the modified COSE to a different file
    with the same name but with an additional ".empty_uhdr" suffix.
    """
    if len(sys.argv) != 2:
        print("Usage: strip_uhdr <file_path>")
        print(main.__doc__)
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        strip_uhdr(file_path)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
