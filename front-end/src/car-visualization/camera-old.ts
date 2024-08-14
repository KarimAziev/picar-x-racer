import * as THREE from 'three';
import './camera.scss';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

export class CameraVisualization {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private pan: number = 0;
  private tilt: number = 0; // Initial tilt
  private servoAngle: number = 0; // Initial servo angle
  private cameraObject: THREE.Object3D;
  private wheels: THREE.Mesh[] = [];
  private camPanEl: HTMLElement;
  private camTiltEl: HTMLElement;
  private servoDirEl: HTMLElement;
  private textWrapper: HTMLElement;

  constructor(private rootElement: HTMLElement) {
    this.initialize();
  }

  private initialize() {
    const width = 300;
    const height = 200;

    // Set up the scene
    this.scene = new THREE.Scene();

    // Set up the camera
    this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    this.camera.position.set(0, 0, 3); // Move camera closer to the object

    // Add ambient light
    const ambientLight = new THREE.AmbientLight(0x404040); // soft white light
    this.scene.add(ambientLight);

    // Add directional light
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(-1, 2, 4).normalize();
    this.scene.add(directionalLight);

    // Set up the renderer
    this.renderer = new THREE.WebGLRenderer({ alpha: true });
    this.renderer.setSize(width, height);
    const camPanElWrapper = document.createElement('div');
    const camTiltWrapper = document.createElement('div');
    const servoDirWrapper = document.createElement('div');
    const camPanLabel = document.createElement('b');
    const camTiltLabel = document.createElement('b');
    const servoDirLabel = document.createElement('b');
    camTiltLabel.innerText = 'Tilt:';
    camPanLabel.innerText = 'Pan:';
    servoDirLabel.innerText = 'Servo Angle:';
    camPanElWrapper.appendChild(camPanLabel);
    camTiltWrapper.appendChild(camTiltLabel);
    servoDirWrapper.appendChild(servoDirLabel);
    this.camPanEl = document.createElement('span');
    this.camTiltEl = document.createElement('span');
    this.servoDirEl = document.createElement('span');
    camPanElWrapper.appendChild(this.camPanEl);
    camTiltWrapper.appendChild(this.camTiltEl);
    servoDirWrapper.appendChild(this.servoDirEl);
    this.textWrapper = document.createElement('div');
    this.textWrapper.classList.add('camera-info');
    this.textWrapper.appendChild(camPanElWrapper);
    this.textWrapper.appendChild(camTiltWrapper);
    this.textWrapper.appendChild(servoDirWrapper);
    this.rootElement.appendChild(this.renderer.domElement);
    this.rootElement.appendChild(this.textWrapper);

    // Create the camera object (representing the 'head')
    this.cameraObject = new THREE.Object3D();

    // Create a transparent sphere for the "head"
    const headGeometry = new THREE.SphereGeometry(0.5, 32, 32);
    const headMaterial = new THREE.MeshPhongMaterial({
      color: 0x3d3d3d,
      transparent: true,
      opacity: 0.3,
    });
    const head = new THREE.Mesh(headGeometry, headMaterial);
    this.cameraObject.add(head);

    // Create eyes for the "head"
    const eyeGeometry = new THREE.SphereGeometry(0.1, 16, 16);
    const eyeMaterial = new THREE.MeshPhongMaterial({ color: 0xffffff });

    const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
    leftEye.position.set(-0.2, 0.2, 0.5);
    this.cameraObject.add(leftEye);

    const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
    rightEye.position.set(0.2, 0.2, 0.5);
    this.cameraObject.add(rightEye);

    // Create pupils for the "eyes"
    const pupilGeometry = new THREE.SphereGeometry(0.05, 16, 16);
    const pupilMaterial = new THREE.MeshPhongMaterial({ color: 0x000000 });

    const leftPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
    leftPupil.position.set(-0.2, 0.2, 0.55);
    this.cameraObject.add(leftPupil);

    const rightPupil = new THREE.Mesh(pupilGeometry, pupilMaterial);
    rightPupil.position.set(0.2, 0.2, 0.55);
    this.cameraObject.add(rightPupil);

    // Add the custom camera object to the scene
    this.scene.add(this.cameraObject);

    // Create wheels for Picar X
    for (let i = 0; i < 4; i++) {
      const wheelGeometry = new THREE.CylinderGeometry(0.2, 0.2, 0.1, 32);
      const wheelMaterial = new THREE.MeshPhongMaterial({ color: 0x000000 });
      const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
      wheel.rotation.z = Math.PI / 2;
      this.wheels.push(wheel);
      this.scene.add(wheel);
    }
    // Position wheels (adjust as necessary)
    this.wheels[0].position.set(-0.7, -0.4, 0.4);
    this.wheels[1].position.set(0.7, -0.4, 0.4);
    this.wheels[2].position.set(-0.7, -0.4, -0.4);
    this.wheels[3].position.set(0.7, -0.4, -0.4);

    const bodyGeometry = new THREE.BoxGeometry(1.5, 0.2, 0.8);
    const bodyMaterial = new THREE.MeshPhongMaterial({ color: 0xaaaaaa });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.set(0, -0.3, 0);
    this.scene.add(body);

    new OrbitControls(this.camera, this.renderer.domElement);

    // Apply the initial tilt immediately
    this.updateTilt(this.tilt);
    this.updateServoDir(this.servoAngle);
    this.camTiltEl.innerText = `${this.tilt}`;
    this.camPanEl.innerText = `${this.pan}`;
    this.servoDirEl.innerText = `${this.servoAngle}`;

    // Start animation loop
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  private animate() {
    requestAnimationFrame(this.animate);
    this.updateCameraRotation();
    this.renderer.render(this.scene, this.camera);
  }

  private updateCameraRotation() {
    this.cameraObject.rotation.y = Math.PI + THREE.MathUtils.degToRad(this.pan); // Update pan based on value
    this.cameraObject.rotation.x = THREE.MathUtils.degToRad(this.tilt); // Update tilt based on value
  }

  public updatePan(pan: number) {
    this.pan = -pan; // Invert the pan direction
    console.log('Pan value updated to:', pan); // Debugging: Check updates
    this.camPanEl.innerText = `${pan}`;
  }

  public updateTilt(tilt: number) {
    this.tilt = tilt;
    this.camTiltEl.innerText = `${tilt}`;
    console.log('Tilt value updated to:', tilt); // Debugging: Check updates
  }

  public updateServoDir(angle: number) {
    this.servoAngle = angle;
    this.servoDirEl.innerText = `${angle}`;
    console.log('Servo angle updated to:', angle); // Debugging: Check updates
  }
}
