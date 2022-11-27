import json
import sys
from os import path
import os
from jsonschema import validate, exceptions

TYPES = {
    "Credit": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "role": {"type": "string"},
        },
        "required": ["name", "role"],
        "additionalProperties": False,
    },
    "Link": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "url": {"type": "string"},
        },
        "required": ["title", "url"],
        "additionalProperties": False,
    },
    "TitleStatus": {
        "type": "string",
        "enum": ["upcoming", "ongoing", "completed", "cancelled"],
    },
    "Slug": {
        "type": "string",
        "pattern": "^[a-z0-9]+(?:-[a-z0-9]+)*$",
        "errors": {
            "pattern": lambda e: "'"
            + e.instance
            + "' is a not a properly formatted slug. Only use words formed of lowercase characters and digits, separated by dashes (i.e: 'this-is-a-slug')"
        },
    },
    "non-empty-string": {
        "type": "string",
        "pattern": "(?!^[/s]*$)",
        "errors": {"pattern": lambda _: "is an empty string"},
    },
}

SPECS = {
    "library": {
        "index": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "enum": ["2.0"]},
                "titles": {"type": "array", "items": TYPES["Slug"]},
            },
            "required": ["version", "titles"],
            "additionalProperties": False,
        },
        "expectedFiles": ["index.json"],
    },
    "title": {
        "index": {
            "type": "object",
            "properties": {
                "version": {"type": "string", "enum": ["2.0"]},
                "pretitle": {"type": "string", "default": ""},
                "title": TYPES["non-empty-string"],
                "subtitle": {"type": "string", "default": ""},
                "volumes": {
                    "type": "array",
                    "items": TYPES["Slug"],
                },
                "status": TYPES["TitleStatus"],
                "synopsis": {"type": "string"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "serialization": {"type": "string", "default": ""},
                "credits": {"type": "array", "items": TYPES["Credit"]},
                "links": {"type": "array", "items": TYPES["Link"]},
            },
            "required": ["version", "volumes"],
            "additionalProperties": False,
        },
        "expectedFiles": ["index.json", "thumbnail.jpg"],
    },
}


def errorRepport(checkCode, errorPath, message):
    print("[FAILED Check " + str(checkCode) + "] [" + " -> ".join(errorPath) + "] " + message)
    return False


def formatList(list):
    if len(list) > 1:
        lastElem = list.pop()
        return "'" + "', '".join(list) + "'" + ", and '" + lastElem + "'"
    return "'" + list[0] + "'"


def isJsonCompliant(checkCode, errorPath, data, specs):
    try:
        validate(data, specs)
        return True
    except exceptions.ValidationError as error:
        customMessage = None
        if "errors" in error.schema and error.validator in error.schema["errors"]:
            customMessage = error.schema["errors"][error.validator](error)
        validationErrorPath = [str(e) for e in list(error.path)]
        errorRepport(
            checkCode,
            errorPath + validationErrorPath,
            customMessage if customMessage != None else error.message,
        )
        return False


def isTitleCompliant(checkCode, libraryPath, errorPath, titleSlug):
    titlePath = libraryPath + titleSlug + "/"
    errorPath += [titleSlug]

    # :----------------------------------: CHECK 1 :----------------------------------:

    if not path.exists(titlePath):
        return errorRepport(
            checkCode + 0.1,
            errorPath,
            "The given library (" + titlePath + ") doesn't exists",
        )

    # :----------------------------------: CHECK 2 :----------------------------------:

    titleIndexPath = titlePath + "index.json"
    if not path.isfile(titleIndexPath):
        return errorRepport(checkCode + 0.2, errorPath + ["index.json"], "is missing")

    # :----------------------------------: CHECK 3 :----------------------------------:

    with open(titleIndexPath) as f:
        try:
            titleIndexData = json.load(f)
        except json.JSONDecodeError:
            return errorRepport(
                checkCode + 0.3,
                errorPath + ["index.json"],
                "is not a valid JSON file",
            )

    # :----------------------------------: CHECK 4 :----------------------------------:

    if not isJsonCompliant(
        checkCode + 0.4, errorPath + ["index.json"], titleIndexData, SPECS["title"]["index"]
    ):
        return False

    # :----------------------------------: CHECK 5 :----------------------------------:

    allSubfolders = [e for e in os.listdir(titlePath) if path.isdir(titlePath + e)]
    unrecognizedSubfolders = [e for e in allSubfolders if e not in titleIndexData["volumes"]]

    if unrecognizedSubfolders != []:
        return errorRepport(
            5,
            errorPath,
            "Other folders than the ones listed as 'volumes' in 'index.json' are not allowed ("
            + formatList(unrecognizedSubfolders)
            + " was unexpected)",
        )

    # :----------------------------------: CHECK 6 :----------------------------------:

    allSubfiles = [e for e in os.listdir(titlePath) if path.isfile(titlePath + e)]
    unrecognizedFiles = [e for e in allSubfiles if e not in SPECS["title"]["expectedFiles"]]

    if unrecognizedFiles != []:
        return errorRepport(
            6,
            errorPath,
            "Additional files are not allowed ("
            + formatList(unrecognizedFiles)
            + " was unexpected)",
        )

    return True


def isLibraryCompliant(libraryPath):
    if not libraryPath.endswith("/"):
        libraryPath += "/"

    errorPath = ["Library"]

    # :----------------------------------: CHECK 1 :----------------------------------:

    if not path.exists(libraryPath):
        return errorRepport(
            1,
            errorPath,
            "The given library (" + libraryPath + ") doesn't exists",
        )

    # :----------------------------------: CHECK 2 :----------------------------------:

    libraryIndex = libraryPath + "index.json"
    if not path.isfile(libraryIndex):
        return errorRepport(2, errorPath + ["index.json"], "is missing")

    # :----------------------------------: CHECK 3 :----------------------------------:

    with open(libraryIndex) as f:
        try:
            libraryIndexData = json.load(f)
        except json.JSONDecodeError:
            return errorRepport(3, errorPath + ["index.json"], "is not a valid JSON file")

    # :----------------------------------: CHECK 4 :----------------------------------:

    if not isJsonCompliant(
        4, errorPath + ["index.json"], libraryIndexData, SPECS["library"]["index"]
    ):
        return False

    # :----------------------------------: CHECK 5 :----------------------------------:

    allSubfolders = [e for e in os.listdir(libraryPath) if path.isdir(libraryPath + e)]
    unrecognizedSubfolders = [e for e in allSubfolders if e not in libraryIndexData["titles"]]

    if unrecognizedSubfolders != []:
        return errorRepport(
            5,
            errorPath,
            "Other folders than the ones listed as 'titles' in 'index.json' are not allowed ("
            + formatList(unrecognizedSubfolders)
            + " was unexpected)",
        )

    # :----------------------------------: CHECK 6 :----------------------------------:

    allSubfiles = [e for e in os.listdir(libraryPath) if path.isfile(libraryPath + e)]
    unrecognizedFiles = [e for e in allSubfiles if e not in SPECS["library"]["expectedFiles"]]

    if unrecognizedFiles != []:
        return errorRepport(
            6,
            errorPath,
            "Additional files are not allowed ("
            + formatList(unrecognizedFiles)
            + " was unexpected)",
        )

    # :----------------------------------: CHECK 7 :----------------------------------:

    for expectedSubfolder in libraryIndexData["titles"]:
        if not isTitleCompliant(7, libraryPath, errorPath, expectedSubfolder):
            return False

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Please provide the path to your Okuma-Library as a argument when running this python file (i.e: python3 prog.py ./library/)."
        )
        exit()

    isLibraryCompliant(sys.argv[1])
