import cbor2
import sys
import hashlib
import struct
import ccf.cose
import cwt
from typing import List, Tuple
from pyscitt.verify import DynamicTrustStore


class MMR:
    """
    Namespace for MMR verification code, taken from the MRR Profile Individual Draft (draft-bryce-cose-receipts-mmr-profile).
    https://github.com/robinbryce/draft-bryce-cose-receipts-mmr-profile/blob/main/draft-bryce-cose-receipts-mmr-profile.md
    """

    @staticmethod
    def all_ones(pos: int) -> bool:
        """Returns true if all bits, starting with the most significant, are 1"""
        imsb = pos.bit_length() - 1
        mask = (1 << (imsb + 1)) - 1
        return pos == mask

    @staticmethod
    def most_sig_bit(pos: int) -> int:
        """Returns the mask for the the most significant bit in pos"""
        return 1 << (pos.bit_length() - 1)

    @staticmethod
    def index_height(i: int) -> int:
        """Returns the 0 based height of the mmr entry indexed by i"""
        # convert the index to a position to take advantage of the bit patterns afforded
        pos = i + 1
        while not MMR.all_ones(pos):
            pos = pos - (MMR.most_sig_bit(pos) - 1)

        return pos.bit_length() - 1

    @staticmethod
    def hash_pospair64(pos: int, a: bytes, b: bytes) -> bytes:
        """
        Compute the hash of  pos || a || b

        Args:
            pos (int): the 1-based position of an mmr node. If a, b are left and
                right children, pos should be the parent position.
            a (bytes): the first value to include in the hash
            b (bytes): the second value to include in the hash

        Returns:
            The value for the node identified by pos
        """
        h = hashlib.sha256()
        h.update(pos.to_bytes(8, byteorder="big", signed=False))
        h.update(a)
        h.update(b)
        return h.digest()

    @staticmethod
    def included_root(i: int, nodehash: bytes, proof: List[bytes]) -> bytes:
        """Apply the proof to nodehash to produce the implied root

        For a valid cose receipt of inclusion, using the returned root as the
        detached payload will result in a receipt message whose signature can be
        verified.

        Args:
            i (int): the mmr index where `nodehash` is located.
            nodehash (bytes): the value whose inclusion is being proven.
            proof (List[bytes]): the siblings required to produce `root` from `nodehash`.

        Returns:
            the root hash produced for `nodehash` using `path`
        """

        # set `root` to the value whose inclusion is to be proven
        root = nodehash

        # set g to the zero based height of i.
        g = MMR.index_height(i)

        # for each sibling in the proof
        for sibling in proof:
            # if the height of the entry immediately after i is greater than g, then
            # i is a right child.
            if MMR.index_height(i + 1) > g:
                # advance i to the parent. As i is a right child, the parent is at `i+1`
                i = i + 1
                # Set `root` to `H(i+1 || sibling || root)`
                root = MMR.hash_pospair64(i + 1, sibling, root)
            else:
                # Advance i to the parent. As i is a left child, the parent is at `i + (2^(g+1))`
                i = i + (2 << g)
                # Set `root` to `H(i+1 || root || sibling)`
                root = MMR.hash_pospair64(i + 1, root, sibling)

            # Set g to the height index above the current
            g = g + 1

        # Return the hash produced. If the path length was zero, the original nodehash is returned
        return root


class MMRUtils:
    """
    Utility functions for MMR verification.
    """

    @staticmethod
    def normserialised_cose_key(decoded_cose_key: dict) -> bytes:
        """
        Normalize a decoded COSE key to ensure it can be used for verification
        with python-cwt, which is strict about field types.
        """
        assert decoded_cose_key[1] == "EC"
        decoded_cose_key[1] = 2  # 'EC'
        assert decoded_cose_key[-1] == "P-256"
        decoded_cose_key[-1] = 1
        # kid must be a bstr
        decoded_cose_key[2] = str(decoded_cose_key[2]).encode()
        return cbor2.dumps(decoded_cose_key)

    @staticmethod
    def leaf_digest(statement: bytes, timestamp: bytes) -> bytes:
        """
        Compute the MMR leaf digest for a given statement and timestamp.
        """
        statement_phdr = cbor2.loads(statement)
        subject = cbor2.loads(statement_phdr.value[0])[15][2]
        extraBytes = subject[:24].encode()
        leaf_content = b"\0" + extraBytes + timestamp + statement
        return hashlib.sha256(leaf_content).digest()

    @staticmethod
    def root_and_cnf(statement: bytes, mmr_receipt: bytes) -> Tuple[bytes, bytes]:
        receipt = cbor2.loads(mmr_receipt)
        phdr = cbor2.loads(receipt.value[0])
        uhdr = receipt.value[1]

        cnf = phdr[15][8][1]
        cbor_cnf = MMRUtils.normserialised_cose_key(cnf)

        timestamp_int = uhdr[-260]
        timestamp = struct.pack(">Q", timestamp_int)
        leafFromHeader = uhdr[-259]
        leaf_digest = MMRUtils.leaf_digest(statement, timestamp)
        assert leafFromHeader == leaf_digest, "Leaf digest does not match header"
        inclusion_proof = uhdr[396][-1][0]
        mmr_index = inclusion_proof[1]
        proof_elements = inclusion_proof[2]
        return MMR.included_root(mmr_index, leaf_digest, proof_elements), cbor_cnf


def cose_sign1_from_buffer(buffer: bytes) -> cwt.COSEMessage:
    """
    Parse a COSE Sign1 message from a byte buffer, but
    WITHOUT verifying the signature.
    """
    cbor = cbor2.loads(buffer)
    assert cbor.tag == 18
    return cwt.COSEMessage(cwt.COSETypes.SIGN1, cbor.value)


def main():
    if len(sys.argv) != 2:
        print("Usage: verify <transparent_statement_path>")
        sys.exit(1)

    transparent_statement_path = sys.argv[1]

    with open(transparent_statement_path, "rb") as f:
        transparent_statement = f.read()

    ts = cose_sign1_from_buffer(transparent_statement)

    ts_wo_uhdr = cbor2.loads(transparent_statement)
    ts_wo_uhdr.value[1] = {}
    signed_statement = cbor2.dumps(ts_wo_uhdr)

    for receipt in ts.unprotected[394]:
        r = cose_sign1_from_buffer(receipt)
        cwt_claims = r.protected[15]
        if r.protected[395] == 2:
            print("Found receipt using profile: CCF (2)")
            service_key = DynamicTrustStore().get_key(receipt)
            ccf.cose.verify_receipt(
                receipt, service_key, hashlib.sha256(signed_statement).digest()
            )
        elif r.protected[395] == 3:
            print("Found receipt using profile: MMR (3)")
            root, cbor_cnf = MMRUtils.root_and_cnf(signed_statement, receipt)
            cose_key = cwt.COSEKey.from_bytes(cbor_cnf)
            verified_receipt = cwt.COSE(verify_kid=False)
            verified_receipt.decode_with_headers(
                receipt, cose_key, detached_payload=root
            )
        else:
            print(f"Unexpected profile in receipt: {r.protected[395]}")
            sys.exit(1)
        print(
            f"Verified receipt from issuer (1): {cwt_claims[1]}, subject (2): {cwt_claims[2]}"
        )

    print(f"Verified transparency of statement: {transparent_statement_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
