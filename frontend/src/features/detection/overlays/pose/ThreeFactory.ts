import * as THREE from "three";
import { getRootStyleVariable } from "@/util/theme";

export class ThreeFactory {
  public static createLine(
    points: THREE.Vector3[],
    color: number,
    lineWidth: number,
  ): THREE.Line {
    const geometry = new THREE.BufferGeometry().setFromPoints(points);

    const material = new THREE.LineBasicMaterial({
      color,
      linewidth: lineWidth,
    });
    return new THREE.Line(geometry, material);
  }
  public static createKeypointSphere(
    radius: number,
    color: number,
  ): THREE.Mesh {
    const geometry = new THREE.SphereGeometry(radius, 16, 16);
    const material = new THREE.MeshBasicMaterial({ color });
    return new THREE.Mesh(geometry, material);
  }

  public static parseColor(color: string): number {
    if (color.startsWith("#")) {
      return parseInt(color.slice(1), 16);
    } else if (color.startsWith("--")) {
      return parseInt(getRootStyleVariable(color).slice(1), 16);
    } else if (color.startsWith("0x")) {
      return Number(color);
    }
    return 0xffffff;
  }

  public static createFiberCurves(
    start: THREE.Vector3,
    end: THREE.Vector3,
    absLineWidth: number,
    color: number,
  ): THREE.Line[] {
    const fibers: THREE.Line[] = [];
    const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
    const direction = new THREE.Vector3().subVectors(end, start);
    const distance = direction.length();

    if (distance === 0) {
      return fibers;
    }
    direction.normalize();

    const normal = new THREE.Vector3(-direction.y, direction.x, 0);
    const baseOffset = distance * 0.1;

    const cpOuterPos = mid
      .clone()
      .add(normal.clone().multiplyScalar(baseOffset));
    const cpOuterNeg = mid
      .clone()
      .add(normal.clone().multiplyScalar(-baseOffset));
    const cpInnerPos = mid
      .clone()
      .add(normal.clone().multiplyScalar(baseOffset * 0.5));
    const cpInnerNeg = mid
      .clone()
      .add(normal.clone().multiplyScalar(-baseOffset * 0.5));

    const createFiberLine = (
      controlPoint: THREE.Vector3,
      widthFactor: number,
    ) =>
      ThreeFactory.makeFiberLine(
        controlPoint,
        widthFactor,
        start,
        end,
        absLineWidth,
        color,
      );

    fibers.push(createFiberLine(cpOuterPos, 0.3));
    fibers.push(createFiberLine(cpOuterNeg, 0.1));

    fibers.push(createFiberLine(cpInnerPos, 0.3));
    fibers.push(createFiberLine(cpInnerNeg, 0.1));

    return fibers;
  }

  static makeFiberLine(
    controlPoint: THREE.Vector3,
    widthFactor: number,
    start: THREE.Vector3,
    end: THREE.Vector3,
    absLineWidth: number,
    color: number,
  ) {
    const curve = new THREE.QuadraticBezierCurve3(start, controlPoint, end);
    const points = curve.getPoints(50);
    const fiberLine = ThreeFactory.createLine(
      points,
      color,
      absLineWidth * widthFactor,
    );
    return fiberLine;
  }
}
