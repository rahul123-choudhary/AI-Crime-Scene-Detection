import os
from collections import Counter

# Project folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Training labels folder
LABEL_DIR = os.path.join(
    BASE_DIR,
    "Datasets",
    "unified",
    "train",
    "labels"
)

CLASS_NAMES = [
    "Blood",
    "Finger-print",
    "Glass",
    "Hammer",
    "Human-body",
    "Human-hair",
    "Human-hand",
    "Rope",
    "Shoe-print",
    "Shotgun",
    "Victim",
    "Fire",
    "Grenade",
    "Rocket",
    "Rifle",
    "Blunt-Object",
    "Knife",
    "Pistol",
    "Shotgun-Weapon",
    "Submachine-Gun"
]

counter = Counter()
invalid_labels = []
total_files = 0

print("Checking labels in:")
print(LABEL_DIR)
print()

if not os.path.exists(LABEL_DIR):
    print("ERROR: Labels folder does not exist!")
    print(LABEL_DIR)
    exit()

for filename in os.listdir(LABEL_DIR):

    if not filename.lower().endswith(".txt"):
        continue

    total_files += 1

    filepath = os.path.join(LABEL_DIR, filename)

    try:
        with open(filepath, "r") as f:

            for line_number, line in enumerate(f, start=1):

                values = line.strip().split()

                if not values:
                    continue

                class_id = int(values[0])

                counter[class_id] += 1

                if class_id < 0 or class_id >= len(CLASS_NAMES):
                    invalid_labels.append(
                        (filename, line_number, class_id)
                    )

    except Exception as e:
        print("ERROR reading:", filename)
        print(e)

print()
print("=" * 50)
print("LABEL CHECK COMPLETE")
print("=" * 50)

print()
print("Total label files:", total_files)

print()
print("CLASS DISTRIBUTION")
print("-" * 50)

for class_id in range(len(CLASS_NAMES)):

    print(
        f"{class_id:2d} -> "
        f"{CLASS_NAMES[class_id]:20s} : "
        f"{counter[class_id]}"
    )

print()
print("=" * 50)
print("INVALID CLASS IDs")
print("=" * 50)

if invalid_labels:

    print("Invalid labels found:", len(invalid_labels))

    for item in invalid_labels[:20]:
        print(item)

else:

    print("No invalid class IDs found.")

print()
print("Finished.")