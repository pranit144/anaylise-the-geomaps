let polygonDraw = null;
let currentMap = null;

$(document).ready(function() {
    // Location search form submission
    $('#locationForm').on('submit', function(e) {
        e.preventDefault();
        
        $.ajax({
            url: '/search_location',
            method: 'POST',
            data: {
                location: $('#location').val()
            },
            success: function(response) {
                $('#mapContainer').removeClass('d-none');
                loadMap(response.lat, response.lon);
            },
            error: function(xhr) {
                alert('Error: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Location not found'));
            }
        });
    });

    // File upload form submission
    $('#uploadForm').on('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData();
        const fileInput = $('#imageUpload')[0];
        
        if (fileInput.files.length === 0) {
            alert('Please select a file to upload');
            return;
        }
        
        formData.append('file', fileInput.files[0]);
        
        $.ajax({
            url: '/upload',
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                window.location.href = `/analyze?image=${encodeURIComponent(response.filepath)}`;
            },
            error: function(xhr) {
                alert('Error uploading file: ' + (xhr.responseJSON ? xhr.responseJSON.error : 'Upload failed'));
            }
        });
    });

    // Screenshot capture button click
    $('#captureBtn').on('click', function() {
        if (!polygonDraw) {
            // Initialize polygon drawing if not already initialized
            const mapContainer = document.getElementById('map');
            mapContainer.classList.add('drawing-mode');
            polygonDraw = new PolygonDraw(mapContainer);
            polygonDraw.startDrawing();
            $(this).text('Complete Drawing (Press Enter)');
        } else if (polygonDraw.isDrawing) {
            const points = polygonDraw.completePolygon();
            const mapContainer = document.getElementById('map');
            mapContainer.classList.remove('drawing-mode');
            if (points.length >= 3) {
                captureWithPolygon(points);
            }
            $(this).text('Capture Screenshot');
        } else {
            const mapContainer = document.getElementById('map');
            mapContainer.classList.add('drawing-mode');
            polygonDraw.startDrawing();
            $(this).text('Complete Drawing (Press Enter)');
        }
    });

    // Analyze button click
    $('#analyzeBtn').on('click', function() {
        const screenshotPath = $('#capturedImage').attr('src');
        if (screenshotPath) {
            window.location.href = `/analyze?image=${encodeURIComponent(screenshotPath)}`;
        }
    });

    // Add keyboard event listener for Enter key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && polygonDraw && polygonDraw.isDrawing) {
            const points = polygonDraw.completePolygon();
            const mapContainer = document.getElementById('map');
            mapContainer.classList.remove('drawing-mode');
            if (points.length >= 3) {
                captureWithPolygon(points);
            }
            $('#captureBtn').text('Capture Screenshot');
        }
    });
});

function loadMap(lat, lon) {
    const mapDiv = document.getElementById('map');
    mapDiv.innerHTML = ''; // Clear any existing content
    
    // Create a new map instance
    currentMap = L.map('map', {
        center: [lat, lon],
        zoom: 20,
        maxZoom: 18,
        preferCanvas: true
    });
    
    // Add the satellite tile layer
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Esri',
        maxZoom: 20,
        tileSize: 256
    }).addTo(currentMap);

    // Wait for the map to load completely
    currentMap.whenReady(() => {
        currentMap.invalidateSize();
        currentMap.setView([lat, lon], 20);
    });
}

function captureWithPolygon(points) {
    const mapContainer = document.getElementById('map');
    
    // Get the current map state
    const center = currentMap.getCenter();
    const bounds = currentMap.getBounds();
    const zoom = currentMap.getZoom();
    
    const data = {
        width: mapContainer.offsetWidth,
        height: mapContainer.offsetHeight,
        polygon: points,
        mapState: {
            center: {
                lat: center.lat,
                lng: center.lng
            },
            bounds: {
                north: bounds.getNorth(),
                south: bounds.getSouth(),
                east: bounds.getEast(),
                west: bounds.getWest()
            },
            zoom: zoom
        }
    };

    // Log the map state for debugging
    console.log('Capturing map state:', data.mapState);

    fetch('/capture_screenshot', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            $('#screenshotGallery').removeClass('d-none');
            const imagePath = data.cutout_path || data.screenshot_path;
            const imageUrl = imagePath + '?t=' + new Date().getTime();
            $('#capturedImage').attr('src', imageUrl);
        } else {
            alert('Error capturing screenshot');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error capturing screenshot');
    });
}