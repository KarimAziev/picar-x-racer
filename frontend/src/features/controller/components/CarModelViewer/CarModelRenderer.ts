import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export const colors = {
  white: 0xffffff,
  white2: 0xf9f9f9,
  black: 0x000000,
  grey: 0x404040,
  silver: 0xc0c0c0,
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

/**
 * The original Picar-x model has a length of 25.4 cm (0.254 meters),
 * we use the 3D visualization of this car with a length of 1.5 meters.
 *
 * The original Picar-x model dimensions:
 * - Width: 16.51 cm / 100 = 0.1651 meters
 * - Height: 10.16 cm / 100 = 0.1016 meters
 * - Length: 25.4 cm / 100 = 0.254 meters
 */
export class CarModelRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private pan: number = 0;
  private tilt: number = 0;
  private servoAngle: number = 0;
  // speed is in range from to 100
  private speed: number = 0;
  private cameraObject: THREE.Object3D;
  private head: THREE.Mesh;
  private neck: THREE.Mesh;
  private body: THREE.Mesh;
  private ultrasonic: THREE.Mesh;
  private frontWheelAxle: THREE.Mesh<
    THREE.CylinderGeometry,
    THREE.MeshPhongMaterial,
    THREE.Object3DEventMap
  >;
  private backWheelAxle: THREE.Mesh<
    THREE.CylinderGeometry,
    THREE.MeshPhongMaterial,
    THREE.Object3DEventMap
  >;
  private controlBoard: THREE.Mesh;

  private wheels: { front: THREE.Mesh[]; back: THREE.Mesh[] } = {
    front: [],
    back: [],
  };

  private height: number;
  private width: number;

  private distanceLine: THREE.Line;
  private distanceSpheres: THREE.Mesh[] = [];
  // The maximum measurable distance in cm
  private maxDistance: number = 400;
  private distanceCone: THREE.Mesh;

  private bodyLength: number;
  private scaleFactor: number;
  static originalLength = 0.254;

  private calcDimension(value: number) {
    return (value / 1.5) * this.bodyLength;
  }

  constructor(
    private rootElement: HTMLElement,
    params: { width: number; height: number; bodyLength?: number } = {
      width: 400,
      height: 400,
    },
  ) {
    this.height = params.height;
    this.width = params.width;
    this.bodyLength = params.bodyLength || 1.5;
    this.scaleFactor = this.bodyLength / CarModelRenderer.originalLength;
    this.initialize();
  }

  public setSize(width: number, height: number) {
    this.height = height;
    this.width = width;
    this.renderer.setSize(width, height);
  }

  public updatePan(pan: number) {
    this.pan = pan;
  }

  public updateTilt(tilt: number) {
    this.tilt = tilt;
  }

  public updateSpeed(speed: number) {
    this.speed = speed;
    // rotate wheels
    this.wheels.front
      .concat(this.wheels.back)
      .forEach(
        (wheel) => (wheel.rotation.y += -THREE.MathUtils.degToRad(this.speed)),
      );
  }

  public updateServoDir(angle: number) {
    this.servoAngle = angle;
    this.frontWheelAxle.rotation.y = THREE.MathUtils.degToRad(-this.servoAngle);
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
    this.frontWheelAxle.rotation.y = THREE.MathUtils.degToRad(-this.servoAngle);
  }

  private initialize() {
    this.scene = new THREE.Scene();

    this.camera = new THREE.PerspectiveCamera(
      20,
      this.width / this.height,
      0.1,
      1000,
    );

    this.camera.position.set(5, 5, -10);

    this.camera.lookAt(new THREE.Vector3(0, 2, 0));

    const ambientLight = new THREE.AmbientLight(colors.white);
    this.scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(colors.white, 1);
    directionalLight.position.set(1, 2, 4).normalize();

    this.scene.add(directionalLight);

    this.renderer = new THREE.WebGLRenderer({ alpha: true });
    this.renderer.setSize(this.width, this.height);
    this.rootElement.appendChild(this.renderer.domElement);

    this.cameraObject = new THREE.Object3D();

    this.cameraObject.rotation.y = THREE.MathUtils.degToRad(120);

    this.body = this.createBody(this.calcDimension(this.bodyLength));

    this.ultrasonic = this.createUltrasonic();
    this.ultrasonic.position.set(
      0,
      this.calcDimension(-0.05),
      this.calcDimension(0.8),
    );

    this.body.add(this.ultrasonic);

    // adding neck with head
    const neckPos = this.calcDimension(0.2);
    this.head = this.createHead();
    this.neck = this.createNeck();
    this.head.position.set(0, neckPos, 0);
    this.neck.position.set(0, neckPos, this.calcDimension(0.6));
    this.neck.add(this.head);
    this.body.add(this.neck);

    // adding controlBoard to the back of the car
    this.controlBoard = this.createControlBoard();
    this.controlBoard.position.set(
      0,
      this.calcDimension(0.2),
      this.calcDimension(-0.3),
    );
    this.body.add(this.controlBoard);

    // adding axles with wheels
    const wheelPairs = this.createWheelPairs();

    wheelPairs.forEach((pair) => {
      this.body.add(pair);
    });

    new OrbitControls(this.camera, this.renderer.domElement);

    this.cameraObject.add(this.body);
    this.scene.add(this.cameraObject);

    this.updateTilt(this.tilt);
    this.updateServoDir(this.servoAngle);
    this.updatePan(this.pan);

    requestAnimationFrame(this.animate.bind(this));
  }

  private createBody(depth = 1.5) {
    const width = (0.5 / 1.5) * depth;
    const height = (0.1 / 1.5) * depth;
    const bodyGeometry = new THREE.BoxGeometry(width, height, depth);
    const bodyMaterial = new THREE.MeshPhongMaterial({ color: colors.white });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    return body;
  }

  private createNeck() {
    return new THREE.Mesh(
      new THREE.CylinderGeometry(
        this.calcDimension(0.1),
        this.calcDimension(0.1),
        this.calcDimension(0.6),
      ),
      new THREE.MeshBasicMaterial({ color: colors.grey }),
    );
  }

  private createWheelPairs() {
    const components = [
      this.createWheelPair(this.calcDimension(1.2), this.calcDimension(0.28)),
      this.createWheelPair(this.calcDimension(1.22), this.calcDimension(0.3)),
    ];
    for (let i = 0; i < components.length; i++) {
      const isFront = i === 0;
      const comp = components[i];
      const axle = comp.axle;
      const wheels = comp.wheels;

      axle.rotation.z = -Math.PI / 2;
      axle.position.set(
        0,
        0,
        isFront ? this.calcDimension(0.3) : this.calcDimension(-0.4),
      );

      this[isFront ? "frontWheelAxle" : "backWheelAxle"] = axle;
      this.wheels[isFront ? "front" : "back"] = wheels;
    }
    return [this.frontWheelAxle, this.backWheelAxle];
  }

  private createControlBoard() {
    const raspberryGeometry = new THREE.BoxGeometry(
      this.calcDimension(0.6),
      this.calcDimension(0.1),
      this.calcDimension(0.9),
    );
    const raspberryMaterial = new THREE.MeshPhongMaterial({
      color: colors.grey,
    });
    const raspberry = new THREE.Mesh(raspberryGeometry, raspberryMaterial);
    const wireGeometry = new THREE.BoxGeometry(
      this.calcDimension(0.6),
      this.calcDimension(0.1),
      this.calcDimension(0.7),
    );
    const wireMaterial = new THREE.MeshPhongMaterial({ color: colors.white2 });
    const wire = new THREE.Mesh(wireGeometry, wireMaterial);
    wire.position.set(0, this.calcDimension(0.1), this.calcDimension(0.1));
    raspberry.add(wire);
    return raspberry;
  }

  private createUltrasonicEye() {
    const eyeGeometry = new THREE.CylinderGeometry(
      this.calcDimension(0.05),
      this.calcDimension(0.05),
      this.calcDimension(0.1),
    );

    const eyeMaterial = new THREE.MeshPhongMaterial({ color: colors.silver });
    const eye = new THREE.Mesh(eyeGeometry, eyeMaterial);
    const smallEye = new THREE.Mesh(
      new THREE.CylinderGeometry(
        this.calcDimension(0.04),
        this.calcDimension(0.04),
        this.calcDimension(0.01),
      ),
      new THREE.MeshPhongMaterial({ color: colors.black }),
    );
    smallEye.position.set(0, this.calcDimension(-0.05), 0);
    eye.add(smallEye);
    eye.rotation.x = -Math.PI / 2;
    return eye;
  }

  // value is a number - centimeters
  public updateDistance(value: number) {
    const distanceInMeters = (value / 100) * this.scaleFactor;

    const positions = this.distanceLine.geometry.attributes.position
      .array as Float32Array;

    positions[0] = this.calcDimension(-0.1);
    positions[1] = 0;
    positions[2] = 0;

    positions[3] = 0;
    positions[4] = 0;
    positions[5] = distanceInMeters;

    this.distanceLine.geometry.attributes.position.needsUpdate = true;

    const color = getColorForDistance(value, this.maxDistance);
    (this.distanceLine.material as THREE.LineBasicMaterial).color = color;
    const conePos = this.distanceCone.geometry.attributes.position.array;
    conePos[4] = distanceInMeters;
    this.distanceCone.geometry.attributes.position.needsUpdate = true;
    /**
     * this.distanceCone.scale.set(1, distanceInMeters, 1);
     */

    this.distanceCone.position.set(
      this.calcDimension(-0.1),
      0,
      distanceInMeters,
    );
    (this.distanceCone.material as THREE.MeshBasicMaterial).opacity = Math.max(
      0.1,
      1 - distanceInMeters / 1,
    );

    this.distanceSpheres.forEach((sphere, index) => {
      const sphereDistance = ((index * 10) / 100) * this.scaleFactor;
      (sphere.material as THREE.MeshBasicMaterial).color = getColorForDistance(
        (sphereDistance / this.scaleFactor) * 100,
        this.maxDistance,
      );

      if (sphereDistance <= distanceInMeters && index > 2) {
        sphere.visible = true;
      } else {
        sphere.visible = false;
      }
    });
  }

  private createUltrasonic() {
    const ultrasonicGeometry = new THREE.BoxGeometry(
      this.calcDimension(0.5),
      this.calcDimension(0.25),
      this.calcDimension(0.01),
    );
    const ultrasonicMaterial = new THREE.MeshPhongMaterial({
      color: colors.white,
    });

    const ultrasonic = new THREE.Mesh(ultrasonicGeometry, ultrasonicMaterial);
    const greyscaleModule = new THREE.Mesh(
      ultrasonicGeometry,
      ultrasonicMaterial,
    );
    const rightEye = this.createUltrasonicEye();
    const leftEye = this.createUltrasonicEye();
    const distanceGeometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, 0),
    ]);

    const distanceMaterial = new THREE.LineBasicMaterial({ color: 0xff0000 });
    this.distanceLine = new THREE.Line(distanceGeometry, distanceMaterial);

    ultrasonic.add(this.distanceLine);

    leftEye.position.set(this.calcDimension(0.1), 0, this.calcDimension(0.04));
    rightEye.position.set(
      this.calcDimension(-0.1),
      0,
      this.calcDimension(0.04),
    );
    ultrasonic.add(leftEye);
    ultrasonic.add(rightEye);
    ultrasonic.add(greyscaleModule);
    greyscaleModule.rotation.x = Math.PI / 2;
    greyscaleModule.position.set(0, this.calcDimension(-0.12), 0);

    const coneGeometry = new THREE.ConeGeometry(
      this.calcDimension(0.5),
      this.calcDimension(0.5),
      32,
    );
    const coneMaterial = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      opacity: 0.8,
      transparent: true,
    });

    this.distanceCone = new THREE.Mesh(coneGeometry, coneMaterial);

    this.distanceCone.position.set(
      this.calcDimension(-0.1),
      0,
      this.calcDimension(0.04),
    );
    this.distanceCone.rotation.x = -Math.PI / 2;
    ultrasonic.add(this.distanceCone);

    const sphereGeometry = new THREE.SphereGeometry(
      this.calcDimension(0.05),
      20,
      20,
    );
    for (let i = 0; i <= this.maxDistance; i += 10) {
      const sphereMaterial = new THREE.MeshBasicMaterial({
        color: getColorForDistance(i, this.maxDistance),
      });
      const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial);
      sphere.position.set(
        this.calcDimension(-0.05),
        0,
        0.1 + (i / 100) * this.scaleFactor,
      );
      this.distanceSpheres.push(sphere);
      this.distanceLine.add(sphere);
    }

    return ultrasonic;
  }

  private createWheelPair(height = 1.2, wheelSize = 0.3) {
    const axleGeometry = new THREE.CylinderGeometry(
      this.calcDimension(0.05),
      this.calcDimension(0.05),
      height,
      32,
    );
    const axleMaterial = new THREE.MeshPhongMaterial({
      color: colors.grey,
    });
    const axle = new THREE.Mesh(axleGeometry, axleMaterial);
    const wheelA = this.createWheel(wheelSize);
    const pos = height / 2 - this.calcDimension(0.1);
    wheelA.position.set(0, pos, 0);
    const wheelB = this.createWheel(wheelSize);
    wheelB.position.set(0, -pos, 0);
    axle.add(wheelA);
    axle.add(wheelB);
    return { axle, wheels: [wheelA, wheelB] };
  }

  private createWheel(size = 0.3) {
    const wheelGeometry = new THREE.CylinderGeometry(
      size,
      size,
      this.calcDimension(0.18),
      32,
    );
    const wheelMaterial = new THREE.MeshPhongMaterial({
      color: colors.black,
    });
    const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
    const smallWheelGeometry = new THREE.CylinderGeometry(
      size - this.calcDimension(0.05),
      size - this.calcDimension(0.05),
      this.calcDimension(0.19),
      32,
    );
    const smallWheelMaterial = new THREE.MeshPhongMaterial({
      color: 0xf9f9f9,
    });
    const smallWheel = new THREE.Mesh(smallWheelGeometry, smallWheelMaterial);
    wheel.add(smallWheel);
    return wheel;
  }

  private createHead() {
    const headGeometry = new THREE.BoxGeometry(
      this.calcDimension(0.4),
      this.calcDimension(0.4),
      this.calcDimension(0.4),
      1,
    );
    const headMaterial = new THREE.MeshPhongMaterial({ color: colors.white });
    this.head = new THREE.Mesh(headGeometry, headMaterial);
    const leftEar = this.createTriangle(this.calcDimension(0.1), colors.white);
    const rightEar = this.createTriangle(this.calcDimension(0.1), colors.white);

    const backRightWall = this.createRectangle(
      this.calcDimension(0.2),
      this.calcDimension(0.2),
      colors.white,
    );
    const backLeftWall = this.createRectangle(
      this.calcDimension(0.2),
      this.calcDimension(0.2),
      colors.white,
    );

    const camEye = new THREE.Mesh(
      new THREE.BoxGeometry(
        this.calcDimension(0.2),
        this.calcDimension(0.1),
        this.calcDimension(0.2),
      ),
      new THREE.MeshPhongMaterial({ color: colors.black }),
    );
    camEye.position.set(0, 0, this.calcDimension(0.15));
    backRightWall.position.set(0, this.calcDimension(-0.2), 0);
    backLeftWall.position.set(0, this.calcDimension(-0.2), 0);
    leftEar.add(backLeftWall);
    rightEar.add(backRightWall);
    leftEar.position.set(
      this.calcDimension(0.2),
      this.calcDimension(-0.2),
      this.calcDimension(0.1),
    );
    leftEar.rotation.x = Math.PI / 2;
    rightEar.position.set(
      this.calcDimension(0.2),
      this.calcDimension(0.2),
      this.calcDimension(0.1),
    );
    rightEar.rotation.x = Math.PI / 2;

    this.head.add(camEye);
    this.head.add(leftEar);
    this.head.add(rightEar);
    return this.head;
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
}
