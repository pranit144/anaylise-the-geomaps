# Map Analysis and Image Segmentation Tool

## Overview
This project provides a Flask-based web application for:
- Visualizing and analyzing maps.
- Capturing screenshots of specific map regions.
- Performing advanced image segmentation using k-means clustering and color analysis.

The application includes multiple functionalities such as location search, polygon masking, and enhanced segmentation for features like vegetation, water, buildings, and terrain.

---

## Features
### 1. **Search Location and Map Visualization**
- Use the `search_location` endpoint to find a location by name.
- Render maps using the Esri World Imagery tiles for high-resolution satellite imagery.

### 2. **Capture Screenshots**
- Capture screenshots of rendered maps using Selenium WebDriver.
- Polygon masking for region-specific screenshots.

### 3. **Advanced Image Segmentation**
- Segment uploaded images using k-means clustering.
- Identify features such as vegetation, water, buildings, and terrain using HSV and LAB color spaces.
- Includes additional texture and gradient-based analysis for more accurate classification.

### 4. **Upload and Analyze Images**
- Upload images in formats like PNG, JPEG, or TIFF for analysis.
- Generate segmented images and masks for identified features.

---

## Installation
### Prerequisites
Ensure the following are installed:
- Python 3.7+
- pip (Python package manager)
- Google Chrome and ChromeDriver

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/<your-repo-name>/map-analysis-segmentation.git
   cd map-analysis-segmentation
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up ChromeDriver:
   - Download ChromeDriver that matches your Chrome version from [here](https://chromedriver.chromium.org/downloads).
   - Ensure `chromedriver` is in your PATH or specify its location in `setup_webdriver`.
4. Run the application:
   ```bash
   python app.py
   ```

---

## API Endpoints

### `GET /`
**Description**: Renders the home page.

### `POST /search_location`
**Description**: Searches for a location and returns latitude, longitude, and address.
**Parameters**:
- `location`: Name or address of the location.

### `POST /capture_screenshot`
**Description**: Captures a map screenshot, optionally applying a polygon mask.
**Parameters**:
- `width`: Width of the screenshot.
- `height`: Height of the screenshot.
- `polygon`: Polygon points for masking (optional).
- `mapState`: Map center, zoom, and bounds (optional).

### `GET /analyze`
**Description**: Analyzes an image and performs segmentation.
**Query Parameters**:
- `image`: Path to the image for analysis.

### `POST /upload`
**Description**: Uploads an image for further processing.
**Form Data**:
- `file`: Image file.

---

## Project Structure
```
map-analysis-segmentation/
├── app.py               # Main application file
├── requirements.txt     # Python dependencies
├── templates/           # HTML templates
│   ├── index.html       # Home page
│   └── analysis.html    # Results page
├── static/              # Static files (JS, CSS, images)
│   ├── screenshots/     # Map screenshots
│   ├── uploads/         # Uploaded images
│   └── masks/           # Segmentation masks
└── README.md            # Project documentation
```

---

## Usage
1. **Start the Server**:
   Run the application using:
   ```bash
   python app.py
   ```
2. **Access the Web Interface**:
   Open [http://localhost:5000](http://localhost:5000) in your browser.
3. **Search and Capture**:
   - Search for a location.
   - Adjust the map and capture a screenshot.
4. **Upload and Analyze Images**:
   - Upload an image for analysis.
   - View segmented results and feature masks.

---

## Contributions
Feel free to fork the repository, make improvements, and submit a pull request. Suggestions and feedback are welcome!

---

## License
This project is licensed under the MIT License. See the LICENSE file for details.
