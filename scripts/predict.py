from ultralytics import YOLO

# Load trained model
model = YOLO("models/best.pt")

# Predict on test image
results = model.predict(
    source="test_images",
    save=True,
    conf=0.25
)

print("Prediction Completed!")