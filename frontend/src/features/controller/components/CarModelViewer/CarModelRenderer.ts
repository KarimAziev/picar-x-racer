import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export const colors = {
  white: 0xffffff,
  white2: 0xf9f9f9,
  black: 0x000000,
  grey: 0x404040,
};

function getColorForDistance(
  distance: number,
  maxDistance: number,
): THREE.Color {
  const normalizedDistance = Math.min(distance / maxDistance, 1);
  const color = new THREE.Color();

  if (normalizedDistance <= 0.5) {
    color.setHSL((2 / 3) * (normalizedDistance * 2), 1, 0.5); // Green to Yellow
  } else {
    color.setHSL((2 / 3) * (1 - (normalizedDistance - 0.5) * 2), 1, 0.5); // Yellow to Red
  }

  return color;
}

export class CarModelRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private pan: number = 0;
  private tilt: number = 0;
  private servoAngle: number = 0;
  private cameraObject: THREE.Object3D;
  private head: THREE.Mesh;
  private wheels: { front: THREE.Mesh[]; back: THREE.Mesh[] } = {
    front: [],
    back: [],
  };
  private height: number;
  private width: number;

  private distanceLine: THREE.Line;
  private distanceSpheres: THREE.Mesh[] = [];
  private maxDistance: number = 400; // The maximum measurable distance in cm
  private distanceCone: THREE.Mesh;

  constructor(
    private rootElement: HTMLElement,
    params = { width: 300, height: 300 },
  ) {
    this.height = params.height;
    this.width = params.width;
    this.initialize();
  }

  setSize(width: number, height: number) {
    this.height = height;
    this.width = width;
    this.renderer.setSize(width, height);
  }

  private initialize() {
    this.scene = new THREE.Scene();

    this.camera = new THREE.PerspectiveCamera(
      20,
      this.width / this.height,
      0.1,
      1000,
    );
    this.camera.position.set(0, 5, -10);

    this.camera.lookAt(new THREE.Vector3(0, 0, 0));

    const ambientLight = new THREE.AmbientLight(colors.white);
    this.scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(colors.white, 1);
    directionalLight.position.set(-1, 2, 4).normalize();
    this.scene.add(directionalLight);

    this.renderer = new THREE.WebGLRenderer({ alpha: true });
    this.renderer.setSize(this.width, this.height);
    this.rootElement.appendChild(this.renderer.domElement);

    this.cameraObject = new THREE.Object3D();

    const bodyGeometry = new THREE.BoxGeometry(0.5, 0.1, 1.5);
    const bodyMaterial = new THREE.MeshPhongMaterial({ color: colors.white });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.set(0, -0.3, 0);

    const ultrasonicGeometry = new THREE.BoxGeometry(0.7, 0.4, 0.1);
    const ultrasonicMaterial = new THREE.MeshPhongMaterial({
      color: colors.white,
    });
    const ultrasonic = new THREE.Mesh(ultrasonicGeometry, ultrasonicMaterial);
    ultrasonic.position.set(0, -0.4, 0.8);
    this.scene.add(ultrasonic);

    const headGeometry = new THREE.BoxGeometry(0.4, 0.4, 0.4, 1);
    const headMaterial = new THREE.MeshPhongMaterial({ color: colors.white });
    const head = new THREE.Mesh(headGeometry, headMaterial);
    this.head = head;
    /**
     * head.position.set(0, 0.1, 0.7);
     */

    const camEye = new THREE.Mesh(
      new THREE.BoxGeometry(0.2, 0.1, 0.2),
      new THREE.MeshPhongMaterial({ color: colors.black }),
    );
    camEye.position.set(0, 0, 0.15);
    const neck = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.1, 0.6),
      new THREE.MeshBasicMaterial({ color: colors.grey }),
    );
    neck.position.set(0, 0.2, 0.6);
    body.add(neck);
    neck.add(this.head);
    head.position.set(0, 0.2, 0);

    const raspberryGeometry = new THREE.BoxGeometry(0.6, 0.1, 0.9);
    const raspberryMaterial = new THREE.MeshPhongMaterial({
      color: colors.grey,
    });
    const raspberry = new THREE.Mesh(raspberryGeometry, raspberryMaterial);
    const wireGeometry = new THREE.BoxGeometry(0.6, 0.1, 0.7);
    const wireMaterial = new THREE.MeshPhongMaterial({ color: colors.white2 });
    const wire = new THREE.Mesh(wireGeometry, wireMaterial);

    const leftEar = this.createTriangle(0.1, colors.white);
    const rightEar = this.createTriangle(0.1, colors.white);

    const backRightWall = this.createRectangle(0.2, 0.2, colors.white);
    const backLeftWall = this.createRectangle(0.2, 0.2, colors.white);
    backRightWall.position.set(0, -0.2, 0);
    backLeftWall.position.set(0, -0.2, 0);
    leftEar.add(backLeftWall);
    rightEar.add(backRightWall);

    body.add(raspberry);
    raspberry.position.set(0, 0.2, -0.3);
    wire.position.set(0, 0.1, 0.1);
    raspberry.add(wire);
    leftEar.position.set(0.2, -0.2, 0.1);
    leftEar.rotation.x = Math.PI / 2;
    rightEar.position.set(0.2, 0.2, 0.1);
    rightEar.rotation.x = Math.PI / 2;

    head.add(camEye);
    head.add(leftEar);
    head.add(rightEar);

    for (let i = 0; i < 4; i++) {
      const wheelGeometry = new THREE.CylinderGeometry(0.3, 0.3, 0.18, 32);
      const wheelMaterial = new THREE.MeshPhongMaterial({
        color: colors.black,
      });
      const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
      const smallWheelGeometry = new THREE.CylinderGeometry(
        0.25,
        0.25,
        0.19,
        32,
      );
      const smallWheelMaterial = new THREE.MeshPhongMaterial({
        color: 0xf9f9f9,
      });
      const smallWheel = new THREE.Mesh(smallWheelGeometry, smallWheelMaterial);
      const extraSmallWheelGeometry = new THREE.CylinderGeometry(
        0.05,
        0.05,
        0.5,
        32,
      );
      const extraSmallWheelMaterial = new THREE.MeshPhongMaterial({
        color: colors.black,
      });
      const extraSmallWheel = new THREE.Mesh(
        extraSmallWheelGeometry,
        extraSmallWheelMaterial,
      );
      smallWheel.add(extraSmallWheel);

      wheel.rotation.z = -Math.PI / 2;
      extraSmallWheel.position.set(
        0,
        i === 0 ? 0.1 : i === 1 ? -0.1 : i === 2 ? 0.1 : -0.1,
        0,
      );

      wheel.add(smallWheel);
      if (i < 2) {
        this.wheels.front.push(wheel);
      } else {
        this.wheels.back.push(wheel);
      }

      this.scene.add(wheel);
    }

    this.wheels.front[0].position.set(-0.6, -0.4, 0.4);
    this.wheels.front[1].position.set(0.6, -0.4, 0.4);
    this.wheels.back[0].position.set(-0.6, -0.4, -0.4);
    this.wheels.back[1].position.set(0.6, -0.4, -0.4);

    new OrbitControls(this.camera, this.renderer.domElement);

    this.updateTilt(this.tilt);
    this.updateServoDir(this.servoAngle);
    this.updatePan(this.pan);

    const distanceGeometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, -1, 0), // Start point (the front of the car)
      new THREE.Vector3(0, -1, 0), // End point (initially the same as the start point)
    ]);

    const distanceMaterial = new THREE.LineBasicMaterial({ color: 0xff0000 });
    this.distanceLine = new THREE.Line(distanceGeometry, distanceMaterial);
    ultrasonic.add(this.distanceLine);

    const coneGeometry = new THREE.ConeGeometry(0.05, 1, 32);
    const coneMaterial = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      opacity: 0.6,
      transparent: true,
    });
    this.distanceCone = new THREE.Mesh(coneGeometry, coneMaterial);
    this.distanceCone.position.set(0.3, 0, 0.2);
    this.distanceCone.rotation.x = Math.PI / 2;
    ultrasonic.add(this.distanceCone);

    // spheres at regular intervals
    const sphereGeometry = new THREE.SphereGeometry(0.05, 16, 16);
    for (let i = 0; i <= this.maxDistance; i += 10) {
      const sphereMaterial = new THREE.MeshBasicMaterial({
        color: getColorForDistance(i, this.maxDistance),
      });
      const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial);
      sphere.position.set(0, 0, 0.25 + i / 100);
      this.distanceSpheres.push(sphere);
      body.add(sphere);
    }

    this.cameraObject.add(body);
    this.scene.add(this.cameraObject);

    requestAnimationFrame(this.animate.bind(this));
  }

  private createRectangle(width: number, height: number, color = 0x00ff00) {
    const geometry = new THREE.PlaneGeometry(width, height);

    const material = new THREE.MeshPhongMaterial({
      color,
      side: THREE.DoubleSide,
    });

    const rectangle = new THREE.Mesh(geometry, material);

    return rectangle;
  }

  private createTriangle(size: number, color = 0x00ff00) {
    const vertices = new Float32Array([
      0.0,
      size,
      0.0, // Vertex 1
      -size,
      -size,
      0.0, // Vertex 2
      size,
      -size,
      0.0, // Vertex 3
    ]);

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(vertices, 3),
    );
    geometry.computeVertexNormals();

    const material = new THREE.MeshPhongMaterial({
      color: color,
      side: THREE.DoubleSide,
    });

    const triangle = new THREE.Mesh(geometry, material);

    return triangle;
  }

  // value is a number - centimeters
  public updateDistance(value: number) {
    const distanceInMeters = value / 100;

    const positions = this.distanceLine.geometry.attributes.position
      .array as Float32Array;

    // The first point is always at the initial position
    positions[0] = 0;
    positions[1] = 0.2;
    positions[2] = 0.25;

    positions[3] = 0;
    positions[4] = 0.2;
    positions[5] = 0.25 + distanceInMeters;

    this.distanceLine.geometry.attributes.position.needsUpdate = true;

    const color = getColorForDistance(value, 100);
    (this.distanceLine.material as THREE.LineBasicMaterial).color = color;

    this.distanceCone.scale.set(1, distanceInMeters, 1);
    (this.distanceCone.material as THREE.MeshBasicMaterial).opacity = Math.max(
      0.1,
      1 - distanceInMeters / 1,
    );

    this.distanceCone.position.z = 0.25 + distanceInMeters / 2;

    this.distanceSpheres.forEach((sphere, index) => {
      const sphereDistance = (index * 10) / 100;
      (sphere.material as THREE.MeshBasicMaterial).color = getColorForDistance(
        sphereDistance * 100,
        this.maxDistance,
      );

      if (sphereDistance <= distanceInMeters) {
        sphere.visible = true;
      } else {
        sphere.visible = false;
      }
    });
  }

  private animate() {
    requestAnimationFrame(this.animate.bind(this));
    this.updateCameraRotation();
    this.renderer.render(this.scene, this.camera);
  }

  private updateCameraRotation() {
    this.head.rotation.copy(
      new THREE.Euler(
        THREE.MathUtils.degToRad(-this.tilt),
        THREE.MathUtils.degToRad(-this.pan),
        Math.PI / 2,
      ),
    );
    this.wheels.front.forEach((wheel) => {
      wheel.rotation.y = THREE.MathUtils.degToRad(-this.servoAngle);
    });
  }

  public updatePan(pan: number) {
    this.pan = pan;
  }

  public updateTilt(tilt: number) {
    this.tilt = tilt;
  }

  public updateServoDir(angle: number) {
    this.servoAngle = angle;

    this.wheels.front.forEach((wheel) => {
      wheel.rotation.copy(
        new THREE.Euler(0, THREE.MathUtils.degToRad(angle), -Math.PI / 2),
      );
    });
  }
}
