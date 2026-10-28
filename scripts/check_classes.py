import os

label_dir = r"C:\Users\rahul\OneDrive\Documents\Desktop\AI Crime Scene Detection\Datasets\crime scene\train\labels"

classes = set()

for file in os.listdir(label_dir):
    if file.endswith(".txt"):
        with open(os.path.join(label_dir, file), "r") as f:
            for line in f:
                if line.strip():
                    classes.add(int(line.split()[0]))

print("Classes found:", sorted(classes))