class PolygonDraw {
    constructor(container) {
        this.container = container;
        this.points = [];
        this.isDrawing = false;
        this.svg = null;
        this.polygon = null;
        this.setupSVG();
    }

    setupSVG() {
        // Create SVG overlay
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.style.position = 'absolute';
        this.svg.style.top = '0';
        this.svg.style.left = '0';
        this.svg.style.width = '100%';
        this.svg.style.height = '100%';
        this.svg.style.pointerEvents = 'all';
        this.svg.style.zIndex = '1000';
        
        // Create polygon element
        this.polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        this.polygon.setAttribute('fill', 'rgba(255, 0, 0, 0.2)');
        this.polygon.setAttribute('stroke', 'red');
        this.polygon.setAttribute('stroke-width', '2');
        this.svg.appendChild(this.polygon);
        
        // Add SVG to container
        this.container.appendChild(this.svg);
    }

    startDrawing() {
        this.isDrawing = true;
        this.points = [];
        this.updatePolygon();
        
        // Add click listener to container
        this.container.style.cursor = 'crosshair';
        this.clickHandler = this.handleClick.bind(this);
        this.moveHandler = this.handleMouseMove.bind(this);
        
        // Find and disable the iframe
        const mapFrame = this.container.querySelector('iframe');
        if (mapFrame) {
            mapFrame.style.pointerEvents = 'none';
        }
        
        this.svg.addEventListener('click', this.clickHandler);
        this.svg.addEventListener('mousemove', this.moveHandler);
    }

    handleClick(event) {
        event.preventDefault();
        event.stopPropagation();
        
        const rect = this.container.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        this.points.push({ x, y });
        this.updatePolygon();
    }

    handleMouseMove(event) {
        if (this.points.length > 0) {
            event.preventDefault();
            event.stopPropagation();
            
            const rect = this.container.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            this.updatePolygon([...this.points, { x, y }]);
        }
    }

    updatePolygon(points = this.points) {
        if (points.length > 0) {
            const pointsString = points.map(p => `${p.x},${p.y}`).join(' ');
            this.polygon.setAttribute('points', pointsString);
        } else {
            this.polygon.setAttribute('points', '');
        }
    }

    completePolygon() {
        this.isDrawing = false;
        this.container.style.cursor = 'default';
        this.svg.removeEventListener('click', this.clickHandler);
        this.svg.removeEventListener('mousemove', this.moveHandler);
        
        // Re-enable the iframe
        const mapFrame = this.container.querySelector('iframe');
        if (mapFrame) {
            mapFrame.style.pointerEvents = 'auto';
        }
        
        const points = [...this.points];
        this.points = [];
        this.updatePolygon();
        return points;
    }

    cleanup() {
        if (this.svg && this.svg.parentNode) {
            this.svg.parentNode.removeChild(this.svg);
        }
    }
} 