import cbor2
import sys


def main():
    """
    A CLI script that takes a signed statement in COSE format
    and a receipt also in COSE format, and inserts the receipt
    into the statement's unprotected header, at the 394 parameter,
    appending to the array if it already exists.
    The resulting statement is written to standard output.
    """
    if len(sys.argv) != 3:
        print("Usage: staple_receipt <statement_path> <receipt_path> > <output_path>")
        print(main.__doc__)
        sys.exit(1)

    statement_path = sys.argv[1]
    receipt_path = sys.argv[2]

    with open(statement_path, "rb") as f:
        statement = cbor2.load(f)

    with open(receipt_path, "rb") as f:
        receipt = f.read()

    uhdr = statement.value[1]
    if 394 not in uhdr:
        uhdr[394] = []
    uhdr[394].append(receipt)
    statement.value[1] = uhdr

    sys.stdout.buffer.write(cbor2.dumps(statement))
    sys.exit(0)


if __name__ == "__main__":
    main()
