console.log("particles.js loaded");
const canvas = document.getElementById("particleCanvas");
const ctx = canvas.getContext("2d");

let particles = [];
const PARTICLE_COUNT = 200;
const MAX_DISTANCE = 200;

// Resize canvas
function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
window.addEventListener("resize", resize);
resize();

const mouse = {
    x: null,
    y: null,
    radius: 120
};

window.addEventListener("mousemove", (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
});

window.addEventListener("mouseleave", () => {
    mouse.x = null;
    mouse.y = null;
});

let drift = {
    x: 0.015,
    y: 0.01
};

// Particle class
class Particle {
    constructor() {
    this.x = Math.random() * canvas.width;
    this.y = Math.random() * canvas.height;
    this.depth = Math.random();

    this.vx = (Math.random() * 2 - this.depth) * 0.1;
    this.vy = (Math.random() * 2 - this.depth) * 0.1;

    this.radius = 2;
    }

    update() {
        this.x += this.vx + drift.x * this.depth;
        this.y += this.vy + drift.y * this.depth;

        // bounce off walls
        if (this.x <= 0 || this.x >= canvas.width) this.vx *= -1;
        if (this.y <= 0 || this.y >= canvas.height) this.vy *= -1;

        if (mouse.x && mouse.y) {
            const dx = mouse.x - this.x;
            const dy = mouse.y - this.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < mouse.radius) {
                const force = (mouse.radius - distance) / mouse.radius;
                const strength = this.depth * 0.08;

                this.x -= dx * force * strength;
                this.y -= dy * force * strength;
            }
        }
    }

    draw() {
        ctx.fillStyle = `hsla(${260 + this.depth * 60}, 100%, 75%, 1)`;
        ctx.globalAlpha = 0.3 + this.depth * 0.7;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius + this.depth * 1.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
    }
}
// Create particles
for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle());
}

function nebulaColor(distance, maxDistance) {
    const t = Math.min(distance / maxDistance, 1);
    const hue = 320 - t * 110;
    const alpha = 1 - t;
    return `hsla(${hue}, 100%, 70%, ${alpha})`;
}

// Draw connections
function connectParticles() {
    for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < MAX_DISTANCE) {
                ctx.strokeStyle = nebulaColor(distance, MAX_DISTANCE);
                ctx.lineWidth = (distance / MAX_DISTANCE) * 2;
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.stroke();
            }
        }
    }
}


// Animation loop
function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    particles.forEach(p => {
    p.update();
    p.draw();
    });

    connectParticles();
    requestAnimationFrame(animate);
}

animate();