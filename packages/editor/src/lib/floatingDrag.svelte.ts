export function createFloatingDrag(selector: string) {
  let pos = $state<{ x: number; y: number } | null>(null);

  function startDrag(e: PointerEvent): void {
    e.preventDefault();
    const el = (e.currentTarget as HTMLElement).closest(selector) as HTMLElement;
    const rect = el.getBoundingClientRect();
    const canvasRect = (el.parentElement as HTMLElement).getBoundingClientRect();
    const initX = rect.left - canvasRect.left;
    const initY = rect.top - canvasRect.top;
    const startX = e.clientX;
    const startY = e.clientY;
    function onMove(me: PointerEvent): void {
      pos = {
        x: Math.max(0, Math.min(canvasRect.width - rect.width, initX + me.clientX - startX)),
        y: Math.max(0, Math.min(canvasRect.height - rect.height, initY + me.clientY - startY)),
      };
    }
    function onUp(): void {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    }
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }

  return {
    get pos() { return pos; },
    startDrag,
  };
}
