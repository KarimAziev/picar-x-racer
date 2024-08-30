import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { colors, MeshFactory } from "./MeshFactory";

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
  private distance: number = 0;
  private servoAngle: number = 0;
  private speed: number = 0;
  private direction: number = 0;
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
  private maxDistance: number = 400;
  private distanceCone: THREE.Mesh;
  private bodyLength: number;
  private scaleFactor: number;
  static originalLength = 0.254;

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

  public updateDirection(direction: number) {
    this.direction = direction;
  }

  public rotateWheels() {
    const maxRPM = 200;
    const gearRatio = 48;
    const wheelCircumference = 0.204;

    const wheelRotationsPerSecond =
      ((this.speed / 100) * maxRPM) / gearRatio / 60;
    const distancePerSecond = wheelRotationsPerSecond * wheelCircumference;

    this.wheels.front.concat(this.wheels.back).forEach((wheel) => {
      const rotationAngle =
        (distancePerSecond / wheelCircumference) * Math.PI * 2;

      const currentRotation = wheel.rotation.y;
      const nextRotation = currentRotation + this.direction * rotationAngle;

      wheel.rotation.y = nextRotation;
    });
  }

  public updateSpeed(speed: number) {
    this.speed = speed;
  }

  public updateServoDir(angle: number) {
    this.servoAngle = angle;
  }

  private renderDistance() {
    const value = this.distance;
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

    const color = this.getColorForDistance(value);
    (this.distanceLine.material as THREE.LineBasicMaterial).color = color;

    const conePos = this.distanceCone.geometry.attributes.position.array;
    conePos[4] = distanceInMeters;

    this.distanceCone.geometry.attributes.position.needsUpdate = true;
    this.distanceCone.position.set(
      this.calcDimension(-0.1),
      0,
      distanceInMeters,
    );

    this.distanceCone.visible = value > 0;

    (this.distanceCone.material as THREE.MeshBasicMaterial).opacity = Math.max(
      0.1,
      (1 - distanceInMeters) / 1,
    );

    this.distanceSpheres.forEach((sphere, index) => {
      const sphereDistance = ((index * 10) / 100) * this.scaleFactor;
      (sphere.material as THREE.MeshBasicMaterial).color =
        this.getColorForDistance((sphereDistance / this.scaleFactor) * 100);

      if (sphereDistance <= distanceInMeters && index > 2) {
        sphere.visible = true;
      } else {
        sphere.visible = false;
      }
    });
  }

  private updateState() {
    this.head.rotation.copy(
      new THREE.Euler(
        THREE.MathUtils.degToRad(-this.tilt),
        THREE.MathUtils.degToRad(-this.pan),
        Math.PI / 2,
      ),
    );
    this.rotateWheels();
    this.renderDistance();
    this.frontWheelAxle.rotation.y = THREE.MathUtils.degToRad(-this.servoAngle);
  }

  private getColorForDistance(distance: number): THREE.Color {
    const normalizedDistance = Math.min(distance / this.maxDistance, 1);
    const color = new THREE.Color();

    if (normalizedDistance <= 0.5) {
      color.setHSL((2 / 3) * (normalizedDistance * 2), 1, 0.5);
    } else {
      color.setHSL((2 / 3) * (1 - (normalizedDistance - 0.5) * 2), 1, 0.5);
    }
    return color;
  }

  private calcDimension(value: number) {
    return (value / 1.5) * this.bodyLength;
  }

  private animate() {
    requestAnimationFrame(this.animate.bind(this));
    this.updateState();
    this.renderer.render(this.scene, this.camera);
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

    this.body = this.createBody();

    this.ultrasonic = this.createUltrasonic();
    this.ultrasonic.position.set(
      0,
      this.calcDimension(-0.05),
      this.calcDimension(0.8),
    );
    this.body.add(this.ultrasonic);

    const neckPos = this.calcDimension(0.2);
    this.head = this.createHead();
    this.neck = this.createNeck();
    this.head.position.set(0, neckPos, 0);
    this.neck.position.set(0, neckPos, this.calcDimension(0.6));
    this.neck.add(this.head);
    this.body.add(this.neck);

    this.controlBoard = this.createControlBoard();
    this.controlBoard.position.set(
      0,
      this.calcDimension(0.2),
      this.calcDimension(-0.3),
    );
    this.body.add(this.controlBoard);

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

  private createBody() {
    return MeshFactory.createBox(
      (0.5 / 1.5) * this.bodyLength,
      (0.1 / 1.5) * this.bodyLength,
      this.bodyLength,
      colors.white,
    );
  }

  private createNeck() {
    return MeshFactory.createCylinder(
      this.calcDimension(0.1),
      this.calcDimension(0.1),
      this.calcDimension(0.6),
      colors.grey,
    );
  }

  private createWheelPairs() {
    const components = [
      this.createWheelPair(this.calcDimension(1.22), this.calcDimension(0.28)),
      this.createWheelPair(this.calcDimension(1.22), this.calcDimension(0.28)),
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
        isFront ? this.calcDimension(0.4) : this.calcDimension(-0.4),
      );

      this[isFront ? "frontWheelAxle" : "backWheelAxle"] = axle;
      this.wheels[isFront ? "front" : "back"] = wheels;
    }
    return [this.frontWheelAxle, this.backWheelAxle];
  }

  private createControlBoard() {
    const controlBoard = MeshFactory.createBox(
      this.calcDimension(0.6),
      this.calcDimension(0.1),
      this.calcDimension(0.9),
      colors.grey,
    );

    const robotHAT = MeshFactory.createBox(
      this.calcDimension(0.6),
      this.calcDimension(0.1),
      this.calcDimension(0.7),
      colors.white2,
    );

    robotHAT.position.set(0, this.calcDimension(0.1), this.calcDimension(0.1));
    controlBoard.add(robotHAT);
    return controlBoard;
  }

  private createUltrasonic() {
    const ultrasonic = MeshFactory.createBox(
      this.calcDimension(0.5),
      this.calcDimension(0.25),
      this.calcDimension(0.01),
      colors.white,
    );

    const greyscaleModule = MeshFactory.createBox(
      this.calcDimension(0.5),
      this.calcDimension(0.25),
      this.calcDimension(0.01),
      colors.white,
    );

    greyscaleModule.rotation.x = Math.PI / 2;
    greyscaleModule.position.set(0, this.calcDimension(-0.12), 0);
    ultrasonic.add(greyscaleModule);

    const rightEye = MeshFactory.createUltrasonicEye(this.calcDimension(0.05));
    const leftEye = MeshFactory.createUltrasonicEye(this.calcDimension(0.05));

    rightEye.position.set(
      this.calcDimension(-0.1),
      0,
      this.calcDimension(0.04),
    );
    leftEye.position.set(this.calcDimension(0.1), 0, this.calcDimension(0.04));

    ultrasonic.add(rightEye);
    ultrasonic.add(leftEye);

    const distanceGeometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, 0),
    ]);

    const distanceMaterial = new THREE.LineBasicMaterial({ color: colors.red });
    this.distanceLine = new THREE.Line(distanceGeometry, distanceMaterial);
    ultrasonic.add(this.distanceLine);

    const coneGeometry = new THREE.ConeGeometry(
      this.calcDimension(0.5),
      this.calcDimension(0.5),
      32,
    );

    const coneMaterial = new THREE.MeshBasicMaterial({
      color: colors.emerald,
      opacity: 0,
      transparent: true,
    });

    this.distanceCone = new THREE.Mesh(coneGeometry, coneMaterial);
    this.distanceCone.position.set(
      this.calcDimension(-0.1),
      0,
      this.calcDimension(0.04),
    );

    this.distanceCone.visible = false;

    this.distanceCone.rotation.x = -Math.PI / 2;
    ultrasonic.add(this.distanceCone);

    const sphereGeometry = new THREE.SphereGeometry(
      this.calcDimension(0.05),
      20,
      20,
    );
    for (let i = 0; i <= this.maxDistance; i += 10) {
      const sphereMaterial = new THREE.MeshBasicMaterial({
        color: this.getColorForDistance(i),
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
    const axle = MeshFactory.createCylinder(
      this.calcDimension(0.05),
      this.calcDimension(0.05),
      height,
      colors.grey,
    );

    const wheelA = this.createWheel(wheelSize);
    const pos = height / 2 - this.calcDimension(0.1);
    wheelA.position.set(0, pos, 0);
    axle.add(wheelA);

    const wheelB = this.createWheel(wheelSize);
    wheelB.position.set(0, -pos, 0);
    axle.add(wheelB);

    return { axle, wheels: [wheelA, wheelB] };
  }

  private createWheel(size = 0.3) {
    const wheelWidth = this.calcDimension(0.18);
    const smallWheelWidth = this.calcDimension(0.19);
    const wheelSize = this.calcDimension(size);

    const wheel = MeshFactory.createCylinder(
      wheelSize,
      wheelSize,
      wheelWidth,
      colors.black,
    );

    const smallWheel = MeshFactory.createCylinder(
      wheelSize - this.calcDimension(0.05),
      wheelSize - this.calcDimension(0.05),
      smallWheelWidth,
      colors.white2,
    );

    wheel.add(smallWheel);

    const spikeWidth = wheelSize * 2;

    for (let i = 0; i < 24; i++) {
      const spike = MeshFactory.createRectangle(
        spikeWidth,
        wheelSize / 2,
        colors.white2,
      );
      wheel.add(spike);
      spike.rotation.y = THREE.MathUtils.degToRad(i * 10);
    }

    return wheel;
  }

  private createHead() {
    const head = MeshFactory.createBox(
      this.calcDimension(0.4),
      this.calcDimension(0.4),
      this.calcDimension(0.4),
      colors.white,
    );

    const camEye = MeshFactory.createBox(
      this.calcDimension(0.2),
      this.calcDimension(0.1),
      this.calcDimension(0.2),
      colors.black,
    );

    camEye.position.set(0, 0, this.calcDimension(0.15));
    head.add(camEye);

    const leftEar = MeshFactory.createTriangle(
      this.calcDimension(0.1),
      colors.white,
    );
    const rightEar = MeshFactory.createTriangle(
      this.calcDimension(0.1),
      colors.white,
    );

    const backRightWall = MeshFactory.createRectangle(
      this.calcDimension(0.2),
      this.calcDimension(0.2),
      colors.white,
    );

    const backLeftWall = MeshFactory.createRectangle(
      this.calcDimension(0.2),
      this.calcDimension(0.2),
      colors.white,
    );

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

    head.add(leftEar);
    head.add(rightEar);
    return head;
  }

  public updateDistance(value: number) {
    this.distance = value;
  }
}
