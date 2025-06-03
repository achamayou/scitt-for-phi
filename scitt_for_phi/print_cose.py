import cbor2
import sys
import pprint


def expand_phdr(cose: cbor2.types.CBORTag) -> cbor2.types.CBORTag:
    cose.value[0] = cbor2.loads(cose.value[0])
    return cose


def main():
    if len(sys.argv) != 2:
        print("Usage: print_cose <cbor_path>")
        sys.exit(1)

    with open(sys.argv[1], "rb") as cbor_file:
        cose = cbor2.load(cbor_file)
        assert cose.tag == 18
        print(f"Tag {cose.tag} ".ljust(80, "="))
        cose = expand_phdr(cose)
        print("Protected Header ".ljust(80, "="))
        phdr = cose.value[0]
        pprint.pp(phdr, indent=2)
        print("Unprotected Header ".ljust(80, "="))
        uhdr = cose.value[1]
        if 394 in uhdr:
            uhdr[394] = [expand_phdr(cbor2.loads(vdp)).value for vdp in uhdr[394]]
        pprint.pp(uhdr, indent=2)
        print("Payload ".ljust(80, "="))
        pprint.pp(cose.value[2], indent=2)
        print("Signature ".ljust(80, "="))
        pprint.pp(cose.value[3], indent=2)
    sys.exit(0)


if __name__ == "__main__":
    main()
