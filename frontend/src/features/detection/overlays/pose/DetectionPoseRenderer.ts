import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import type { DetectionResult } from "@/features/detection";
import type {
  OverlayLinesParams,
  KeypointsParams,
} from "@/features/detection/interface";
import { BODY_PARTS } from "@/features/detection/enums";
import {
  HEAD_SKELETON,
  ARMS_SKELETON,
  BODY_SKELETON,
  LEGS_SKELETON,
} from "@/features/detection/overlays/pose/config";
import { takePercentage } from "@/util/number";
import {
  keypointsGroups,
  keypointsColors,
} from "@/features/detection/overlays/pose/config";
import {
  mergeSkeleton,
  keystrokesPred,
} from "@/features/detection/overlays/pose/util";
import { ThreeFactory } from "@/features/detection/overlays/pose/ThreeFactory";
import { getRootStyleVariable } from "@/util/theme";

export class DetectionPoseRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private orbitControls: OrbitControls;
  private animationId: number | null = null;

  private bboxGroup: THREE.Group;
  private skeletonGroup: THREE.Group;
  private keypointsGroup: THREE.Group;

  constructor(
    private rootElement: HTMLElement,
    private baseFontSize: number,
    width = 400,
    height = 400,
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

    this.animate();
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
    return takePercentage(this.baseFontSize, percentage);
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
          this.keypointsGroup.add(sphere);
        });
      }

      if (keypoints && keypoints.length > 0) {
        const mergedSkeleton = [
          ...mergeSkeleton(
            HEAD_SKELETON,
            linesParams ? linesParams.head : undefined,
          ),
          ...mergeSkeleton(
            ARMS_SKELETON,
            linesParams ? linesParams.arms : undefined,
          ),
          ...mergeSkeleton(
            BODY_SKELETON,
            linesParams ? linesParams.torso : undefined,
          ),
          ...mergeSkeleton(
            LEGS_SKELETON,
            linesParams ? linesParams.legs : undefined,
          ),
        ];

        mergedSkeleton.forEach((bone) => {
          const [startIdx, endIdx, lineSizePercent, colorStr, renderFiber] =
            bone;

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

          const maxLineWidth = 4;

          const absLineWidth = takePercentage(maxLineWidth, lineSizePercent);
          const boneLine = ThreeFactory.createLine(
            [start, end],
            ThreeFactory.parseColor(colorStr),
            absLineWidth,
          );
          this.skeletonGroup.add(boneLine);
          if (renderFiber) {
            const fibers = ThreeFactory.createFiberCurves(
              start,
              end,
              absLineWidth,
              ThreeFactory.parseColor(colorStr),
            );
            fibers.forEach((fiberLine) => {
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
    this.renderer.dispose();
  }

  private animate(): void {
    this.orbitControls.update();
    this.renderer.render(this.scene, this.camera);
    this.animationId = requestAnimationFrame(this.animate.bind(this));
  }
}
