from flask import Flask, render_template, request, jsonify
from geopy.geocoders import Nominatim
import folium
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import cv2
import numpy as np
from PIL import Image
import logging
import uuid
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw

app = Flask(__name__)

# Configure screenshot directory
SCREENSHOT_DIR = os.path.join(app.static_folder, 'screenshots')
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tif', 'tiff'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def kmeans_segmentation(image, n_clusters=8):
    """
    Enhanced segmentation using multiple color spaces and improved filters
    """
    try:
        # Convert PIL Image to CV2 format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Create mask for non-black pixels with more lenient threshold
        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
        non_black_mask = cv2.inRange(hsv, np.array([0, 0, 15]), np.array([180, 255, 255]))
        
        # Enhanced color ranges for better classification
        color_ranges = {
            'vegetation': {
                'hsv': {
                    'lower': np.array([30, 40, 40]),
                    'upper': np.array([90, 255, 255])
                },
                'lab': {
                    'lower': np.array([0, 0, 125]),
                    'upper': np.array([255, 120, 255])
                },
                'color': (0, 255, 0)  # Green
            },
            'water': {
                'hsv': {
                    'lower': np.array([85, 30, 30]),
                    'upper': np.array([140, 255, 255])
                },
                'lab': {
                    'lower': np.array([0, 115, 0]),
                    'upper': np.array([255, 255, 130])
                },
                'color': (255, 0, 0)  # Blue
            },
            'building': {
                'hsv': {
                    'lower': np.array([0, 0, 100]),
                    'upper': np.array([180, 50, 255])
                },
                'lab': {
                    'lower': np.array([50, 115, 115]),
                    'upper': np.array([200, 140, 140])
                },
                'color': (128, 128, 128)  # Gray
            },
            'terrain': {
                'hsv': {
                    'lower': np.array([0, 20, 40]),  # Broader range for terrain
                    'upper': np.array([30, 255, 220])
                },
                'lab': {
                    'lower': np.array([20, 110, 110]),  # Adjusted LAB range
                    'upper': np.array([200, 140, 140])
                },
                'color': (139, 69, 19)  # Brown
            }
        }
        
        # Get only non-black pixels for clustering
        valid_pixels = cv_image[non_black_mask > 0].reshape(-1, 3).astype(np.float32)
        
        if len(valid_pixels) == 0:
            raise ValueError("No valid pixels found after filtering")
        
        # Perform k-means clustering on non-black pixels
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(valid_pixels, n_clusters, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert centers to uint8
        centers = np.uint8(centers)
        
        # Create segmented image
        height, width = cv_image.shape[:2]
        segmented = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Create mask for each cluster
        valid_indices = np.where(non_black_mask > 0)
        segmented[valid_indices] = centers[labels.flatten()]
        
        results = {}
        masks = {}
        total_valid_pixels = np.count_nonzero(non_black_mask)
        
        # Initialize masks for each feature
        for feature in color_ranges:
            masks[feature] = np.zeros((height, width, 3), dtype=np.uint8)
        masks['other'] = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Analyze original image colors for each cluster
        for cluster_id in range(n_clusters):
            cluster_mask = np.zeros((height, width), dtype=np.uint8)
            cluster_mask[valid_indices] = (labels.flatten() == cluster_id).astype(np.uint8)
            
            # Get original colors for this cluster
            cluster_pixels = cv_image[cluster_mask > 0]
            if len(cluster_pixels) == 0:
                continue
            
            # Convert to both HSV and LAB color spaces
            cluster_hsv = cv2.cvtColor(cluster_pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV)
            cluster_lab = cv2.cvtColor(cluster_pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2LAB)
            
            # Count pixels matching each feature in both color spaces
            feature_counts = {}
            for feature, ranges in color_ranges.items():
                hsv_mask = cv2.inRange(cluster_hsv, ranges['hsv']['lower'], ranges['hsv']['upper'])
                lab_mask = cv2.inRange(cluster_lab, ranges['lab']['lower'], ranges['lab']['upper'])
                
                # Combine results from both color spaces
                combined_mask = cv2.bitwise_or(hsv_mask, lab_mask)
                feature_counts[feature] = np.count_nonzero(combined_mask)
                
                # Additional texture analysis for building detection
                if feature == 'building':
                    gray = cv2.cvtColor(cluster_pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2GRAY)
                    local_std = np.std(gray)
                    
                    # Calculate gradient magnitude using Sobel
                    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
                    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
                    gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
                    
                    # Adjust feature count based on texture analysis
                    if local_std < 30 and np.mean(gradient_magnitude) > 10:
                        feature_counts[feature] *= 1.5  # Boost building detection score
                    elif local_std > 50:
                        feature_counts[feature] *= 0.5  # Reduce building detection score
                
                # Additional texture and color analysis for terrain/ground
                elif feature == 'terrain':
                    # Calculate texture features
                    gray = cv2.cvtColor(cluster_pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2GRAY)
                    local_std = np.std(gray)
                    
                    # Calculate GLCM features
                    glcm = np.zeros((256, 256), dtype=np.uint8)
                    for i in range(len(gray)-1):
                        glcm[gray[i], gray[i+1]] += 1
                    glcm_sum = np.sum(glcm)
                    if glcm_sum > 0:
                        glcm = glcm / glcm_sum
                    
                    # Calculate homogeneity
                    homogeneity = np.sum(glcm / (1 + np.abs(np.arange(256)[:, None] - np.arange(256))))
                    
                    # Color analysis
                    avg_saturation = np.mean(cluster_hsv[:, :, 1])
                    avg_value = np.mean(cluster_hsv[:, :, 2])
                    
                    # Adjust feature count based on multiple criteria
                    if (20 < local_std < 60 and homogeneity > 0.5 
                        and avg_saturation < 100 and 40 < avg_value < 200):
                        feature_counts[feature] *= 1.8  # Boost terrain detection
                    elif local_std > 80 or avg_saturation > 150:
                        feature_counts[feature] *= 0.4  # Reduce score
                    
                    # Check for grass-like patterns
                    if (30 <= np.mean(cluster_hsv[:, :, 0]) <= 90 
                        and avg_saturation > 30 and local_std < 40):
                        feature_counts['vegetation'] = feature_counts.get('vegetation', 0) + feature_counts[feature]
                        feature_counts[feature] *= 0.5
            
            # Assign cluster to feature with highest pixel count
            if any(feature_counts.values()):
                dominant_feature = max(feature_counts.items(), key=lambda x: x[1])[0]
                if dominant_feature not in results:
                    results[dominant_feature] = 0
                
                pixel_count = np.count_nonzero(cluster_mask)
                percentage = (pixel_count / total_valid_pixels) * 100
                results[dominant_feature] += percentage
                
                # Update feature mask
                masks[dominant_feature][cluster_mask > 0] = color_ranges[dominant_feature]['color']
            else:
                # Unclassified pixels
                if 'other' not in results:
                    results['other'] = 0
                pixel_count = np.count_nonzero(cluster_mask)
                percentage = (pixel_count / total_valid_pixels) * 100
                results['other'] += percentage
                masks['other'][cluster_mask > 0] = (200, 200, 200)  # Light gray
        
        # Filter results and save masks
        filtered_results = {}
        filtered_masks = {}
        
        for feature, percentage in results.items():
            if percentage > 0.5:  # Only include if more than 0.5%
                filtered_results[feature] = round(percentage, 1)
                
                # Save mask
                mask_filename = f'mask_{feature}_{uuid.uuid4().hex[:8]}.png'
                mask_path = os.path.join(app.static_folder, 'masks', mask_filename)
                cv2.imwrite(mask_path, masks[feature])
                filtered_masks[feature] = f'/static/masks/{mask_filename}'
        
        # Save segmented image
        segmented_filename = f'segmented_{uuid.uuid4().hex[:8]}.png'
        segmented_path = os.path.join(app.static_folder, 'masks', segmented_filename)
        cv2.imwrite(segmented_path, segmented)
        filtered_masks['segmented'] = f'/static/masks/{segmented_filename}'
        
        return {
            'percentages': dict(sorted(filtered_results.items(), key=lambda x: x[1], reverse=True)),
            'masks': filtered_masks
        }
        
    except Exception as e:
        logging.error(f"Segmentation error: {str(e)}")
        raise

def setup_webdriver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=chrome_options)

def create_polygon_mask(image_size, points):
    """Create a mask image from polygon points"""
    mask = Image.new('L', image_size, 0)
    draw = ImageDraw.Draw(mask)
    polygon_points = [(p['x'], p['y']) for p in points]
    draw.polygon(polygon_points, fill=255)
    return mask

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search_location', methods=['POST'])
def search_location():
    try:
        location = request.form.get('location')
        
        # Geocode the location
        geolocator = Nominatim(user_agent="map_screenshot_app")
        location_data = geolocator.geocode(location)
        
        if not location_data:
            return jsonify({'error': 'Location not found'}), 404
        
        # Create a Folium map with controls disabled
        m = folium.Map(
            location=[location_data.latitude, location_data.longitude],
            zoom_start=20,
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            # zoom_control=False,  # Disable zoom control
            # dragging=False,      # Disable dragging
            # scrollWheelZoom=False  # Disable scroll wheel zoom
        )
        
        # Save the map
        map_path = os.path.join(app.static_folder, 'temp_map.html')
        m.save(map_path)
        
        return jsonify({
            'lat': location_data.latitude,
            'lon': location_data.longitude,
            'address': location_data.address
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/capture_screenshot', methods=['POST'])
def capture_screenshot():
    try:
        data = request.get_json()
        width = data.get('width', 600)
        height = data.get('height', 400)
        polygon_points = data.get('polygon', None)
        map_state = data.get('mapState', None)
        
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        
        # Create a new map with the current state
        if map_state:
            center = map_state['center']
            zoom = map_state['zoom']
            
            m = folium.Map(
                location=[center['lat'], center['lng']],
                zoom_start=zoom,
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                width=width,
                height=height
            )
            
            # Set the bounds
            bounds = map_state['bounds']
            m.fit_bounds([[bounds['south'], bounds['west']], 
                         [bounds['north'], bounds['east']]])
            
            # Add custom JavaScript to ensure correct zoom
            m.get_root().html.add_child(folium.Element(f"""
                <script>
                    document.addEventListener('DOMContentLoaded', function() {{
                        setTimeout(function() {{
                            var map = document.querySelector('#map');
                            if (map && map._leaflet_map) {{
                                map._leaflet_map.setView([{center['lat']}, {center['lng']}], {zoom});
                            }}
                        }}, 1000);
                    }});
                </script>
            """))
            
            # Save the map
            map_path = os.path.join(app.static_folder, 'temp_map.html')
            m.save(map_path)
        
        # Increase wait time to ensure map loads completely
        time.sleep(1)
        
        driver = setup_webdriver()
        try:
            driver.set_window_size(width + 50, height + 50)  # Add padding to prevent scrollbars
            map_url = f"http://localhost:{app.config['PORT']}/static/temp_map.html"
            driver.get(map_url)
            
            # Wait for map to load and settle
            time.sleep(3)
            
            # Take screenshot
            driver.save_screenshot(filepath)
            
            if polygon_points and len(polygon_points) >= 3:
                # Create polygon cutout
                img = Image.open(filepath)
                mask = create_polygon_mask(img.size, polygon_points)
                
                # Create cutout image
                cutout = Image.new('RGBA', img.size, (0, 0, 0, 0))
                cutout.paste(img, mask=mask)
                
                # Save cutout
                cutout_filename = f"cutout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                cutout_filepath = os.path.join(SCREENSHOT_DIR, cutout_filename)
                cutout.save(cutout_filepath)
                
                return jsonify({
                    'success': True,
                    'screenshot_path': f'/static/screenshots/{filename}',
                    'cutout_path': f'/static/screenshots/{cutout_filename}'
                })
            
            return jsonify({
                'success': True,
                'screenshot_path': f'/static/screenshots/{filename}'
            })
            
        finally:
            driver.quit()
            
    except Exception as e:
        logging.error(f"Screenshot error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/analyze')
def analyze():
    try:
        image_path = request.args.get('image')
        if not image_path:
            return "No image provided", 400
            
        # Create masks directory if it doesn't exist
        masks_dir = os.path.join(app.static_folder, 'masks')
        os.makedirs(masks_dir, exist_ok=True)
        
        # Clean up old mask files
        for f in os.listdir(masks_dir):
            if f.startswith(('mask_', 'segmented_')):
                try:
                    os.remove(os.path.join(masks_dir, f))
                except:
                    pass
        
        # Clean up the image path
        image_path = image_path.split('?')[0]
        image_path = image_path.replace('/static/', '')
        full_path = os.path.join(app.static_folder, image_path)
        
        if not os.path.exists(full_path):
            return f"Image file not found: {image_path}", 404
        
        # Load and process image
        image = Image.open(full_path)
        
        # Ensure image is in RGB mode
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        # Perform k-means segmentation
        segmentation_results = kmeans_segmentation(image)
        
        return render_template('analysis.html', 
                             image_path=request.args.get('image').split('?')[0],
                             results=segmentation_results['percentages'],
                             masks=segmentation_results['masks'])
                             
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        return f"Error processing image: {str(e)}", 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        return jsonify({
            'success': True,
            'filepath': f'/static/uploads/{unique_filename}'
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    port = 5000
    app.config['PORT'] = port
    app.run(debug=True, port=port) 