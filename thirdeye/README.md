# ThirdEye---forensic-face-sketch-construction-and-recognition
AI-powered forensic face sketch construction and recognition system using Python and Deep Learning
# Face Sketch Builder 😊

A Flask web application for constructing face sketches by dragging and dropping PNG facial feature assets.

## Features

- 🎯 **Drag & Drop Interface**: Intuitive drag-and-drop functionality for facial features
- 🖼️ **Canvas Workspace**: Large canvas area for face construction
- 📁 **Organized Assets**: Facial features organized into categories (face shapes, hair, eyes, noses, mouths, eyebrows, ears, facial hair, accessories)
- 💾 **Save Functionality**: Save your face sketch data as JSON
- 🗑️ **Easy Management**: Clear canvas, reposition features, and remove parts with double-click
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Project Structure

```
project/
├── app.py                  # Flask backend server
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── output/                # Saved face sketches directory
├── static/
│   ├── assets/           # PNG assets organized by facial feature
│   │   ├── heads/        # Face shapes (oval, round, square, etc.)
│   │   ├── hair/         # Hairstyles
│   │   ├── eyes/         # Eye variations
│   │   ├── noses/        # Nose shapes
│   │   ├── mouths/       # Mouth expressions
│   │   ├── eyebrows/     # Eyebrow styles
│   │   ├── ears/         # Ear shapes
│   │   ├── facialhair/   # Beards, mustaches
│   │   └── accessories/  # Glasses, earrings, etc.
│   ├── css/
│   │   └── style.css     # Application styles
│   └── js/
│       └── app.js        # Frontend JavaScript
└── templates/
    └── index.html        # Main HTML template
```

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your PNG assets:**
   - Place PNG files in the appropriate folders under `static/assets/`
   - Categories: heads (face shapes), hair, eyes, noses, mouths, eyebrows, ears, facialhair, accessories

## Usage

1. **Start the Flask server:**
   ```bash
   python app.py
   ```

2. **Open your browser:**
   Navigate to `http://localhost:5000`

3. **Create your face sketch:**
   - Drag facial features from the left panel to the canvas
   - Start with a face shape, then add eyes, nose, mouth, etc.
   - Click and drag placed features to reposition them
   - Double-click a feature to remove it
   - Use the control buttons to clear, export, or save your face sketch

## Controls

- **Clear**: Remove all facial features from the canvas
- **Export PNG**: Export your face sketch as a PNG image (requires html2canvas)
- **Save Sketch**: Save face sketch data as JSON to the output folder

## Adding Facial Feature Assets

To add your own PNG assets:

1. Create PNG images with transparent backgrounds
2. Place them in the appropriate category folder:
   - `static/assets/heads/` - Face shapes (oval, round, square, heart-shaped, etc.)
   - `static/assets/hair/` - Various hairstyles (long, short, curly, straight, etc.)
   - `static/assets/eyes/` - Different eye styles and expressions
   - `static/assets/noses/` - Various nose shapes and sizes
   - `static/assets/mouths/` - Mouth expressions (smile, frown, neutral, etc.)
   - `static/assets/eyebrows/` - Eyebrow styles (thick, thin, arched, etc.)
   - `static/assets/ears/` - Ear shapes and styles
   - `static/assets/facialhair/` - Beards, mustaches, goatees, etc.
   - `static/assets/accessories/` - Glasses, earrings, hats, etc.

## Development

- **Backend**: Python Flask serving the web application
- **Frontend**: Vanilla JavaScript for interactions
- **Styling**: Modern CSS with responsive design

## Tips

- Start with a face shape as the base
- Add eyes and position them symmetrically
- Layer eyebrows above the eyes
- Place the nose in the center
- Add the mouth below the nose
- Layer hair on top of the face shape
- Add facial hair and accessories last
- Use double-click to quickly remove unwanted features
- Save your work frequently using the Save Sketch button

## License

MIT License - Feel free to use and modify for your projects!


