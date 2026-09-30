/**
 * APEX SPEED 3D - Unified Desktop & Mobile Input Handler
 */

class InputController {
  constructor() {
    this.gas = false;
    this.brake = false;
    this.left = false;
    this.right = false;
    this.drift = false;
    this.nitro = false;
    this.reset = false;

    this.locked = false; // Locked during countdown

    this.initKeyboard();
    this.initTouchControls();
  }

  lock() {
    this.locked = true;
    this.resetAll();
  }

  unlock() {
    this.locked = false;
  }

  resetAll() {
    this.gas = false;
    this.brake = false;
    this.left = false;
    this.right = false;
    this.drift = false;
    this.nitro = false;
    this.reset = false;
  }

  initKeyboard() {
    window.addEventListener('keydown', (e) => {
      // Unlock sound on first user gesture
      if (window.soundEngine) window.soundEngine.unlock();

      if (this.locked) return;

      switch (e.code) {
        case 'KeyW':
        case 'ArrowUp':
          this.gas = true;
          break;
        case 'KeyS':
        case 'ArrowDown':
          this.brake = true;
          break;
        case 'KeyA':
        case 'ArrowLeft':
          this.left = true;
          break;
        case 'KeyD':
        case 'ArrowRight':
          this.right = true;
          break;
        case 'Space':
          this.drift = true;
          break;
        case 'ShiftLeft':
        case 'ShiftRight':
        case 'KeyN':
        case 'KeyE':
          this.nitro = true;
          break;
        case 'KeyR':
          this.reset = true;
          break;
      }
    });

    window.addEventListener('keyup', (e) => {
      switch (e.code) {
        case 'KeyW':
        case 'ArrowUp':
          this.gas = false;
          break;
        case 'KeyS':
        case 'ArrowDown':
          this.brake = false;
          break;
        case 'KeyA':
        case 'ArrowLeft':
          this.left = false;
          break;
        case 'KeyD':
        case 'ArrowRight':
          this.right = false;
          break;
        case 'Space':
          this.drift = false;
          break;
        case 'ShiftLeft':
        case 'ShiftRight':
        case 'KeyN':
        case 'KeyE':
          this.nitro = false;
          break;
        case 'KeyR':
          this.reset = false;
          break;
      }
    });
  }

  initTouchControls() {
    const bindBtn = (id, property) => {
      const el = document.getElementById(id);
      if (!el) return;

      const onPress = (e) => {
        e.preventDefault();
        if (window.soundEngine) window.soundEngine.unlock();
        if (this.locked) return;
        this[property] = true;
        el.classList.add('active');
      };

      const onRelease = (e) => {
        e.preventDefault();
        this[property] = false;
        el.classList.remove('active');
      };

      el.addEventListener('touchstart', onPress, { passive: false });
      el.addEventListener('touchend', onRelease, { passive: false });
      el.addEventListener('touchcancel', onRelease, { passive: false });
      el.addEventListener('mousedown', onPress);
      el.addEventListener('mouseup', onRelease);
      el.addEventListener('mouseleave', onRelease);
    };

    // Wait for DOM
    window.addEventListener('DOMContentLoaded', () => {
      bindBtn('touch-gas', 'gas');
      bindBtn('touch-brake', 'brake');
      bindBtn('touch-left', 'left');
      bindBtn('touch-right', 'right');
      bindBtn('touch-drift', 'drift');
      bindBtn('touch-nitro', 'nitro');
      bindBtn('touch-reset', 'reset');
    });
  }
}

window.inputController = new InputController();
