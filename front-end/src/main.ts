import { Controller } from '@/api';
import { VideoCarController } from './video-car-controller';
import './style.scss';

document.addEventListener('DOMContentLoaded', () => {
  const controller = new VideoCarController(
    new Controller(
      'ws://' + window.location.hostname + ':8765',
      !import.meta.env.PROD,
    ),
    document.querySelector<HTMLDivElement>('#app')!,
  );
  controller.start();
});
