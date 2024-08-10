import './style.css';

import { VideoCarController } from './video-car-controller';
import { RealSockets } from '@/api';
import { FakeSockets } from '@/stubs';

document.addEventListener('DOMContentLoaded', () => {
  const controller = new VideoCarController(
    import.meta.env.PROD
      ? new RealSockets('ws://' + window.location.hostname + ':8765')
      : new FakeSockets(),
    document.querySelector<HTMLDivElement>('#app')!,
  );
  controller.start();
});
