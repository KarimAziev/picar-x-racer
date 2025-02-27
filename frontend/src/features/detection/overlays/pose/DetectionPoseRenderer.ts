import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { DetectionResult } from "@/features/detection";
import type {
  OverlayLinesParams,
  KeypointsParams,
} from "@/features/detection/interface";
import { BODY_PARTS } from "@/features/detection/enums";
import { overlayLinesGrouped } from "@/features/detection/overlays/pose/config";
import { takePercentage } from "@/util/number";
import {
  keypointsGroups,
  keypointsColors,
} from "@/features/detection/overlays/pose/config";
import {
  keystrokesPred,
  mergeSkeletonLines,
} from "@/features/detection/overlays/pose/util";
import { ThreeFactory } from "@/features/detection/overlays/pose/ThreeFactory";
import { getRootStyleVariable } from "@/util/theme";
import { startCase } from "@/util/str";
import { MAX_LINE_WIDTH } from "@/features/detection/overlays/config";

export type Metadata = {
  type: string;
  group: string;
};

export type OnItemClick = (event: MouseEvent, data?: Metadata) => void;

export class DetectionPoseRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private orbitControls: OrbitControls;
  private raycaster: THREE.Raycaster;
  private pointer: THREE.Vector2;

  private animationId: number | null = null;

  private bboxGroup: THREE.Group;
  private skeletonGroup: THREE.Group;
  private keypointsGroup: THREE.Group;

  private tooltipElement: HTMLElement;
  private tooltipTimer: number | null = null;
  private hoveredObject: THREE.Object3D | null = null;
  private readonly tooltipDelay = 500;

  constructor(
    private rootElement: HTMLElement,
    private baseFontSize: number,
    width = 400,
    height = 400,
    private onClick?: OnItemClick,
  ) {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000000);

    this.camera = new THREE.PerspectiveCamera(40, 2, 0.1, 2000);
    this.camera.position.set(0, 0, 1000);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(width, height);
    this.rootElement.appendChild(this.renderer.domElement);

    const ambient = new THREE.AmbientLight(0xffffff, 0.8);
    this.scene.add(ambient);

    this.bboxGroup = new THREE.Group();
    this.skeletonGroup = new THREE.Group();
    this.keypointsGroup = new THREE.Group();
    this.scene.add(this.bboxGroup);
    this.scene.add(this.skeletonGroup);
    this.scene.add(this.keypointsGroup);

    this.orbitControls = new OrbitControls(
      this.camera,
      this.renderer.domElement,
    );
    this.orbitControls.enableDamping = true;
    this.orbitControls.enableRotate = true;
    this.orbitControls.mouseButtons = {
      LEFT: THREE.MOUSE.PAN,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.RIGHT,
    };

    this.raycaster = new THREE.Raycaster();
    this.pointer = new THREE.Vector2();

    this.renderer.domElement.addEventListener(
      "click",
      this.handleClick.bind(this),
    );

    this.renderer.domElement.addEventListener(
      "mousemove",
      this.handleMouseMove.bind(this),
    );

    this.tooltipElement = document.createElement("div");
    this.tooltipElement.style.position = "absolute";
    this.tooltipElement.style.padding = "4px 8px";

    this.tooltipElement.style.backgroundColor = "var(--p-tooltip-background)";
    this.tooltipElement.style.color = "var(--p-tooltip-color)";
    this.tooltipElement.style.borderRadius = "4px";
    this.tooltipElement.style.width = "250px";
    this.tooltipElement.style.pointerEvents = "none";
    this.tooltipElement.style.transition = "opacity 0.2s";
    this.tooltipElement.style.opacity = "0";
    this.tooltipElement.style.zIndex = "9999";
    this.tooltipElement.style.fontSize = `${this.baseFontSize}px`;
    this.tooltipElement.classList.add("p-tooltip");
    this.tooltipElement.style.display = "block";
    this.rootElement.style.position = "relative";
    this.rootElement.appendChild(this.tooltipElement);

    this.animate();
  }

  public zoomIn(factor = 0.9): void {
    this.camera.position.z *= factor;
    this.orbitControls.update();
  }

  public zoomOut(factor = 1.1): void {
    this.camera.position.z *= factor;
    this.orbitControls.update();
  }

  private handleMouseMove(event: MouseEvent): void {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.pointer, this.camera);

    const interactiveObjects = [
      ...this.keypointsGroup.children,
      ...this.skeletonGroup.children,
      ...this.bboxGroup.children,
    ];

    const intersects = this.raycaster.intersectObjects(
      interactiveObjects,
      false,
    );

    if (intersects.length > 0) {
      this.renderer.domElement.style.cursor = "pointer";
    } else {
      this.renderer.domElement.style.cursor = "auto";
    }

    if (intersects.length > 0) {
      const firstObj = intersects[0].object;
      if (this.hoveredObject !== firstObj) {
        this.clearTooltipTimer();
        this.hoveredObject = firstObj;
        this.tooltipTimer = window.setTimeout(() => {
          this.showTooltip(event, firstObj.userData as Metadata);
        }, this.tooltipDelay);
      } else {
        if (this.tooltipElement.style.opacity === "1") {
          this.updateTooltipPosition(event);
        }
      }
    } else {
      this.hoveredObject = null;
      this.clearTooltipTimer();
      this.hideTooltip();
    }
  }

  private handleClick(event: MouseEvent): void {
    this.hideTooltip();
    this.clearTooltipTimer();

    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.pointer, this.camera);

    const interactiveObjects = [
      ...this.keypointsGroup.children,
      ...this.skeletonGroup.children,
      ...this.bboxGroup.children,
    ];

    const intersects = this.raycaster.intersectObjects(
      interactiveObjects,
      false,
    );

    if (intersects.length > 0) {
      const selectedObject = intersects[0].object;
      const metadata = selectedObject.userData;
      if (this.onClick) {
        this.onClick(event, metadata as Metadata);
      }
    } else {
      if (this.onClick) {
        this.onClick(event);
      }
    }
  }

  public moveUp(distance = 20): void {
    this.camera.position.y -= distance;
    this.orbitControls.target.y -= distance;
    this.orbitControls.update();
  }

  public moveDown(distance = 20): void {
    this.camera.position.y += distance;
    this.orbitControls.target.y += distance;
    this.orbitControls.update();
  }

  public moveLeft(distance = 20): void {
    this.camera.position.x += distance;
    this.orbitControls.target.x += distance;
    this.orbitControls.update();
  }

  public moveRight(distance = 20): void {
    this.camera.position.x -= distance;
    this.orbitControls.target.x -= distance;
    this.orbitControls.update();
  }

  private showTooltip(event: MouseEvent, data: Metadata): void {
    this.tooltipElement.innerHTML = `<div>Type: ${startCase(data.type)}</div><div>Group: ${startCase(data.group)}</div>`;
    this.tooltipElement.style.opacity = "1";

    this.updateTooltipPosition(event);
  }

  private updateTooltipPosition(event: MouseEvent): void {
    const rect = this.rootElement.getBoundingClientRect();
    const x = event.clientX - rect.left + 20;
    const y = event.clientY - rect.top + 5;
    this.tooltipElement.style.left = `${x}px`;
    this.tooltipElement.style.top = `${y}px`;
  }

  private hideTooltip(): void {
    this.tooltipElement.style.opacity = "0";
  }

  private clearTooltipTimer(): void {
    if (this.tooltipTimer !== null) {
      clearTimeout(this.tooltipTimer);
      this.tooltipTimer = null;
    }
  }

  public alignToCenter() {
    const box = new THREE.Box3();
    box.expandByObject(this.bboxGroup);
    box.expandByObject(this.skeletonGroup);
    box.expandByObject(this.keypointsGroup);
    const center = new THREE.Vector3();
    box.getCenter(center);

    this.orbitControls.target.copy(center);
    this.camera.lookAt(center);
    this.orbitControls.update();
    this.camera.position.set(center.x, center.y + 50, center.z + 800);
    this.camera.lookAt(center);
    this.orbitControls.update();
  }

  private toAbsSize(percentage: number): number {
    return takePercentage(MAX_LINE_WIDTH, percentage);
  }

  public renderDetections(
    detections: DetectionResult[],
    linesParams?: OverlayLinesParams,
    keypointsParams?: KeypointsParams,
    bboxesColor?: string,
  ): void {
    this.bboxGroup.clear();
    this.skeletonGroup.clear();
    this.keypointsGroup.clear();

    detections.forEach((detection) => {
      const { bbox, keypoints } = detection;

      if (bbox) {
        const [x1, y1, x2, y2] = bbox;
        const boxPoints = [
          new THREE.Vector3(x1, -y1, 0),
          new THREE.Vector3(x2, -y1, 0),
          new THREE.Vector3(x2, -y2, 0),
          new THREE.Vector3(x1, -y2, 0),
          new THREE.Vector3(x1, -y1, 0),
        ];
        const colorNumber = ThreeFactory.parseColor(
          bboxesColor || "--color-text",
        );

        const boxLine = ThreeFactory.createLine(boxPoints, colorNumber, 2);
        boxLine.userData = { type: "bbox", group: "bbox" };
        this.bboxGroup.add(boxLine);
      }

      if (keypoints && keypoints.length > 0) {
        keypoints.forEach((kp, idx) => {
          const groupName = keypointsGroups[idx as BODY_PARTS];

          let kpSize = 4;
          let kpColor = 0xffffff;
          if (keypointsParams && keypointsParams[groupName]) {
            kpSize = this.toAbsSize(keypointsParams[groupName].size);

            kpColor = ThreeFactory.parseColor(
              keypointsParams[groupName].color ||
                getRootStyleVariable(
                  keypointsColors[idx as keyof typeof keypointsColors],
                ),
            );
          }

          const sphere = ThreeFactory.createKeypointSphere(kpSize, kpColor);
          sphere.position.set(kp.x, -kp.y, 0);
          sphere.userData = {
            type: "keypoint",
            group: groupName,
          };
          this.keypointsGroup.add(sphere);
        });
      }

      if (keypoints && keypoints.length > 0) {
        const mergedSkeleton = mergeSkeletonLines(
          overlayLinesGrouped,
          linesParams,
        );

        mergedSkeleton.forEach((bone) => {
          const [
            startIdx,
            endIdx,
            lineSizePercent,
            colorStr,
            renderFiber,
            groupKey,
          ] = bone;

          if (
            !keystrokesPred(keypoints[startIdx]) ||
            !keystrokesPred(keypoints[endIdx])
          ) {
            return;
          }
          const start = new THREE.Vector3(
            keypoints[startIdx].x,
            -keypoints[startIdx].y,
            0,
          );
          const end = new THREE.Vector3(
            keypoints[endIdx].x,
            -keypoints[endIdx].y,
            0,
          );

          const absLineWidth = takePercentage(
            MAX_LINE_WIDTH,
            Math.max(1, lineSizePercent),
          );
          const boneLine = ThreeFactory.createLine(
            [start, end],
            ThreeFactory.parseColor(colorStr),
            absLineWidth,
          );
          boneLine.userData = {
            type: "skeleton",
            group: groupKey,
          };
          this.skeletonGroup.add(boneLine);
          if (renderFiber) {
            const fibers = ThreeFactory.createFiberCurves(
              start,
              end,
              absLineWidth,
              ThreeFactory.parseColor(colorStr),
            );
            fibers.forEach((fiberLine) => {
              fiberLine.userData = {
                type: "skeleton",
                group: groupKey,
              };
              this.skeletonGroup.add(fiberLine);
            });
          }
        });
      }
    });
  }

  public setSize(width: number, height: number): void {
    this.renderer.setSize(width, height);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  public dispose(): void {
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
    }
    this.renderer.domElement.removeEventListener("click", this.handleClick);
    this.renderer.domElement.removeEventListener(
      "mousemove",
      this.handleMouseMove,
    );
    this.renderer.dispose();
  }

  private animate(): void {
    this.orbitControls.update();
    this.renderer.render(this.scene, this.camera);
    this.animationId = requestAnimationFrame(this.animate.bind(this));
  }
}
