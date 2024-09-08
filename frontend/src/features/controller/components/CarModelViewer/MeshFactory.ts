import * as THREE from "three";

export const colors = {
  white: 0xffffff,
  white2: 0xf9f9f9,
  whiteMute: 0xf2f2f2,
  black: 0x181818,
  grey: 0x404040,
  indigo: 0x2c3e50,
  silver: 0xc0c0c0,
  red: 0xff0000,
  emerald: 0x10b981,
  lime: 0x00ff00,
  forestGreen1: 0x228b22,
  forestGreen2: 0x008000,
};

export class MeshFactory {
  static createBox(
    width: number,
    height: number,
    depth: number,
    color: number,
    params?: THREE.MeshPhongMaterialParameters,
  ) {
    const geometry = new THREE.BoxGeometry(width, height, depth);
    const material = new THREE.MeshPhongMaterial({ color, ...params });
    return new THREE.Mesh(geometry, material);
  }

  static createCylinder(
    radiusTop: number,
    radiusBottom: number,
    height: number,
    color: number,
  ) {
    const geometry = new THREE.CylinderGeometry(
      radiusTop,
      radiusBottom,
      height,
      32,
    );
    const material = new THREE.MeshPhongMaterial({ color });
    return new THREE.Mesh(geometry, material);
  }

  static createUltrasonicEye(size: number) {
    const eye = this.createCylinder(size, size, size * 2, colors.silver);
    const smallEye = this.createCylinder(
      size * 0.8,
      size * 0.8,
      size * 0.2,
      colors.black,
    );
    smallEye.position.set(0, -size, 0);
    eye.add(smallEye);
    eye.rotation.x = -Math.PI / 2;
    return eye;
  }

  static createRectangle(width: number, height: number, color = colors.lime) {
    const geometry = new THREE.PlaneGeometry(width, height);
    const material = new THREE.MeshPhongMaterial({
      color,
      side: THREE.DoubleSide,
    });
    return new THREE.Mesh(geometry, material);
  }

  static createTriangle(size: number, color = colors.lime) {
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
      color,
      side: THREE.DoubleSide,
    });

    return new THREE.Mesh(geometry, material);
  }
}
