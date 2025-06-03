#!/usr/bin/env python3
import os
import sys
import hashlib
import json


def create_intoto_json(directory: str) -> dict:
    """Create an in-toto v1 JSON file with file paths and their SHA-256 hashes."""
    in_toto_data = {
        "subject": [],
        "predicateType": "https://model_signing/Digests/v0.1",
        "predicate": {"unused": "Unused, just passed due to API requirements"},
    }

    for root, _, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            real_path = os.path.realpath(file_path)
            with open(real_path, "rb") as f:
                file_hash = hashlib.file_digest(f, "sha256").hexdigest()
            relative_path = os.path.relpath(file_path, directory)
            in_toto_data["subject"].append(
                {
                    "name": relative_path,
                    "digest": {"sha256": file_hash},
                    "annotations": {"actual_hash_algorithm": "file-sha256"},
                }
            )

    return in_toto_data


def main():
    """
    A CLI script that takes a directory path as an argument,
    lists all the files in that directory,
    computes their SHA-256 hashes,
    and creates a JSON document in the in-toto v1 format with
    the file paths and their corresponding hashes,
    which it prints to standard output.
    """
    if len(sys.argv) != 2:
        print("Usage: intoto <directory_path>")
        print(main.__doc__)
        sys.exit(1)

    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory.")
        sys.exit(1)

    in_toto_json = create_intoto_json(directory)
    print(json.dumps(in_toto_json, indent=2))


if __name__ == "__main__":
    main()
