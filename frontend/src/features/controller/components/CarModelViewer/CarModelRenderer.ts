import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export class CarModelRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private pan: number = 0;
  private tilt: number = 0;
  private servoAngle: number = 0;
  private cameraObject: THREE.Object3D;
  private wheels: { front: THREE.Mesh[]; back: THREE.Mesh[] } = {
    front: [],
    back: [],
  };

  constructor(private rootElement: HTMLElement) {
    this.initialize();
  }

  private initialize() {
    const width = 300;
    const height = 300;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(20, width / height, 0.1, 1000);
    this.camera.position.set(0, 5, 10);
    this.camera.lookAt(new THREE.Vector3(0, 0, 0));

    const ambientLight = new THREE.AmbientLight(0x404040);
    this.scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(-1, 2, 4).normalize();
    this.scene.add(directionalLight);

    this.renderer = new THREE.WebGLRenderer({ alpha: true });
    this.renderer.setSize(width, height);
    this.rootElement.appendChild(this.renderer.domElement);

    this.cameraObject = new THREE.Object3D();
    this.scene.add(this.cameraObject);

    const bodyGeometry = new THREE.BoxGeometry(1, 0.3, 2.5);
    const bodyMaterial = new THREE.MeshPhongMaterial({ color: 0xffffff });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.set(0, -0.3, 0);
    this.scene.add(body);

    const headGeometry = new THREE.BoxGeometry(0.5, 0.5, 0.5);
    const headMaterial = new THREE.MeshPhongMaterial({ color: 0xffffff });
    const head = new THREE.Mesh(headGeometry, headMaterial);
    this.cameraObject.add(head);

    const eyeGeometry = new THREE.SphereGeometry(0.1, 32, 32);
    const eyeMaterial = new THREE.MeshPhongMaterial({ color: 0x10b981 });
    const eyeCamera = new THREE.Mesh(eyeGeometry, eyeMaterial);
    eyeCamera.position.set(0, 0.15, 0.25);
    head.add(eyeCamera);

    const beamGeometry = new THREE.ConeGeometry(0.05, 1, 32);
    const beamMaterial = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      opacity: 0.6,
      transparent: true,
    });
    const beam = new THREE.Mesh(beamGeometry, beamMaterial);
    beam.position.set(0, 0.2, 1);
    beam.rotation.x = Math.PI / 2;
    eyeCamera.add(beam);

    const earGeometry = new THREE.BoxGeometry(0.1, 0.3, 0.1);
    const earMaterial = new THREE.MeshPhongMaterial({ color: 0x3d3d3d });
    const leftEar = new THREE.Mesh(earGeometry, earMaterial);
    const rightEar = new THREE.Mesh(earGeometry, earMaterial);
    leftEar.position.set(-0.3, 0, 0);
    rightEar.position.set(0.3, 0, 0);
    head.add(leftEar);
    head.add(rightEar);

    for (let i = 0; i < 4; i++) {
      const wheelGeometry = new THREE.CylinderGeometry(0.3, 0.3, 0.1, 32);
      const wheelMaterial = new THREE.MeshPhongMaterial({ color: 0x000000 });
      const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
      wheel.rotation.z = -Math.PI / 2;

      if (i < 2) {
        this.wheels.front.push(wheel);
      } else {
        this.wheels.back.push(wheel);
      }
      this.scene.add(wheel);
    }

    this.wheels.front[0].position.set(-0.6, -0.4, 1);
    this.wheels.front[1].position.set(0.6, -0.4, 1);
    this.wheels.back[0].position.set(-0.6, -0.4, -1.2);
    this.wheels.back[1].position.set(0.6, -0.4, -1.2);

    new OrbitControls(this.camera, this.renderer.domElement);

    this.updateTilt(this.tilt);
    this.updateServoDir(this.servoAngle);
    this.updatePan(this.pan);

    requestAnimationFrame(this.animate.bind(this));
  }

  private animate() {
    requestAnimationFrame(this.animate.bind(this));
    this.updateCameraRotation();
    this.renderer.render(this.scene, this.camera);
  }

  private updateCameraRotation() {
    this.cameraObject.rotation.y = Math.PI + THREE.MathUtils.degToRad(this.pan);
    this.cameraObject.rotation.x = THREE.MathUtils.degToRad(this.tilt);

    this.wheels.back.forEach((wheel) => {
      wheel.rotation.y = THREE.MathUtils.degToRad(this.servoAngle);
    });
  }

  public updatePan(pan: number) {
    this.pan = -pan;
  }

  public updateTilt(tilt: number) {
    this.tilt = tilt;
  }

  public updateServoDir(angle: number) {
    this.servoAngle = -angle;

    this.wheels.back.forEach((wheel) => {
      wheel.rotation.copy(
        new THREE.Euler(0, THREE.MathUtils.degToRad(angle), Math.PI / 2),
      );
    });
  }
}
