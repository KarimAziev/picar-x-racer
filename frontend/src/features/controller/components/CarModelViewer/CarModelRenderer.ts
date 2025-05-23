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
 * - Diameter of wheels is around 65mm (0.065 meters)
 */

export class CarModelRenderer {
  private scene: THREE.Scene;
  public camera: THREE.PerspectiveCamera;
  public cameraObject: THREE.Object3D;
  private detectedWall: THREE.Mesh;
  private renderer: THREE.WebGLRenderer;
  private pan: number = 0;
  private tilt: number = 0;
  private distance: number = 0;
  private servoAngle: number = 0;
  private sceneNeedsUpdate = true;
  private orbitNeedsUpdate = false;
  private initted = false;
  private speed: number = 0;
  private direction: number = 0;
  private prevDistance: number = 0;
  private prevPan: number = 0;
  private prevTilt: number = 0;
  private prevServoAngle: number = 0;
  private prevSpeed: number = 0;
  private prevDirection: number = 0;
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
  private prevHeight: number;
  private prevWidth: number;
  private distanceLine: THREE.Line;
  private distanceSpheres: THREE.Mesh[] = [];
  private maxDistance: number = 400;
  private distanceCone: THREE.Mesh;
  /**
   * this.bodyLength / CarModelRenderer.originalLength
   */
  private bodyLength: number;
  private scaleFactor: number;

  /**
   * The original Picar-x model has a length of 25.4 cm (0.254 meters),
   */
  static originalLength = 0.254;
  /**
  Diameter of wheels is around 65mm (0.065 meters)
   */
  static wheelDiameter = 0.065;
  /**
  The wheel circumference using the formula circumference = π * diameter
   */
  static wheelCircumference = Math.PI * CarModelRenderer.wheelDiameter;
  /**
  Maximum rotations per minute of the motor
   */
  static maxRPM = 200;
  /**
  DC motors with a `1:48` gear ratio allow the max speed of a PiCar-X to be around 1.8 to 2 km/h.
   */
  static gearRatio = 48;

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
    this.prevHeight = this.height;
    this.prevWidth = this.width;
    this.height = height;
    this.width = width;
    const w = width;
    const h = height;
    const fullWidth = w;
    const fullHeight = h;
    this.renderer.setSize(width, height);
    this.camera.setViewOffset(fullWidth, fullHeight, w * 0, h * 0, w, h);
  }

  public updatePan(pan: number) {
    this.prevPan = this.pan;
    this.pan = pan;
  }

  public updateTilt(tilt: number) {
    this.prevTilt = this.tilt;
    this.tilt = tilt;
  }

  public updateDirection(direction: number) {
    this.prevDirection = this.direction;
    this.direction = direction;
  }

  public updateDistance(value: number) {
    this.prevDistance = this.distance;
    this.distance = value;
  }

  public rotateWheels() {
    const wheelRotationsPerSecond =
      ((this.speed / 100) * CarModelRenderer.maxRPM) /
      CarModelRenderer.gearRatio /
      60;
    const distancePerSecond =
      wheelRotationsPerSecond * CarModelRenderer.wheelCircumference;

    this.wheels.front.concat(this.wheels.back).forEach((wheel) => {
      const rotationAngle =
        (distancePerSecond / CarModelRenderer.wheelCircumference) * Math.PI * 2;

      const currentRotation = wheel.rotation.y;
      const nextRotation = currentRotation + this.direction * rotationAngle;

      wheel.rotation.y = nextRotation;
    });
  }

  public updateSpeed(speed: number) {
    this.prevSpeed = this.speed;
    this.speed = speed;
  }

  public updateServoDir(angle: number) {
    this.prevServoAngle = this.servoAngle;
    this.servoAngle = angle;
  }

  private initialize() {
    this.scene = new THREE.Scene();

    this.camera = new THREE.PerspectiveCamera(
      40,
      this.width / this.height,
      0.1,
      1000,
    );

    this.camera.zoom = 5;

    this.camera.position.set(5, 5, -40);
    this.camera.lookAt(new THREE.Vector3(0, 2, 0));

    const ambientLight = new THREE.AmbientLight(colors.white);
    this.scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(colors.whiteMute, 1);
    directionalLight.position.set(1, 2, 4).normalize();
    this.scene.add(directionalLight);

    this.renderer = new THREE.WebGLRenderer({ alpha: true });
    this.rootElement.appendChild(this.renderer.domElement);

    this.cameraObject = new THREE.Object3D();
    this.cameraObject.rotation.y = THREE.MathUtils.degToRad(25);

    this.body = this.createBody();

    this.ultrasonic = this.createUltrasonic();
    this.ultrasonic.position.set(
      0,
      this.calcDimension(-0.05),
      this.calcDimension(0.7),
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
      this.calcDimension(0.23),
      this.calcDimension(-0.3),
    );
    this.body.add(this.controlBoard);

    const wheelPairs = this.createWheelPairs();
    wheelPairs.forEach((pair) => {
      this.body.add(pair);
    });

    this.detectedWall = MeshFactory.createBox(
      this.calcDimension(2),
      this.calcDimension(2),
      this.calcDimension(0.1),
      colors.red,
      { transparent: true, opacity: 0.2 },
    );
    this.detectedWall.visible = false;
    this.body.add(this.detectedWall);

    new OrbitControls(this.camera, this.renderer.domElement).addEventListener(
      "change",
      () => {
        this.orbitNeedsUpdate = true;
      },
    );

    this.cameraObject.add(this.body);
    this.scene.add(this.cameraObject);

    this.updateTilt(this.tilt);
    this.updateServoDir(this.servoAngle);
    this.updatePan(this.pan);
    this.setSize(this.width, this.height);

    this.renderer.render(this.scene, this.camera);

    requestAnimationFrame(this.animate.bind(this));
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

    if (value > 0) {
      this.detectedWall.visible = true;
      this.detectedWall.position.set(0, 0, distanceInMeters + this.bodyLength);
    } else {
      this.detectedWall.visible = false;
    }
  }

  private updateState(force?: boolean) {
    const shouldUpdate =
      force ||
      !![
        [true, this.initted],
        [0, this.speed],
        [this.prevTilt, this.tilt],
        [this.prevPan, this.pan],
        [this.prevSpeed, this.speed],
        [this.prevDirection, this.direction],
        [this.prevDistance, this.distance],
        [this.prevServoAngle, this.servoAngle],
        [this.prevWidth, this.width],
        [this.prevHeight, this.height],
      ].find(([a, b]) => a !== b);

    if (shouldUpdate) {
      this.head.rotation.copy(
        new THREE.Euler(
          THREE.MathUtils.degToRad(-this.tilt),
          THREE.MathUtils.degToRad(-this.pan),
          Math.PI / 2,
        ),
      );
      this.prevTilt = this.tilt;
      this.prevPan = this.pan;
    }
    if (shouldUpdate) {
      this.rotateWheels();
      this.prevSpeed = this.speed;
      this.prevDirection = this.direction;
    }
    if (shouldUpdate) {
      this.renderDistance();
      this.prevDistance = this.distance;
    }
    if (shouldUpdate) {
      this.frontWheelAxle.rotation.y = THREE.MathUtils.degToRad(
        -this.servoAngle,
      );
      this.prevServoAngle = this.servoAngle;
    }

    if (shouldUpdate) {
      this.initted = true;
      this.prevWidth = this.width;
      this.prevHeight = this.height;
    }

    this.sceneNeedsUpdate = shouldUpdate;
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
    this.updateState(this.orbitNeedsUpdate);
    if (this.sceneNeedsUpdate) {
      this.renderer.render(this.scene, this.camera);
      this.sceneNeedsUpdate = false;
      this.orbitNeedsUpdate = false;
    }
    requestAnimationFrame(this.animate.bind(this));
  }

  private createBody() {
    const backRightWall = MeshFactory.createBox(
      this.calcDimension(0.2),
      this.calcDimension(0.09),
      this.calcDimension(0.3),
      colors.white,
    );

    const bodyTop = MeshFactory.createBox(
      this.calcDimension(0.7),
      this.calcDimension(0.1),
      this.calcDimension(0.2),
      colors.white,
    );

    bodyTop.position.set(0, 0, this.calcDimension(0.4));

    const backLeftWall = MeshFactory.createBox(
      this.calcDimension(0.3),
      this.calcDimension(0.09),
      this.calcDimension(0.22),
      colors.white,
    );
    const bodyEnd = MeshFactory.createBox(
      (0.5 / 1) * this.bodyLength,
      0.09,
      this.bodyLength / 3,
      colors.white,
    );
    const body = MeshFactory.createBox(
      (0.5 / 1.9) * this.bodyLength,
      (0.1 / 1.7) * this.bodyLength,
      this.bodyLength - 0.1,
      colors.white,
    );
    bodyEnd.position.set(
      this.calcDimension(0),
      this.calcDimension(0),
      this.calcDimension(-0.3),
    );

    bodyEnd.add(backRightWall);
    bodyEnd.add(backLeftWall);
    backRightWall.position.set(
      this.calcDimension(-0.2),
      this.calcDimension(0),
      this.calcDimension(0.28),
    );
    backLeftWall.position.set(
      this.calcDimension(0.19),
      this.calcDimension(0),
      this.calcDimension(0.27),
    );
    backRightWall.rotation.y = THREE.MathUtils.degToRad(45);
    backLeftWall.rotation.y = THREE.MathUtils.degToRad(45);
    body.add(bodyEnd);
    body.add(bodyTop);
    return body;
  }

  private createNeck() {
    return MeshFactory.createCylinder(
      this.calcDimension(0.1),
      this.calcDimension(0.1),
      this.calcDimension(0.6),
      colors.whiteMute,
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
    const controlBoardWidth = 0.45;
    const controlBoardLen = 0.65;
    const robotHatLen = controlBoardLen - 0.1;
    const controlBoard = MeshFactory.createBox(
      this.calcDimension(controlBoardWidth),
      this.calcDimension(0.005),
      this.calcDimension(controlBoardLen),
      colors.forestGreen2,
      { opacity: 0.8, transparent: true },
    );
    const portsCols = 3;
    const portWidth = controlBoardWidth / portsCols - 0.01;

    let leftOffset = (portWidth * 100 + 0.08) / 100;

    for (let i = 0; i < portsCols; i++) {
      const len = i + 1 === portsCols ? portWidth - 0.01 : portWidth - 0.05;
      const port = MeshFactory.createBox(
        this.calcDimension(portWidth - 0.01),
        this.calcDimension(0.1),
        this.calcDimension(
          i + 1 === portsCols ? portWidth - 0.01 : portWidth - 0.05,
        ),
        colors.silver,
      );

      const hole = MeshFactory.createBox(
        this.calcDimension(portWidth - 0.03),
        this.calcDimension(0.09),
        this.calcDimension(len),
        colors.black,
      );

      port.add(hole);
      hole.position.set(0, this.calcDimension(0), this.calcDimension(-0.01));
      controlBoard.add(port);

      port.position.set(
        this.calcDimension(leftOffset + 0.02),
        this.calcDimension(0.05),
        this.calcDimension(-(controlBoardLen / 2.3)),
      );
      leftOffset -= portWidth + 0.02;
    }

    const robotHAT = MeshFactory.createBox(
      this.calcDimension(controlBoardWidth),
      this.calcDimension(0.05),
      this.calcDimension(robotHatLen),
      colors.whiteMute,
    );

    const pillBaseW = controlBoardWidth / 2.3;
    const pillBaseH = robotHatLen / 2.7;

    for (let i = 0; i < 4; i++) {
      const isOdd = i % 2;
      const isTop = i < 2;
      const robotHatPillar = MeshFactory.createBox(
        this.calcDimension(0.05),
        this.calcDimension(0.3),
        this.calcDimension(0.05),
        colors.black,
      );

      robotHatPillar.position.set(
        this.calcDimension(isOdd ? pillBaseW : -pillBaseW),
        this.calcDimension(-0.18),
        this.calcDimension(isTop ? -pillBaseH : pillBaseH),
      );
      robotHAT.add(robotHatPillar);
    }

    const robotHATWall = MeshFactory.createBox(
      this.calcDimension(0.1),
      this.calcDimension(0.1),
      this.calcDimension(robotHatLen),
      colors.black,
    );

    robotHATWall.position.set(
      this.calcDimension(-(controlBoardWidth / 3)),
      this.calcDimension(-0.04),
      this.calcDimension(0),
    );
    robotHAT.add(robotHATWall);

    let offset = controlBoardWidth / 2.5;
    for (let i = 0; i < 5; i++) {
      const pwm = this.createPWM();
      const isSecondRow = i > 2;

      robotHAT.add(pwm);

      if (i === 3) {
        offset = controlBoardWidth / 2.5;
      }

      pwm.position.set(
        this.calcDimension(offset),
        this.calcDimension(0),
        this.calcDimension(isSecondRow ? -0.08 : -0.15),
      );

      offset -= 0.1;

      if (i === 2) {
        const pinRight = MeshFactory.createBox(
          this.calcDimension(0.05),
          this.calcDimension(0.08),
          this.calcDimension(0.1),
          colors.grey,
        );
        robotHAT.add(pinRight);

        pinRight.position.set(
          this.calcDimension(offset),
          this.calcDimension(0),
          this.calcDimension(isSecondRow ? -0.08 : -0.15),
        );
      }
    }

    const powerButton = MeshFactory.createBox(
      this.calcDimension(0.08),
      this.calcDimension(0.08),
      this.calcDimension(0.04),
      colors.black,
    );

    const ledButton = MeshFactory.createBox(
      this.calcDimension(0.04),
      this.calcDimension(0.08),
      this.calcDimension(0.08),
      colors.lime,
      { transparent: true, opacity: 0.3 },
    );
    robotHAT.add(ledButton);
    ledButton.position.set(
      this.calcDimension(-0.1),
      this.calcDimension(0),
      this.calcDimension(0.15),
    );
    robotHAT.add(powerButton);

    powerButton.position.set(
      this.calcDimension(0.15),
      this.calcDimension(0),
      this.calcDimension(0.15),
    );

    robotHAT.position.set(
      0,
      this.calcDimension(0.08),
      this.calcDimension(0.05),
    );
    controlBoard.add(robotHAT);
    return controlBoard;
  }

  private createPIN(color: number) {
    return MeshFactory.createBox(
      this.calcDimension(0.08),
      this.calcDimension(0.02),
      this.calcDimension(0.02),
      color,
    );
  }

  private createPWM() {
    const pwm = MeshFactory.createBox(
      this.calcDimension(0.08),
      this.calcDimension(0.04),
      this.calcDimension(0.1),
      colors.black,
      { opacity: 0.2, transparent: true },
    );

    const pins = [colors.grey, colors.red, colors.yellow];
    let offset = -0.04;
    for (let i = 0; i < pins.length; i++) {
      const col = pins[i];
      const pin = this.createPIN(col);
      pwm.add(pin);
      pin.position.set(
        this.calcDimension(0),
        this.calcDimension(0.02),
        this.calcDimension(offset),
      );
      offset += 0.02;
    }

    return pwm;
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
      this.calcDimension(0.04),
      this.calcDimension(0.04),
      height,
      colors.black,
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
    const wheelSize = size;

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
        colors.whiteMute,
      );
      wheel.add(spike);
      spike.rotation.y = THREE.MathUtils.degToRad(i * 10);
    }

    return wheel;
  }

  public dispose() {
    this.renderer.dispose();
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
}
