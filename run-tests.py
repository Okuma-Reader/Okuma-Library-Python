from prog import isLibraryCompliant
import os

os.system("cls")

testFolders = ["tests/fail_1"] + ["tests/" + e for e in os.listdir("tests")]

for index, path in enumerate(testFolders):
    expectedResult = "success" in path
    print("")
    print("[" + str(index + 1) + "/" + str(len(testFolders)) + "] " + path)
    result = isLibraryCompliant(path)
    print("✔️" if expectedResult == result else "❌")

print()
