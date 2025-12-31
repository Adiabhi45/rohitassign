# Reference Database Folder

This folder contains reference face images used for automatic matching when you upload a sketch.

## How to Use

1. **Add Reference Images**: Place face photos (PNG, JPG, JPEG, BMP, GIF) in this folder
2. **Upload Sketch**: Go to the "Search Database" feature in the app
3. **Automatic Matching**: The system will automatically compare your sketch with all images here
4. **View Results**: Get prediction scores for each reference image, sorted by similarity

## Supported Formats

- PNG (.png)
- JPEG (.jpg, .jpeg)
- BMP (.bmp)
- GIF (.gif)

## Tips for Best Results

- Use clear, front-facing face photos
- Good lighting improves matching accuracy
- Higher resolution images work better
- Organize files with descriptive names (e.g., "person_name.jpg")

## Example

```
reference_database/
├── john_doe.jpg
├── jane_smith.png
├── suspect_001.jpg
└── witness_photo.png
```

When you upload a sketch, the CLIP AI model will compare it against all these images and show you the best matches with prediction scores.
