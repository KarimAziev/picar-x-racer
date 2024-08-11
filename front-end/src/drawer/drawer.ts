import './drawer.css';

export interface DrawerParams {
  rootElement: HTMLElement;
}

export class Drawer {
  private rootElement: HTMLElement | null = null;

  constructor(params?: Partial<DrawerParams>) {
    if (params?.rootElement) {
      this.rootElement = params.rootElement;
      this.render();
    }
  }

  static make(params?: Partial<DrawerParams>) {
    return new Drawer(params);
  }

  mount<Element extends HTMLElement>(parentElement: Element) {
    this.rootElement = parentElement;
    this.render();
  }

  private render() {
    if (!this.rootElement) return;
    this.rootElement.innerHTML = `
    <nav id="drawer">
    <button class="toggle">Logs</button>
    <button class="toggle-side"></button>
    <ul class="logs">

    </ul>
    </nav>
    `;

    const toggleButton = document.querySelector('#drawer .toggle');
    const toggleButton2 = document.querySelector('#drawer .toggle-side');
    toggleButton2?.addEventListener('click', () => {
      const parent = document.querySelector('#drawer');
      parent?.classList.toggle('open');
    });
    toggleButton?.addEventListener('click', () => {
      const parent = document.querySelector('#drawer');
      parent?.classList.toggle('open');
    });
  }
}
